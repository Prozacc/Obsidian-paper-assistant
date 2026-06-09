---
name: paper-assistant
description: Process academic PDFs or fetch arXiv preprints and generate structured Markdown reading notes. Use when the user wants to (1) process a local PDF paper into a reading note, (2) fetch recent papers from arXiv, (3) extract figures and text from a PDF, or (4) generate a structured literature summary. Supports any Markdown-based note-taking workflow (Obsidian, Logseq, Notion, etc.).
---

# Paper Assistant

Transform academic papers into structured Markdown reading notes.

## What It Does

- **PDF Parsing**: Extract text, sections, references, captions, and figure images from academic PDFs using PyMuPDF.
- **Agent-Native Analysis**: The agent itself analyzes paper content using the built-in prompt template — no external LLM API needed.
- **Markdown Generation**: Render analysis into a templated Markdown note with auto-embedded figures.
- **arXiv Fetching**: Search and download recent arXiv preprints.

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Optional environment variables:

```bash
export PAPER_VAULT_DIR="./output"
export PAPER_ATTACHMENTS_DIR="./output/attachments"
export PAPER_OUTPUT_DIR="./output"
export PAPER_DOWNLOAD_DIR="./papers"
```

## Workflow

### 1. Process a Local PDF

```bash
# Step 1: Parse PDF
python scripts/pdf_parser.py "paper.pdf" --out ./output

# Step 2: Agent reads output/<stem>/<stem>.json, analyzes it,
#         saves as output/<stem>/<stem>.analysis.json

# Step 3: Render note
python scripts/obsidian_writer.py ./output/<stem>/<stem>.analysis.json --vault ./output
```

Or use `process_paper.py` for step 1 + 3:

```bash
# Parse only (agent analyzes in between)
python scripts/process_paper.py "paper.pdf"

# Parse + render (if analysis JSON already exists)
python scripts/process_paper.py "paper.pdf" --analysis ./output/paper/paper.analysis.json --name "2025 TiMi"
```

### 2. Fetch from arXiv

```bash
python scripts/fetch_arxiv.py                                    # last 7 days, 5 papers
python scripts/fetch_arxiv.py --query "transformer" --max 3      # custom query
```

### 3. Step-by-Step

```bash
python scripts/pdf_parser.py "paper.pdf" --out ./output
# Agent analyzes...
python scripts/obsidian_writer.py ./output/paper/paper.analysis.json --vault ./output
```

## Output

- **Note**: `<vault_dir>/<name>.md`
- **Analysis JSON**: `<output_dir>/<paper>/<paper>.analysis.json`
- **Raw JSON**: `<output_dir>/<paper>/<paper>.json`
- **Images**: `<output_dir>/<paper>/images/png/*.png`

## Customization

- **Note template**: Edit `assets/paper-note.md`
- **Analysis style guide**: Edit `references/style-guide.md`
- **Journal abbreviations**: Edit `_simplify_journal()` in `scripts/obsidian_writer.py`

## Agent CLI Adaptation

| Agent | Location | Notes |
|-------|----------|-------|
| **Claude Code** | `.claude/skills/paper.md` | Skill adapter in this repo |
| **Kimi Code CLI** | `.kimi/skills/paper-assistant/` | Copy to `~/.kimi/skills/` |
| **Other** | Agent's skills directory | Copy `SKILL.md` + `scripts/` + `assets/` + `references/` |
