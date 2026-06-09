---
name: paper
description: Process academic PDFs or fetch arXiv preprints and generate structured Markdown reading notes. Use when the user wants to (1) process a local PDF paper into a reading note, (2) fetch recent papers from arXiv, (3) extract figures and text from a PDF, or (4) generate a structured literature summary. Supports any Markdown-based note-taking workflow (Obsidian, Logseq, Notion, etc.).
user_invocable: true
---

# Paper Assistant (Claude Code Adapter)

This skill wraps the generic `paper-assistant` toolset for Claude Code.

## Prerequisites

```bash
cd <skill-root> && pip install -r requirements.txt
```

## Process a Local PDF

When user provides a PDF path:

```bash
# Step 1: Parse PDF
cd <skill-root> && python scripts/pdf_parser.py "<PDF_PATH>" --out ./output
```

Then read the generated JSON (`output/<stem>/<stem>.json`), use `build_prompt()` from `scripts/llm_analyzer.py` to get the analysis prompt, analyze the paper, and save the result as `output/<stem>/<stem>.analysis.json`.

```bash
# Step 3: Render note
cd <skill-root> && python scripts/obsidian_writer.py ./output/<stem>/<stem>.analysis.json --vault ./output
```

- Note name format: `YYYY ShortName`, e.g. `2025 TiMi`, `2024 Mamba`

## Fetch from arXiv

When user asks to find/fetch recent papers:

```bash
cd <skill-root> && python scripts/fetch_arxiv.py --max <COUNT> --days <DAYS>
```

- Defaults: last 7 days, max 5 papers
- Use `--query` for custom search terms
- User says "find 3 papers" -> `--max 3`, "last two weeks" -> `--days 14`

## Output Directories

- Notes: `$PAPER_VAULT_DIR` (default: `./output`)
- Images: `$PAPER_ATTACHMENTS_DIR` (default: `./output/attachments`)

## Note Structure

Frontmatter -> One-line summary -> Core contributions (Problem/Method/Result) -> Model architecture (detailed + formulas + figures) -> Experiments (concise) -> Thoughts (concise)

## Adapting This Skill

This file is a thin adapter. The core skill definition and all scripts are in the repository root (`SKILL.md` and `scripts/`). To update behavior, edit those files rather than this adapter.
