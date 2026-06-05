# Obsidian Paper Assistant

Utilities for parsing academic PDFs into structured JSON and extracting figure
images for downstream note-taking workflows such as Obsidian.

## Contents

- `tools/pdf_parser.py`: PyMuPDF-based parser for text, sections, references,
  captions, and figure image crops.
- `tools/llm_analyzer.py`: optional LLM-based second-pass analyzer for parsed
  paper JSON.
- `output/`: sample parsed outputs and extracted images.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install pymupdf openai
```

`openai` is only required for `tools/llm_analyzer.py`.

## Parse a PDF

```powershell
.\.venv\Scripts\python.exe tools\pdf_parser.py "path\to\paper.pdf" --out output
```

The parser writes:

- `output/<paper>/<paper>.json`
- `output/<paper>/images/png/*.png`

## Analyze Parsed JSON With DeepSeek

Set the API key in your shell instead of hard-coding it:

```powershell
$env:DEEPSEEK_API_KEY="your_api_key"
$env:DEEPSEEK_MODEL="deepseek-chat"
.\.venv\Scripts\python.exe tools\llm_analyzer.py output\DUET\DUET.json --out output\DUET\DUET.analysis.json
```
