# obsidian-paper-assistant 项目记忆

## 项目结构
- `scripts/pdf_parser.py` — PDF 解析（PyMuPDF）
- `scripts/llm_analyzer.py` — Prompt 模板 + JSON 清洗
- `scripts/obsidian_writer.py` — Markdown 渲染引擎
- `references/style-guide.md` — 笔记风格指南
- `assets/paper-note.md` — Markdown 模板

## 关键配置（.env）
- `PAPER_VAULT_DIR` — Obsidian 笔记输出目录
- `PAPER_ATTACHMENTS_DIR` — 图片附件目录
- `PAPER_IMAGE_ENGINE=pymupdf`
- `PAPER_LANG=zh`

## 工作流程
1. `python scripts/pdf_parser.py "paper.pdf" --out ./output` → 解析 PDF
2. 读取 `output/<stem>/<stem>.json`，使用 `llm_analyzer.build_prompt()` 构造 prompt
3. LLM 分析后保存为 `output/<stem>/<stem>.analysis.json`
4. `python scripts/obsidian_writer.py analysis.json --vault ... --images-dir ...` → 渲染 Markdown

## 已知修复（2026-06-11）
- `_cleanup_experiments` 不再应用到 problem/method/result 字段
- `_restore_latex_backslashes` 不再误删 LaTeX 中的小数字（如 $10^{-4}$）
- 百分比清理正则不再误删范围表达（如 12-18%）
- Prompt 从 ~170 行精简到 ~80 行
- 新增 `_normalize_numbered_lists`、`_ensure_paragraph_breaks`、`_normalize_experiments_format`
- 模板新增 `> [!quote] 这一部分最重要。` callout
- 图片自动嵌入：描述性文件名 `{paper}_fig{N}.png`、从 figure_notes 生成 blockquote caption、heading 语义匹配位置
- `_cleanup_figure_table_refs` 和 `_cleanup_architecture` 添加 Obsidian embed 保护（placeholder 机制），不再误删/误改 `![[]]` 嵌入

## 注意事项
- 安装 PyMuPDF: `pip install PyMuPDF`（需要安装到隔离环境）
- 测试: `pytest tests/test_llm_analyzer.py tests/test_obsidian_writer.py -v`
- `pdf_parser.py` 测试需要 PyMuPDF，如果未安装会跳过
