---
title: "{{title}}"
type: paper-note
status: active
review_status: summarized
created: "{{exportDate | format('YYYY-MM-DD')}}"
updated: "{{exportDate | format('YYYY-MM-DD')}}"
authors:
{{authors_yaml}}
year: "{{date | format('YYYY')}}"
journal: "{{publicationTitle}}"
citekey: "{{citekey}}"
zotero_link: "{{zoteroSelectURI}}"
source: "ai_summary"
topic:
{{topics}}
project: []
tags:
  - paper
  - 论文阅读
  - "year/{{date | format('YYYY')}}"
aliases:
{{aliases}}
related:
{{related_papers}}
---

# 📖 {{title}}

> [!abstract] **摘要**
> {{abstractNote}}

---
## 🚀 核心贡献 (TL;DR)
*{{tldr}}*

{{problem}}

{{method}}

{{result}}

---
## 🧠 模型/算法架构
> [!tip] 重点：关注模型输入输出形状、Loss Function、创新模块。

{{architecture}}

---
## 📊 实验与结果
{{experiments}}

## 💡 个人思考与启发
> [!quote] 这篇论文已经进入我的研究坐标系了

{{thoughts}}

---
## 🔗 参考文献与链接
- **PDF 附件:** {{desktopURI}}
- **代码链接:**
