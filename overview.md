# TiMi Skill 运行报告

## 执行流程

1. **PDF 解析** — 使用 `pdf_parser.py` 成功提取 TiMi 论文的文本、图片（10张含caption）、参考文献
2. **LLM 分析** — 基于解析后的 JSON 和精简版 prompt 模板，手动构造 analysis JSON
3. **JSON 清洗** — `llm_analyzer.py` 的 `clean_analysis` 正确规范了作者名、摘要等字段
4. **Markdown 渲染** — `obsidian_writer.py` 成功渲染并写入 Obsidian vault

## 输出文件

`C:\Users\14870\Documents\Obsidian Vault\琅嬛记\02_Research\21_论文阅读笔记\2026 TiMi.md`

## 运行中发现的 Bug（已修复）

| Bug | 原因 | 修复 |
|-----|------|------|
| `$10^{-4}$` 变成 `$$$^{-4}$` | `_restore_latex_backslashes` 的 hallucination 正则误匹配 | lookbehind 加入 `$` |
| `12-18%` 变成 `12-` | `_cleanup_experiments` 的百分比正则误删 | 排除连字符前缀 |
| Problem/Method/Result 中的百分比被删 | `_cleanup_experiments` 被错误应用到这些字段 | 改为只应用 `_cleanup_figure_table_refs` |

## 最终验证

- 66 个单元测试全部通过 ✅
- `$10^{-4}$` 正确保留 ✅
- `12-18%` 正确保留 ✅
- 公式前后有空行 ✅
- `**关键理解：**` 段落正确渲染 ✅
- `> [!quote]` callout 正确显示 ✅
- 实验部分使用 `- **key:** value` 行内格式 ✅
