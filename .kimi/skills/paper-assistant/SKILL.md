---
name: paper-assistant
description: Process academic PDFs or fetch arXiv preprints and generate structured Markdown reading notes. Use when the user wants to (1) process a local PDF paper into a reading note, (2) fetch recent papers from arXiv, (3) extract figures and text from a PDF, or (4) generate a structured literature summary. Supports any Markdown-based note-taking workflow (Obsidian, Logseq, Notion, etc.).
---

# Paper Assistant (Kimi Code CLI Adapter)

This skill wraps the generic `paper-assistant` toolset for Kimi Code CLI.

## Bundled Resources

- `scripts/` — Executable Python scripts for PDF parsing, analysis utilities, and Markdown generation
- `assets/paper-note.md` — Markdown note template
- `references/style-guide.md` — Analysis style guide

## Prerequisites

Install dependencies in the skill directory:

```bash
cd ~/.kimi/skills/paper-assistant && pip install -r requirements.txt
```

## Agent-Native Workflow

This skill uses an agent-native architecture — the agent itself analyzes papers, no external LLM API needed.

### Process a Local PDF

```bash
# Step 1: Parse PDF
cd ~/.kimi/skills/paper-assistant && python scripts/pdf_parser.py "<PDF_PATH>" --out ./output

# Step 2: Agent reads paper.json, analyzes it, saves paper.analysis.json

# Step 3: Render note
cd ~/.kimi/skills/paper-assistant && python scripts/obsidian_writer.py ./output/<stem>/<stem>.analysis.json --vault ./output
```

### Fetch from arXiv

```bash
cd ~/.kimi/skills/paper-assistant && python scripts/fetch_arxiv.py --max <COUNT> --days <DAYS>
```

### Optional Directory Overrides

```bash
export PAPER_VAULT_DIR="./output"
export PAPER_ATTACHMENTS_DIR="./output/attachments"
```

## Adapting This Skill

This file is a thin adapter. The core skill definition and all scripts are in the repository root (`SKILL.md` and `scripts/`). To update behavior, edit those files rather than this adapter.
