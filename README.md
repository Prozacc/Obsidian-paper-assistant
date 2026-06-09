# 📄 Paper Assistant

<p align="center">
  <b>PDF → Structured Markdown Reading Notes · Zero External LLM API Cost</b>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
  <a href="#"><img src="https://img.shields.io/badge/python-3.10+-green.svg" alt="Python"></a>
  <a href="#"><img src="https://img.shields.io/badge/code%20style-ruff-261230.svg" alt="Ruff"></a>
  <img src="https://img.shields.io/badge/tests-61%20passed-brightgreen.svg" alt="Tests">
  <img src="https://img.shields.io/badge/agent-Claude%20%7C%20Kimi%20%7C%20Reasonix-purple.svg" alt="Agent support">
</p>

---

Turn any academic PDF into a beautifully structured Markdown reading note — with extracted figures, LaTeX formulas, and AI-powered analysis. Works as a **standalone CLI tool** or as an **AI agent skill** (Claude Code / Kimi Code / Reasonix).

> **Why agent-native?** The AI agent does the "reading comprehension" itself — no external LLM API calls. Your existing agent's intelligence is the only inference cost.

## ✨ Features

| Feature | Description |
|---|---|
| 🔬 **Dual-Engine PDF Parsing** | PyMuPDF for text + pdf2image/Pillow for high-res figure extraction |
| 🧠 **Agent-Native Analysis** | Structured prompts guide your AI agent to produce deep paper analysis |
| 📝 **Obsidian-Ready Output** | YAML frontmatter + Callout syntax + auto-embedded figures |
| 🔍 **arXiv Fetcher** | Search and download recent preprints by keyword |
| 🌐 **Multi-Language** | Prompt templates in Chinese and English (`PAPER_LANG=en`) |
| ⚡ **Online Learning** | Partial retraining strategy for rolling-window forecasting research |
| 🧪 **Tested** | 61 unit tests across all core modules |

## 🚀 5-Second Start

```bash
git clone https://github.com/Prozacc/Obsidian-paper-assistant.git
cd Obsidian-paper-assistant
pip install -r requirements.txt

# Process a paper in one command
python scripts/process_paper.py "paper.pdf" --name "My Reading Note"
```

## 📖 How It Works

```
PDF paper
    │
    ▼
┌──────────────────┐
│  pdf_parser.py   │  ← PyMuPDF (text) + Pillow (figures at 300 DPI)
│  dual-engine     │
└──────┬───────────┘
       │  paper.json + figure PNGs
       ▼
┌──────────────────┐
│  AI Agent        │  ← Your Claude / Kimi / Reasonix reads the JSON,
│  (you)           │     analyzes with structured prompts from llm_analyzer.py
└──────┬───────────┘
       │  paper.analysis.json
       ▼
┌──────────────────┐
│  obsidian_writer │  ← Template rendering + figure auto-embed
└──────┬───────────┘
       │
       ▼
   📄 paper.md      ← Drop into Obsidian, ready to read
```

### Manual Step-by-Step

```bash
# Step 1: Parse PDF → structured JSON + extracted figures
python scripts/pdf_parser.py "paper.pdf" --out ./output

# Step 2: Agent reads output/<paper>/<paper>.json and writes analysis JSON
# (your AI assistant handles this)

# Step 3: Render Markdown note
python scripts/obsidian_writer.py ./output/<paper>/<paper>.analysis.json --vault ./output
```

## 🎮 As an AI Agent Skill

Drop `SKILL.md` + `scripts/` + `assets/` + `references/` into your agent's skills directory:

| Agent | Install |
|---|---|
| **Reasonix** | `/skill new paper-assistant` or copy to `.reasonix/skills/` |
| **Claude Code** | `.claude/skills/paper.md` (included) |
| **Kimi Code** | `.kimi/skills/paper-assistant/` (included) |

Then just say: *"Analyze this paper: attention.pdf"*

## ⚙️ Configuration

```bash
export PAPER_VAULT_DIR="./output"           # Where .md notes go
export PAPER_ATTACHMENTS_DIR="./output/attachments"  # Image attachments
export PAPER_OUTPUT_DIR="./output"           # Intermediate JSON files
export PAPER_DOWNLOAD_DIR="./papers"         # Downloaded arXiv PDFs
export PAPER_IMAGE_ENGINE="pillow"           # "pymupdf" (default) or "pillow" (high-res)
export PAPER_LANG="zh"                       # Analysis language: "zh" or "en"
```

## 📊 Example Output

```
obisidian-paper-assistant/output/
├── AdaptiveMoE.md              ← Final reading note (drop into Obsidian)
├── AdaptiveMoE/
│   ├── AdaptiveMoE.json        ← Raw parsed paper data
│   ├── AdaptiveMoE.analysis.json ← AI agent's structured analysis
│   └── images/png/
│       ├── figure_1_architecture.png
│       └── figure_2_results.png
```

The generated `.md` note includes:

- **YAML frontmatter** with authors, year, journal, topics, related papers
- **TL;DR** one-sentence summary
- **Problem → Method → Result** structured bullets
- **Architecture deep-dive** with LaTeX formulas and `> [!question]` callouts
- **Experiments** summary with key metrics
- **Personal thoughts** section
- **Auto-embedded figures** referenced in text

## 🧪 Development

```bash
pip install -e ".[dev]"
pytest tests/ -v     # 61 tests
ruff check scripts/  # Lint
```

## 📦 Project Structure

```
paper-assistant/
├── SKILL.md                    # Agent skill definition
├── scripts/
│   ├── pdf_parser.py           # Dual-engine PDF → JSON + PNGs
│   ├── llm_analyzer.py         # Prompt templates (zh/en) + JSON cleanup
│   ├── obsidian_writer.py      # JSON → Obsidian Markdown
│   ├── process_paper.py        # One-command pipeline
│   └── fetch_arxiv.py          # arXiv search & download
├── tests/                      # 61 unit tests
├── assets/paper-note.md        # Note template
├── references/style-guide.md   # Analysis quality standards
└── pyproject.toml
```

## 🙏 Acknowledgments

Built with:
- [PyMuPDF](https://pymupdf.readthedocs.io/) for PDF text extraction
- [pdf2image](https://github.com/Belval/pdf2image) + [Pillow](https://python-pillow.org/) for figure extraction
- [Obsidian](https://obsidian.md/) as the target note-taking environment

## 📄 License

MIT — use it, fork it, build on it.
