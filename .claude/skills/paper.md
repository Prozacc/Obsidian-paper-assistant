---
name: paper
description: 处理论文 PDF 或从 arXiv 抓取最新论文，生成 Obsidian 阅读笔记
user_invocable: true
---

# 论文笔记助手

根据用户意图，执行以下操作之一：

## 1. 处理单篇论文

当用户提供一个 PDF 路径时：

```bash
cd D:/code/obsidian-paper-assistant && .venv/Scripts/python.exe tools/process_paper.py "<PDF路径>" --name "<笔记名>"
```

- `<笔记名>` 格式为 `年份 简称`，如 `2025 TiMi`、`2024 Mamba`
- 如果用户没给笔记名，从 PDF 文件名自动推断

## 2. 从 arXiv 抓取最新论文

当用户要求找/抓最新论文时：

```bash
cd D:/code/obsidian-paper-assistant && .venv/Scripts/python.exe tools/fetch_arxiv.py --max <数量> --days <天数>
```

- 默认抓最近 7 天、最多 5 篇
- 可用 `--query` 自定义搜索关键词
- 用户说"找 3 篇" → `--max 3`，"最近两周" → `--days 14`

## 输出位置

- 笔记：`C:\Users\14870\Documents\Obsidian Vault\琅嬛记\02_Research\21_论文阅读笔记\`
- 图片：`C:\Users\14870\Documents\Obsidian Vault\琅嬛记\99_Templates\Attachments\`

## 笔记结构

Frontmatter → 一句话总结 → 核心贡献（Problem/Method/Result）→ 模型架构（详解+公式+图片）→ 实验（简洁）→ 思考（简洁）
