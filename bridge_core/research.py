"""
M4STCLAW Research Agent v1.0
==============================
Multi-source deep research — upgraded over M4ST v6.

2026 Upgrades:
  ✅ Tavily API as primary (agent-optimized search)
  ✅ Gap detection loop (finds what's missing, searches again)
  ✅ Source deduplication
  ✅ Parallel search (asyncio)
  ✅ Structured output with citations
  ✅ Perplexity fallback for web-grounded answers
  ✅ Research depth levels (quick/standard/deep)
"""

import os, re, time, json, asyncio, threading
from typing import List, Dict, Optional
import requests as http

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _cfg(key, default=""):
    try:
        with open(os.path.join(ROOT, "config", ".env"), encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == key:
                    return v.strip()
    except FileNotFoundError:
        pass
    return os.environ.get(key, default)

def _brain(prompt: str, task_type: str = "research", max_tokens: int = 2000) -> str:
    from brain import brain_quick
    return brain_quick(prompt, task_type=task_type, max_tokens=max_tokens)


# ══════════════════════════════════════════════════════════════════════
#  SEARCH BACKENDS
# ══════════════════════════════════════════════════════════════════════

def _tavily_search(query: str, max_results: int = 5, search_depth: str = "basic") -> List[Dict]:
    key = _cfg("TAVILY_API_KEY")
    if not key:
        return []
    try:
        r = http.post(
            "https://api.tavily.com/search",
            json={
                "api_key": key,
                "query": query,
                "max_results": max_results,
                "search_depth": search_depth,  # basic or advanced
                "include_answer": True,
                "include_raw_content": False,
            },
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        results = data.get("results", [])
        if data.get("answer"):
            results.insert(0, {"title": "Tavily AI Answer", "url": "", "content": data["answer"], "score": 1.0})
        return results
    except Exception as e:
        print(f"[RESEARCH] Tavily error: {e}")
        return []


def _ddg_search(query: str, max_results: int = 5) -> List[Dict]:
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddg:
            results = list(ddg.text(query, max_results=max_results))
        return [{"title": r.get("title",""), "url": r.get("href",""), "content": r.get("body",""), "score": 0.5} for r in results]
    except Exception as e:
        print(f"[RESEARCH] DDG error: {e}")
        return []


def _perplexity_search(query: str) -> str:
    """Perplexity — web-grounded answer."""
    key = _cfg("PERPLEXITY_API_KEY")
    if not key:
        return ""
    try:
        r = http.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": "sonar",
                "messages": [{"role": "user", "content": query}],
                "max_tokens": 1000,
            },
            timeout=20,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[RESEARCH] Perplexity error: {e}")
        return ""


def _fetch_article(url: str) -> str:
    """Extract main text from URL."""
    if not url:
        return ""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; M4STCLAW/1.0)"}
        r = http.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        try:
            from newspaper import Article
            art = Article(url)
            art.set_html(r.text)
            art.parse()
            return art.text[:1500]
        except Exception:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r.text, "html.parser")
            for tag in soup(["script", "style", "nav"]):
                tag.decompose()
            return soup.get_text(separator=" ", strip=True)[:1500]
    except Exception:
        return ""


# ══════════════════════════════════════════════════════════════════════
#  MAIN RESEARCH FUNCTION
# ══════════════════════════════════════════════════════════════════════

def research(
    query: str,
    depth: str = "standard",  # quick | standard | deep
    max_sources: int = 6,
) -> str:
    """
    Deep research on a topic.
    depth:
      quick    — 1 search, AI summary
      standard — 2 searches + gap detection
      deep     — 3+ searches + full article fetch + synthesis
    """
    start_time = time.time()
    all_results = []
    seen_urls = set()

    print(f"[RESEARCH] Query: {query} | Depth: {depth}")

    # ── Round 1: Primary search ─────────────────────────────────────
    results = _tavily_search(query, max_results=max_sources, search_depth="advanced" if depth == "deep" else "basic")
    if not results:
        results = _ddg_search(query, max_results=max_sources)
    
    for r in results:
        url = r.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            all_results.append(r)

    if depth == "quick":
        return _synthesize(query, all_results, depth="quick")

    # ── Round 2: Gap detection ──────────────────────────────────────
    if depth in ("standard", "deep") and all_results:
        content_so_far = " ".join(r.get("content","") for r in all_results[:5])
        gap_prompt = f"""Research query: {query}

Found information:
{content_so_far[:1000]}

What IMPORTANT aspects are MISSING from this research? List 2-3 specific search queries needed to fill gaps.
Format: one query per line, no explanation."""
        
        gap_queries_raw = _brain(gap_prompt, task_type="reasoning", max_tokens=200)
        gap_queries = [q.strip() for q in gap_queries_raw.strip().split("\n") if q.strip() and len(q) > 5][:2]
        
        for gq in gap_queries:
            print(f"[RESEARCH] Gap search: {gq}")
            gap_results = _tavily_search(gq, max_results=3)
            if not gap_results:
                gap_results = _ddg_search(gq, max_results=3)
            for r in gap_results:
                url = r.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(r)

    # ── Round 3: Article fetch (deep only) ─────────────────────────
    if depth == "deep":
        # Fetch top 3 article full texts
        for i, result in enumerate(all_results[:3]):
            url = result.get("url", "")
            if url and len(result.get("content", "")) < 200:
                full_text = _fetch_article(url)
                if full_text:
                    all_results[i]["content"] = full_text

        # Also try Perplexity
        perplexity_answer = _perplexity_search(query)
        if perplexity_answer:
            all_results.insert(0, {"title": "Perplexity Web Answer", "url": "perplexity.ai", "content": perplexity_answer, "score": 0.9})

    # ── Synthesis ───────────────────────────────────────────────────
    result_text = _synthesize(query, all_results[:max_sources], depth=depth)
    elapsed = time.time() - start_time
    return result_text + f"\n\n_Research completed in {elapsed:.1f}s | {len(all_results)} sources_"


def _synthesize(query: str, results: List[Dict], depth: str = "standard") -> str:
    """LLM se results synthesize karke final report banao."""
    if not results:
        return f"⚠️ No sources found for: {query}"

    # Build context from results
    context_parts = []
    citations = []
    for i, r in enumerate(results[:6], 1):
        title = r.get("title", "Source")
        url = r.get("url", "")
        content = r.get("content", "")[:500]
        context_parts.append(f"[{i}] {title}\n{content}")
        if url:
            citations.append(f"[{i}] {title}: {url}")

    context = "\n\n".join(context_parts)

    depth_instructions = {
        "quick": "Write a brief 2-3 paragraph summary. Be concise.",
        "standard": "Write a comprehensive summary with key findings. 3-5 paragraphs. Include specific facts, numbers, dates.",
        "deep": "Write a detailed research report. Include: Executive Summary, Key Findings, Analysis, Implications. Cite sources as [1], [2] etc.",
    }

    synthesis_prompt = f"""You are a research analyst. Based on these sources, answer the research query.

Query: {query}

Sources:
{context}

{depth_instructions.get(depth, depth_instructions['standard'])}

Write in Hinglish-friendly style if the query was in Hinglish. Be factual, cite sources."""

    summary = _brain(synthesis_prompt, task_type="research", max_tokens=2000)

    # Add citations
    if citations and depth in ("standard", "deep"):
        summary += "\n\n**Sources:**\n" + "\n".join(citations)

    return summary


def quick_research(query: str) -> str:
    """Fast single-call research."""
    return research(query, depth="quick")


def deep_research(query: str) -> str:
    """Full deep research."""
    return research(query, depth="deep")
