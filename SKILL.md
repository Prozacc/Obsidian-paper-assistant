---
name: paper-assistant
description: Process academic PDFs or fetch arXiv preprints and generate structured Markdown reading notes. Use when the user wants to (1) process a local PDF paper into a reading note, (2) fetch recent papers from arXiv, (3) extract figures and text from a PDF, or (4) generate a structured literature summary. Supports any Markdown-based note-taking workflow (Obsidian, Logseq, Notion, etc.).
---

# Paper Assistant

Turn any academic PDF into a structured Markdown reading note with extracted figures and AI-powered analysis — no external LLM API needed.

## Installation

```bash
git clone https://github.com/Prozacc/Obsidian-paper-assistant.git
cd Obsidian-paper-assistant
pip install -r requirements.txt
```

## Configuration

```bash
export PAPER_VAULT_DIR="./output"              # Where .md notes go
export PAPER_ATTACHMENTS_DIR="./output/attachments"  # Figure images for embeds
export PAPER_OUTPUT_DIR="./output"              # Intermediate files
export PAPER_DOWNLOAD_DIR="./papers"            # arXiv downloads
export PAPER_IMAGE_ENGINE="pymupdf"             # "pymupdf" or "pillow" (300 DPI)
export PAPER_LANG="zh"                          # "zh" or "en"
```

## Agent Workflow

When an AI agent processes a paper, it must complete ALL 3 steps:

### Step 1: Parse PDF → Structured JSON + Figures

```bash
python scripts/pdf_parser.py "paper.pdf" --out ./output
```

Output: `output/<stem>/<stem>.json` + extracted figures in `output/<stem>/images/png/`

### Step 2: Agent Analysis → Analysis JSON

The agent reads the parsed JSON, deeply analyzes the paper content, and saves:

```bash
# Agent writes: output/<stem>/<stem>.analysis.json
```

Required fields: title, authors, year, journal, abstract, summary, tldr, problem, method, result, architecture, innovations, experiments, thoughts, figure_notes, limitations, topics, aliases, related_papers

**Figure embedding:** In the `architecture` and `experiments` fields, include explicit figure references like "如图1所示" or "Figure 1 shows". The renderer auto-detects these and embeds extracted PNGs as `![[Pasted image ...]]`.

**Figure notes:** The `figure_notes` field should list the paper's key figures/tables with 1-2 sentence descriptions each. PDF-extracted images are auto-attached.

### Step 3: Render → Markdown Note

```bash
python scripts/obsidian_writer.py ./output/<stem>/<stem>.analysis.json --vault "$PAPER_VAULT_DIR" --images-dir ./output/<stem>/images/png --attachments-dir "$PAPER_ATTACHMENTS_DIR"
```

Output: A complete Obsidian-compatible `.md` note with YAML frontmatter, auto-embedded figures, and structured sections.

## Fetch from arXiv

```bash
python scripts/fetch_arxiv.py --query "transformer time series" --max 5 --days 7
```

## Analysis Style Guide

- Output in the target language (Chinese by default), preserve English technical terms
- **Architecture** is the most important section: detail each module (why this design, what problem it solves), include formulas in LaTeX `$...$`, use callouts for tricky concepts. Reference the paper's architecture diagram.
- **Experiments**: datasets, baselines, key findings with critical numbers. Reference key result charts by figure number.
- **figure_notes**: list the paper's key figures/tables, 1-2 sentence descriptions each
- Thoughts: first person perspective, 1-2 points, can be empty

## Customization

- **Note template**: Edit `assets/paper-note.md`
- **Analysis style guide**: Edit `references/style-guide.md`
- **Journal abbreviations**: Edit `_simplify_journal()` in `scripts/obsidian_writer.py`

## As an AI Agent Skill

After cloning, install the skill to your agent's skills directory:

| Agent | Command |
|---|---|
| **Reasonix** | `mkdir -p .reasonix/skills/paper-assistant && cp SKILL.md .reasonix/skills/paper-assistant/` |
| **Claude Code** | `cp SKILL.md .claude/skills/paper-assistant/SKILL.md` |
| **Kimi Code** | `mkdir -p ~/.kimi/skills/paper-assistant && cp SKILL.md ~/.kimi/skills/paper-assistant/` |

Then tell your agent: *"Analyze this paper: paper.pdf"*
