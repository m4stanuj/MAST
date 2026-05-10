---
name: excel-full
description: Full Excel file manipulation - read, write, formulas, formatting (3.6k stars)
---

# Excel MCP Server — haris-musa/excel-mcp-server

**MOST POPULAR EXCEL MCP:** 3.6k stars | Fully free | No API keys needed

## Quick Start

### Install (already done!)
```bash
pip install excel-mcp-server
```

### Verified Command
```bash
python -m excel_mcp stdio
```

### Status: ✅ WORKING

### Configuration (opencode.jsonc)
```jsonc
{
  "mcp": {
    "excel-full": {
      "command": ["python", "-m", "excel_mcp", "stdio"],
      "enabled": true
    }
  }
}
```

## Features

### Read Operations ✅
- Read cell values
- Read entire sheets
- Read formulas
- Get metadata

### Write Operations ✅
- Write cell values
- Write formulas
- Create new sheets
- Format cells

### Advanced ✅
- Formulas (SUM, AVERAGE, VLOOKUP, etc.)
- Cell formatting (bold, colors, borders)
- Multiple sheets
- Data validation

## Rating

| Feature | Score |
|---------|-------|
| Free | ✅ 10/10 |
| Functionality | ✅ 10/10 |
| Stars | 3.6k ⭐ |
| Ease of Use | 9/10 |

**Overall: 10/10** — Best Excel MCP, fully free!

# Excel MCP Server — haris-musa/excel-mcp-server

**MOST POPULAR EXCEL MCP:** 3.6k stars | Fully free | No API keys needed

## Quick Start

### Install
```bash
npx -y @haris-musa/excel-mcp-server
```

### Configuration (opencode.jsonc)
```jsonc
{
  "mcp": {
    "excel-full": {
      "command": ["npx", "-y", "@haris-musa/excel-mcp-server"]
    }
  }
}
```

## Features

### Read Operations
- Read cell values
- Read entire sheets
- Read formulas
- Get metadata

### Write Operations
- Write cell values
- Write formulas
- Create new sheets
- Format cells

### Advanced
- Formulas (SUM, AVERAGE, VLOOKUP, etc.)
- Cell formatting (bold, colors, borders)
- Multiple sheets
- Data validation

## Tools Available

- `read_excel` - Read Excel file
- `write_excel` - Write to Excel
- `create_sheet` - Add new sheet
- `write_formula` - Add formula
- `format_cell` - Format cell style

## Usage Example

```python
# Read Excel
data = await read_excel(
    path="data.xlsx",
    sheet="Sheet1"
)

# Write to Excel
await write_excel(
    path="output.xlsx",
    data={"A1": "Name", "B1": "Age", "A2": "John", "B2": 25}
)

# Add formula
await write_formula(
    path="output.xlsx",
    cell="C1",
    formula="=SUM(A1:A10)"
)
```

## Rating

| Feature | Score |
|---------|-------|
| Free | ✅ 10/10 |
| Functionality | ✅ 10/10 |
| Stars | 3.6k ⭐ |
| Ease of Use | 9/10 |

**Overall: 10/10** — Best Excel MCP, fully free!

## Common Issues

| Issue | Solution |
|-------|----------|
| File not found | Check path |
| Permission denied | Close Excel file first |
| Large file slow | Use paging limit env var |

---
