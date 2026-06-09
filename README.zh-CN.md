# 📄 Paper Assistant

<p align="center">
  <b>PDF → 结构化 Markdown 阅读笔记 · 零外部 LLM API 成本</b>
</p>

<p align="center">
  <a href="README.md">English</a> &nbsp;·&nbsp; <strong>简体中文</strong>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
  <a href="#"><img src="https://img.shields.io/badge/python-3.10+-green.svg" alt="Python"></a>
  <img src="https://img.shields.io/badge/tests-61%20passed-brightgreen.svg" alt="Tests">
  <img src="https://img.shields.io/badge/agent-Reasonix%20%7C%20Claude%20%7C%20Kimi-purple.svg" alt="Agent support">
</p>

---

把任意学术 PDF 变成结构精美的 Markdown 阅读笔记——带提取的图表、LaTeX 公式和 AI 深度分析。既可以作为**独立 CLI 工具**使用，也可以作为 **AI Agent Skill**（Reasonix / Claude Code / Kimi Code）调用。

> **为什么叫 Agent-Native？** AI 助手自己完成"阅读理解"——不调用外部 LLM API。你已有的 Agent 智能是唯一的推理成本。

## ✨ 功能

| 功能 | 说明 |
|---|---|
| 🔬 **双引擎 PDF 解析** | PyMuPDF 提取文本 + pdf2image/Pillow 高清图表提取（300 DPI） |
| 🧠 **Agent-Native 分析** | 结构化提示词引导 AI 助手产出深度论文分析 |
| 📝 **Obsidian 就绪输出** | YAML frontmatter + Callout 语法 + 图片自动嵌入 |
| 🔍 **arXiv 抓取** | 按关键词搜索并下载最新预印本 |
| 🌐 **多语言** | 中英文提示词模板（`PAPER_LANG=zh` 或 `en`） |
| 🧪 **测试覆盖** | 61 个单元测试覆盖全部核心模块 |

## 🚀 5 秒上手

```bash
git clone https://github.com/Prozacc/Obsidian-paper-assistant.git
cd Obsidian-paper-assistant
pip install -r requirements.txt

# 一键处理论文
python scripts/process_paper.py "paper.pdf"
```

## 📖 工作原理

```
PDF 论文
    │
    ▼
┌──────────────────┐
│  pdf_parser.py   │  ← PyMuPDF (文本) + Pillow (图表 300 DPI)
│  双引擎           │
└──────┬───────────┘
       │  paper.json + 提取的 PNG 图片
       ▼
┌──────────────────┐
│  AI 助手         │  ← Reasonix / Claude / Kimi 读取 JSON，
│  (你的 Agent)    │    按 llm_analyzer.py 的结构化提示词分析
└──────┬───────────┘
       │  paper.analysis.json
       ▼
┌──────────────────┐
│  obsidian_writer │  ← 模板渲染 + 图片自动嵌入
└──────┬───────────┘
       │
       ▼
   📄 paper.md      ← 拖进 Obsidian，直接阅读
```

### 分步操作

```bash
# 第一步：解析 PDF → 结构化 JSON + 提取图表
python scripts/pdf_parser.py "paper.pdf" --out ./output

# 第二步：AI 助手读取 output/<paper>/<paper>.json 并写入分析结果
# （你的 AI 助手完成这一步）

# 第三步：渲染 Markdown 笔记
python scripts/obsidian_writer.py ./output/<paper>/<paper>.analysis.json --vault ./output
```

## 🎮 作为 AI Agent Skill 使用

clone 项目后，按以下方式安装为 AI 助手的 Skill：

### Reasonix

```bash
mkdir -p .reasonix/skills/paper-assistant
cp SKILL.md .reasonix/skills/paper-assistant/SKILL.md
```

或在应用内输入 `/skill new paper-assistant` 并粘贴 `SKILL.md` 内容。

### Claude Code

```bash
cp SKILL.md .claude/skills/paper.md
```

### Kimi Code

```bash
mkdir -p ~/.kimi/skills/paper-assistant
cp SKILL.md ~/.kimi/skills/paper-assistant/SKILL.md
```

然后直接说：*"帮我分析这篇论文 attention.pdf"*

## ⚙️ 配置

```bash
export PAPER_VAULT_DIR="./output"              # Markdown 笔记输出目录
export PAPER_ATTACHMENTS_DIR="./output/attachments"  # 图片附件目录
export PAPER_OUTPUT_DIR="./output"              # 中间 JSON 文件目录
export PAPER_DOWNLOAD_DIR="./papers"            # arXiv 下载目录
export PAPER_IMAGE_ENGINE="pillow"              # "pymupdf"（默认）或 "pillow"（高清）
export PAPER_LANG="zh"                          # 分析语言："zh" 或 "en"
```

## 📊 示例输出

```
obisidian-paper-assistant/output/
├── AdaptiveMoE.md              ← 最终阅读笔记（拖进 Obsidian）
├── AdaptiveMoE/
│   ├── AdaptiveMoE.json        ← 原始解析数据
│   ├── AdaptiveMoE.analysis.json ← AI 助手的结构化分析
│   └── images/png/
│       ├── figure_1_architecture.png
│       └── figure_2_results.png
```

生成的 `.md` 笔记包含：

- **YAML frontmatter** — 作者、年份、期刊、主题、相关论文
- **TL;DR** — 一句话核心贡献
- **Problem → Method → Result** — 结构化分层
- **Architecture 深入解析** — LaTeX 公式 + `> [!question]` Callout 解释框
- **Experiments** — 数据集、Baseline、关键指标
- **个人思考** — "我"的第一人称视角
- **图片自动嵌入** — 文中引用图号自动匹配

## 🧪 开发

```bash
pip install -e ".[dev]"
pytest tests/ -v     # 61 个测试
```

## 📦 项目结构

```
paper-assistant/
├── SKILL.md                    # Agent Skill 定义
├── scripts/
│   ├── pdf_parser.py           # 双引擎 PDF → JSON + PNG
│   ├── llm_analyzer.py         # 中英文提示词模板 + JSON 清洗
│   ├── obsidian_writer.py      # JSON → Obsidian Markdown
│   ├── process_paper.py        # 一键管线
│   └── fetch_arxiv.py          # arXiv 搜索与下载
├── tests/                      # 61 个单元测试
├── assets/paper-note.md        # 笔记模板
├── references/style-guide.md   # 分析质量规范
└── pyproject.toml
```

## 🙏 致谢

基于以下开源项目构建：
- [PyMuPDF](https://pymupdf.readthedocs.io/) — PDF 文本提取
- [pdf2image](https://github.com/Belval/pdf2image) + [Pillow](https://python-pillow.org/) — 图表提取
- [Obsidian](https://obsidian.md/) — 目标笔记环境

## 📄 许可

MIT — 随便用，随便改，随便 fork。
