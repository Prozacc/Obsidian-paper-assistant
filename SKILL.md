---
name: paper-assistant
description: Parse academic PDFs or arXiv papers and generate structured Obsidian Markdown reading notes with selected figures. Use when the user asks to analyze a paper, extract its architecture and experiments, or create a literature reading note from a PDF.
---

# Paper Assistant

Generate research-oriented paper notes that match the user's existing Obsidian style.

## Workflow

1. Parse the PDF:

```bash
python scripts/pdf_parser.py "paper.pdf" --out ./output
```

2. Read `output/<stem>/<stem>.json` and generate every field required by `AnalysisResult` in `scripts/llm_analyzer.py`.

3. Before writing the analysis JSON, read [references/style-guide.md](references/style-guide.md). Treat it as the user's note convention.

4. Save the analysis as `output/<stem>/<stem>.analysis.json`.

5. Render the note:

```bash
python scripts/obsidian_writer.py output/<stem>/<stem>.analysis.json --vault "$PAPER_VAULT_DIR" --images-dir output/<stem>/images/png --attachments-dir "$PAPER_ATTACHMENTS_DIR"
```

## Required Behavior

- Preserve the complete original English abstract. If extraction is incomplete, prefer a more complete abstract candidate already present in the parsed data.
- Make the architecture section the main body. Explain module motivation, data flow, tensor shapes, formulas, symbols, and intuition.
- Keep Problem, Method, Result, and experiments concise. Do not repeat labels already owned by the template.
- Use `- ` dash bullets for sub-lists in Problem/Method/Result; do NOT use numbered lists (`1. `).
- Use inline format for experiments: `- **数据集:** Weather、Traffic` not multi-line expanded lists.
- Select only 3-5 useful figures. Each image must follow the sentence that discusses it.
- Never invent metrics, URLs, citekeys, Zotero links, or personal reflections.
- Leave missing optional content empty or use `（待补充）`; do not emit isolated `- 无` bullets or blank link labels.
- Match existing vault conventions before introducing a new heading, tag, or frontmatter style.

## Output Contract

The analysis JSON must contain:

`title`, `authors`, `year`, `journal`, `abstract`, `summary`, `tldr`, `problem`, `method`, `result`, `architecture`, `innovations`, `experiments`, `thoughts`, `figure_notes`, `limitations`, `topics`, `aliases`, `related_papers`.

Use `scripts/llm_analyzer.py` for prompt construction and normalization, then `scripts/obsidian_writer.py` for deterministic rendering.
