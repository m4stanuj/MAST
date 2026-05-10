"""
M4STCLAW Voice System v1.0
============================
Bidirectional voice — Hear → Understand → Respond → Speak.

2026 Stack:
  Wake Word : Vosk offline keyword detection ("hey m4stclaw")
  STT       : Groq Whisper (fastest, free) → local Whisper fallback
  TTS       : pyttsx3 local (instant) → gTTS (better quality)
  Barge-In  : Detect user speaking while AI responds
  Language  : Hinglish optimized

Components:
  VoiceSession  — full continuous session (background thread)
  t_voice_listen — single utterance capture
  t_voice_speak  — TTS speak text
  t_wake_word    — toggle wake word detection
"""

import os, io, time, queue, threading, base64, re, wave, tempfile
from typing import Optional, Callable
from pathlib import Path

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


# ══════════════════════════════════════════════════════════════════════
#  TTS ENGINE
# ══════════════════════════════════════════════════════════════════════

class TTSEngine:
    """Local TTS — instant, no internet. pyttsx3 primary, gTTS fallback."""

    def __init__(self):
        self._engine = None
        self._lock = threading.Lock()
        self._queue: queue.Queue = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def _init(self):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", 168)    # Speed — comfortable for Hinglish
            engine.setProperty("volume", 0.9)
            # Prefer Indian English voice if available
            voices = engine.getProperty("voices")
            for v in voices:
                if "india" in v.name.lower() or "zira" in v.name.lower():
                    engine.setProperty("voice", v.id)
                    break
            return engine
        except Exception as e:
            print(f"[VOICE] pyttsx3 init error: {e}")
            return None

    def _worker(self):
        self._engine = self._init()
        while self._running:
            try:
                text = self._queue.get(timeout=1.0)
                if text is None:
                    break
                self._speak_now(text)
                self._queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[VOICE] TTS worker error: {e}")

    def _speak_now(self, text: str):
        # Clean text for TTS
        text = re.sub(r'[*_`#]', '', text)       # Remove markdown
        text = re.sub(r'https?://\S+', 'link', text)  # Replace URLs
        text = text.strip()
        if not text:
            return

        if self._engine:
            try:
                self._engine.say(text)
                self._engine.runAndWait()
                return
            except Exception:
                pass

        # gTTS fallback
        try:
            from gtts import gTTS
            import pygame
            tts = gTTS(text=text[:500], lang="hi" if _has_hindi(text) else "en", slow=False)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tts.save(f.name)
                pygame.mixer.init()
                pygame.mixer.music.load(f.name)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
            os.unlink(f.name)
        except Exception as e:
            print(f"[VOICE] gTTS error: {e}")

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._worker, daemon=True, name="TTS-Worker")
        self._thread.start()

    def speak(self, text: str):
        self._queue.put(text)

    def stop(self):
        self._running = False
        self._queue.put(None)

    def is_speaking(self) -> bool:
        return not self._queue.empty()


def _has_hindi(text: str) -> bool:
    """Check if text has Hindi/Devanagari characters."""
    return bool(re.search(r'[\u0900-\u097F]', text))


# ══════════════════════════════════════════════════════════════════════
#  STT ENGINE
# ══════════════════════════════════════════════════════════════════════

class STTEngine:
    """
    Speech-to-Text:
      1. Record audio via pyaudio
      2. Transcribe via Groq Whisper (free, fastest) or local Whisper
    """

    def __init__(self, language: str = "hi-IN"):
        self.language = language
        self._groq_key = _cfg("GROQ_API_KEY")
        self._groq_whisper_url = "https://api.groq.com/openai/v1/audio/transcriptions"

    def record(self, duration: float = 5.0, sample_rate: int = 16000) -> Optional[bytes]:
        """Record audio from microphone."""
        try:
            import pyaudio
            import numpy as np
            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=sample_rate,
                input=True,
                frames_per_buffer=1024,
            )
            frames = []
            total = int(sample_rate / 1024 * duration)
            for _ in range(total):
                data = stream.read(1024, exception_on_overflow=False)
                frames.append(data)
            stream.stop_stream()
            stream.close()
            pa.terminate()

            # Convert to WAV bytes
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(b"".join(frames))
            return buf.getvalue()
        except Exception as e:
            print(f"[VOICE] Record error: {e}")
            return None

    def transcribe(self, audio_bytes: bytes) -> str:
        """Transcribe audio to text."""
        if not audio_bytes:
            return ""

        # Groq Whisper — fastest free option
        if self._groq_key:
            try:
                import requests
                files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
                data = {
                    "model": "whisper-large-v3-turbo",
                    "language": self.language.split("-")[0],  # "hi" or "en"
                    "response_format": "text",
                }
                r = requests.post(
                    self._groq_whisper_url,
                    headers={"Authorization": f"Bearer {self._groq_key}"},
                    files=files,
                    data=data,
                    timeout=15,
                )
                if r.ok:
                    return r.text.strip()
            except Exception as e:
                print(f"[VOICE] Groq Whisper error: {e}")

        # Local Whisper fallback
        try:
            import whisper
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_bytes)
                tmp_path = f.name
            model = whisper.load_model("base")
            result = model.transcribe(tmp_path, language="hi" if "hi" in self.language else "en")
            os.unlink(tmp_path)
            return result["text"].strip()
        except ImportError:
            pass
        except Exception as e:
            print(f"[VOICE] Local Whisper error: {e}")

        # SpeechRecognition fallback (Google)
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            with io.BytesIO(audio_bytes) as f:
                with sr.AudioFile(f) as source:
                    audio = recognizer.record(source)
            return recognizer.recognize_google(audio, language=self.language)
        except Exception as e:
            print(f"[VOICE] SpeechRecognition error: {e}")
            return ""

    def listen_once(self, duration: float = 5.0) -> str:
        """Record + transcribe in one call."""
        print("[VOICE] 🎤 Listening...")
        audio = self.record(duration)
        if not audio:
            return ""
        text = self.transcribe(audio)
        print(f"[VOICE] Heard: {text}")
        return text


# ══════════════════════════════════════════════════════════════════════
#  WAKE WORD DETECTOR
# ══════════════════════════════════════════════════════════════════════

WAKE_WORDS = ["hey m4stclaw", "hey mast", "hey m4st", "jarvis", "हे जार्विस", "ऐ मस्त"]

class WakeWordDetector:
    """
    Offline wake word detection.
    Primary: Vosk (accurate, requires model download)
    Fallback: Energy-based detection + keyword match via Groq Whisper
    """

    def __init__(self):
        self._running = False
        self._callback: Optional[Callable] = None
        self._vosk_model = None
        self._thread: Optional[threading.Thread] = None

    def _init_vosk(self) -> bool:
        try:
            from vosk import Model, KaldiRecognizer
            model_path = os.path.join(ROOT, "data", "vosk-model")
            if not os.path.exists(model_path):
                print(f"[WAKE] Vosk model not found at {model_path}")
                print(f"[WAKE] Download: https://alphacephei.com/vosk/models (vosk-model-small-en-us)")
                return False
            self._vosk_model = Model(model_path)
            print("[WAKE] ✅ Vosk model loaded")
            return True
        except ImportError:
            print("[WAKE] Vosk not installed (pip install vosk)")
            return False
        except Exception as e:
            print(f"[WAKE] Vosk init error: {e}")
            return False

    def _listen_vosk(self):
        """Continuous listening with Vosk."""
        from vosk import KaldiRecognizer
        import pyaudio, json as _json
        rec = KaldiRecognizer(self._vosk_model, 16000)
        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=pyaudio.paInt16, channels=1, rate=16000,
            input=True, frames_per_buffer=8000,
        )
        stream.start_stream()
        print("[WAKE] 🎤 Wake word detection active — say 'Hey M4STCLAW'")
        while self._running:
            data = stream.read(4000, exception_on_overflow=False)
            if rec.AcceptWaveform(data):
                result = _json.loads(rec.Result())
                text = result.get("text", "").lower()
                if any(w in text for w in WAKE_WORDS):
                    print(f"[WAKE] 🔥 Wake word detected!")
                    if self._callback:
                        self._callback()
        stream.stop_stream()
        pa.terminate()

    def _listen_energy(self):
        """Fallback: energy-based detection, then Whisper check."""
        import pyaudio
        import struct
        import math
        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=pyaudio.paInt16, channels=1, rate=16000,
            input=True, frames_per_buffer=1024,
        )
        THRESHOLD = 1500
        SILENCE_FRAMES = 20
        print("[WAKE] 🎤 Energy wake word active (fallback mode)")
        frames = []
        silent_count = 0
        recording = False

        while self._running:
            data = stream.read(1024, exception_on_overflow=False)
            shorts = struct.unpack(f"{len(data)//2}h", data)
            rms = math.sqrt(sum(s*s for s in shorts) / len(shorts))

            if rms > THRESHOLD:
                recording = True
                silent_count = 0
                frames.append(data)
            elif recording:
                frames.append(data)
                silent_count += 1
                if silent_count > SILENCE_FRAMES:
                    # Check if it's a wake word
                    audio_bytes = self._frames_to_wav(frames, 16000)
                    stt = STTEngine()
                    text = stt.transcribe(audio_bytes).lower()
                    frames = []
                    recording = False
                    silent_count = 0
                    if any(w in text for w in WAKE_WORDS):
                        print(f"[WAKE] 🔥 Wake word: '{text}'")
                        if self._callback:
                            self._callback()

        stream.stop_stream()
        pa.terminate()

    def _frames_to_wav(self, frames: list, rate: int) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(rate)
            wf.writeframes(b"".join(frames))
        return buf.getvalue()

    def start(self, on_wake: Callable):
        """Start wake word detection in background thread."""
        self._callback = on_wake
        self._running = True
        if self._init_vosk():
            target = self._listen_vosk
        else:
            target = self._listen_energy
        self._thread = threading.Thread(target=target, daemon=True, name="WakeWord")
        self._thread.start()

    def stop(self):
        self._running = False


# ══════════════════════════════════════════════════════════════════════
#  FULL VOICE SESSION
# ══════════════════════════════════════════════════════════════════════

class VoiceSession:
    """
    Complete voice session:
    Wake word → Listen → Transcribe → M4STCLAW → Speak response
    """

    def __init__(self, bridge_url: str = "http://localhost:5000"):
        self.bridge_url = bridge_url
        self.tts = TTSEngine()
        self.stt = STTEngine()
        self.wake = WakeWordDetector()
        self._active = False
        self._history = []

    def _on_wake(self):
        """Called when wake word detected."""
        self.tts.speak("Haan bolo")
        time.sleep(0.5)
        # Listen for command
        text = self.stt.listen_once(duration=6.0)
        if not text.strip():
            self.tts.speak("Sunai nahi diya, phir se bolo")
            return
        print(f"[VOICE] Command: {text}")
        # Send to M4STCLAW bridge
        try:
            import requests
            resp = requests.post(
                f"{self.bridge_url}/chat",
                json={"message": text, "task_type": "auto", "history": self._history[-4:]},
                timeout=30,
            )
            if resp.ok:
                reply = resp.json().get("content", "")
                self._history.append({"role": "user", "content": text})
                self._history.append({"role": "assistant", "content": reply})
                # Speak response (keep it short for voice)
                speak_text = reply[:400] if len(reply) > 400 else reply
                self.tts.speak(speak_text)
            else:
                self.tts.speak("Kuch problem ho gayi")
        except Exception as e:
            print(f"[VOICE] Bridge error: {e}")
            self.tts.speak("Bridge se connect nahi ho raha")

    def start(self):
        """Start full voice session."""
        self._active = True
        self.tts.start()
        self.tts.speak("M4STCLAW active. Hey M4STCLAW bolo activate karne ke liye.")
        self.wake.start(on_wake=self._on_wake)
        print("[VOICE] ✅ Voice session started")

    def stop(self):
        """Stop voice session."""
        self._active = False
        self.wake.stop()
        self.tts.stop()


# ══════════════════════════════════════════════════════════════════════
#  TOOL FUNCTIONS
# ══════════════════════════════════════════════════════════════════════

_tts_global: Optional[TTSEngine] = None
_stt_global: Optional[STTEngine] = None
_session_global: Optional[VoiceSession] = None

def t_voice_speak(text: str, wait: bool = False) -> str:
    """Text ko speech mein convert karo."""
    global _tts_global
    if _tts_global is None:
        _tts_global = TTSEngine()
        _tts_global.start()
    _tts_global.speak(text)
    if wait:
        while _tts_global.is_speaking():
            time.sleep(0.2)
    return f"✅ Speaking: {text[:60]}..."


def t_voice_listen(duration: float = 5.0) -> str:
    """Microphone se ek utterance sunna."""
    global _stt_global
    if _stt_global is None:
        _stt_global = STTEngine()
    text = _stt_global.listen_once(duration)
    if text:
        return f"🎤 Heard: {text}"
    return "🎤 Nothing detected (check microphone)"


def t_voice_session_start() -> str:
    """Start full wake-word enabled voice session."""
    global _session_global
    if _session_global and _session_global._active:
        return "Voice session already running"
    _session_global = VoiceSession()
    threading.Thread(target=_session_global.start, daemon=True).start()
    return "✅ Voice session started — say 'Hey M4STCLAW'"


def t_voice_session_stop() -> str:
    """Stop voice session."""
    global _session_global
    if _session_global:
        _session_global.stop()
        _session_global = None
    return "✅ Voice session stopped"


def t_voice_status() -> str:
    """Voice system status."""
    try:
        import pyaudio
        pa = pyaudio.PyAudio()
        mics = pa.get_device_count()
        pa.terminate()
        mic_ok = mics > 0
    except Exception:
        mic_ok = False

    session_active = _session_global is not None and _session_global._active
    return "\n".join([
        "🎤 Voice System Status:",
        f"  Microphone: {'✅ Found' if mic_ok else '❌ Not found'}",
        f"  Groq Whisper: {'✅' if _cfg('GROQ_API_KEY') else '❌ No key'}",
        f"  Session: {'🟢 Active' if session_active else '⚫ Stopped'}",
        f"  Wake words: {', '.join(WAKE_WORDS[:3])}",
    ])
