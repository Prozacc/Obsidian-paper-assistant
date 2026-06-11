---
title: "TiMi: Empower Time Series Transformers with Multimodal Mixture of Experts"
type: paper-note
status: active
review_status: summarized
created: 2026-06-11
updated: 2026-06-11
authors:
  - Jiafeng Lin
  - Yuxuan Wang
  - Huakun Luo
  - Zhongyi Pei
  - Jianmin Wang
year: 2026
journal: arXiv:2602.21693
citekey: ""
zotero_link: ""
source: ai_summary
topic:
  - time-series
  - multimodal
  - mixture-of-experts
  - LLM
  - forecasting
project: []
tags:
  - paper
  - 论文阅读
  - 2026
aliases:
  - TiMi
related:
  - PatchTST
  - iTransformer
  - Time-MMD
  - Time-LLM
  - Autoformer
  - TimeXer
  - IMM-TSF
  - GPT4TS
---

# 📖 TiMi: Empower Time Series Transformers with Multimodal Mixture of Experts

> [!abstract] **摘要**
> Multimodal time series forecasting has garnered significant attention for its potential to provide more accurate predictions than traditional singlemodality models by leveraging rich information inherent in other modalities. However, due to fundamental challenges in modality alignment, existing methods often struggle to effectively incorporate multimodal data into predictions, particularly textual information that has a causal influence on time series fluctuations, such as emergency reports and policy announcements. In this paper, we reflect on the role of textual information in numerical forecasting and propose Time series transformers with Multimodal Mixture-ofExperts, TiMi, to unleash the causal reasoning capabilities of LLMs. Concretely, TiMi utilizes LLMs to generate inferences on future developments, which serve as guidance for time series forecasting. To seamlessly integrate both exogenous factors and time series into predictions, we introduce a Multimodal Mixture-of-Experts (MMoE) module as a lightweight plug-in to empower Transformer-based time series models for multimodal forecasting, eliminating the need for explicit representation-level alignment. Experimentally, our proposed TiMi demonstrates consistent state-of-the-art performance on sixteen real-world multimodal forecasting benchmarks, outperforming advanced baselines while offering both strong adaptability and interpretability.

---
## 🚀 核心贡献 (TL;DR)
*TiMi 利用冻结 LLM 对文本做因果推理生成未来趋势 embedding，通过双路由 MoE（TMoE+SMoE）将文本因果知识与历史时序全局表征分别注入 Transformer，在 16 个多模态基准上全面领先。*
- **Problem:** 现有多模态时序预测方法在融合文本信息时面临两个核心问题：
- 跨模态语义不对齐：视觉-语言数据天然具有语义对应，但时序-文本之间没有直接对齐关系，文本（如紧急报告、政策公告）与数值序列的时间戳不一定一一对应；
- LLM 因果推理能力未被充分利用：现有 Early Fusion 方法将时序嵌入 LLM 空间但破坏了时序结构，Late Fusion 方法在表征层做简单拼接，无法充分提取文本中的因果知识来指导预测。
- **Method:** TiMi 以时序为中心，通过双路由 MoE 模块融合文本因果知识：
- 冻结 LLM（Qwen2.5-7B）对文本做趋势/频率/噪声三维推理，生成聚合 textual token；
- TMoE 以文本表征为路由输入，动态选择专家组合，将因果知识注入时序建模；
- SMoE 以时序全局表征为路由输入，按趋势类型分组选择专家，增强时序自身建模能力；
- MMoE 作为即插即用模块，可替换任意 Transformer 中的 FFN。
- **Result:** TiMi 在 Time-MMD 九个数据集和 Time-IMM 七个不规则数据集上全面取得 SOTA，MMoE 作为即插即用模块在 PatchTST、TimeXer、Autoformer 上均带来一致提升，SMoE 的路由结果与 Mann-Kendall 趋势检验高度一致，证实了模型的可解释性。

## 🧠 模型/算法架构
> [!tip] 重点：关注模型输入输出形状、Loss Function、创新模块。

### 1. 整体思路

TiMi 的核心洞察是：**文本对时序的影响不是表征层面的对齐，而是因果层面的指导**。作者认为，现有方法试图将文本和时序嵌入到同一表征空间的做法是走弯路——文本的价值在于提供对未来的因果推理（如"政策收紧将导致消费下降"），这种推理应该以"指导"而非"对齐"的方式融入时序模型。

数据流如下：
1. 文本 $T$ 经冻结 LLM 编码后平均池化，得到 textual representation $\bar{H}$
2. 时序 $x_{1:L}$ 经 patching + embedding 后输入 Transformer
3. Transformer 每个 block 中，FFN 被 MMoE 替换：先做 Self-Attention，再做 MMoE
4. MMoE 内部包含 TMoE 和 SMoE 两条路由路径，分别以文本表征和时序全局表征为路由依据
5. 两条路径的输出相加，经过 LayerNorm 后得到该 block 的输出

$$\hat{h}_l = \text{LayerNorm}(h_{l-1} + \text{Self-Attention}(h_{l-1}))$$

$$h_l = \text{LayerNorm}(\hat{h}_l + \text{MMoE}(\hat{h}_l, \bar{H}))$$

注意 MMoE 的位置：它替换的是 Transformer block 中的 FFN（即 Self-Attention 之后），而不是与 Self-Attention 并行。这意味着时序建模和跨模态融合是解耦的——Self-Attention 负责时序内部依赖，MMoE 负责引入外部知识。

### 2. 文本编码与多维度推理

**冻结 LLM 的设计选择**

TiMi 使用 Qwen2.5-7B 作为文本编码器，且**冻结其全部参数**。这不是出于计算效率的妥协，而是基于一个关键设计考量：LLM 的预训练知识是核心资产，微调可能破坏其推理能力。

**多维度推理 prompt**

作者设计了一套结构化 prompt，引导 LLM 从三个维度推理文本对未来时序的影响：
- **Trend**：整体上升/下降趋势
- **Frequency**：周期性和季节性变化
- **Noise**：随机波动和异常

每个维度提供选项式回答（如 Trend: A. Strong upward / B. Weak upward / C. Weak downward / D. Strong downward），将 LLM 的自由生成约束为结构化输出，降低噪声。

**聚合过程**

LLM 的最后一层 hidden state 通过平均池化压缩为单个 textual token：

$$\bar{H} = \text{AvgPool}(\text{LLM}(T))$$

这一步将变长文本压缩为固定维度表征，包含 LLM 对未来趋势的多维度推理信息。平均池化意味着所有 token 的信息被平等保留，而不是只取 CLS token——这是因为时序预测需要文本中所有时间点的信息，而不只是全局摘要。

**关键理解：**
- TiMi 不在表征层做跨模态对齐，而是利用 LLM 的推理能力提取因果知识，让 MoE 在功能层面选择"怎么用"这些知识
- 结构化 prompt 将 LLM 的输出从自由文本约束为多维选项，这既降低了生成噪声，又使得推理结果可解释

TiMi 整体架构——LLM 编码文本生成推理 embedding，时序经 Transformer+MMoE 建模，TMoE 和 SMoE 分别路由后相加

![[TiMi_fig3.png]]

### 3. Text-Informed Mixture of Experts (TMoE)

**设计动机**

TMoE 要解决的核心问题是：如何让时序模型"听懂"文本中关于未来的因果推理？直接拼接或交叉注意力要么语义不对齐，要么计算代价大。TMoE 的做法是**用文本表征来路由专家**——让文本决定"激活哪些变换"。

**路由机制**

TMoE 的 Router 以文本表征 $\bar{H}$ 为输入，输出专家选择概率：

$$g_{\text{TMoE}} = \text{Softmax}(W_g \cdot \bar{H})$$

其中 $W_g$ 是可学习的路由权重。选取 Top-$k$ 个专家，对选中专家的输出做加权求和：

$$\text{TMoE}(\hat{h}_l, \bar{H}) = \sum_{i \in \text{Top-}k} g_i \cdot \text{FFN}_i(\hat{h}_l)$$

**关键区别于标准 MoE**

标准 MoE 的路由输入是当前 token 自身，而 TMoE 的路由输入是**外部文本表征** $\bar{H}$。这意味着：不同文本内容会激活不同的专家组合，而同一个 batch 内的时序 token 共享同一路由决策。这实质上是让文本"指挥"时序变换的方向——如果文本暗示"未来趋势下降"，TMoE 会选择擅长处理下降趋势的专家。

**Prior 机制**

TMoE 还引入了一个 Prior 项，用于平衡路由的负载，确保所有专家都有机会被训练，避免路由坍缩到少数专家。

**关键理解：**
- TMoE 的路由输入是文本而非时序，这是它与标准 MoE 的根本区别——它实现了"文本指导时序"的范式
- 同一 batch 内所有时序 token 共享文本路由决策，这意味着文本的影响是全局的、一致的，不会在不同 patch 间产生冲突

SMoE 路由可视化——被路由到同一专家的时序呈现相似趋势，与 MK 检验 Z 统计量一致

![[TiMi_fig7.png]]

### 4. Series-Aware Mixture of Experts (SMoE)

**设计动机**

如果只有 TMoE，时序模型会完全依赖文本来指导建模，但文本并非总是可用的、也并非总是可靠的。SMoE 的作用是**从时序自身提取全局趋势信息**，让模型在文本缺失或噪声大时也能做出合理的专家选择。

**路由机制**

SMoE 的路由输入不是单个 token，而是**时序的全局表征**。具体做法是将所有时序 token flatten 后通过一个线性层：

$$r_{\text{SMoE}} = \text{Softmax}(W_s \cdot \text{Flatten}(\hat{h}_l))$$

这里 Flatten 操作将 $N$ 个时序 token 的表征展平后投影，得到一个全局路由向量。这意味着路由决策考虑的是整个时序序列的趋势特征，而非单个 patch 的局部特征。

**可解释性验证**

作者对 SMoE 的路由结果做了可视化分析，发现被路由到同一专家的时序样本确实呈现出相似的全局趋势。为了量化验证这一点，作者使用 Mann-Kendall 趋势检验计算了 Z 统计量，发现路由结果与趋势分类高度一致——强上升趋势、弱上升趋势、弱下降趋势、强下降趋势分别被路由到不同专家。

**关键理解：**
- SMoE 实现了一种数据驱动的趋势感知分组，无需显式标签即可自动发现时序的全局趋势模式
- TMoE 和 SMoE 互补：TMoE 提供"未来会怎样"的外部知识，SMoE 提供"过去是什么样"的内部知识，两者共同决定专家选择

### 5. 训练与优化

**损失函数**：标准 L2 (MSE) 损失，用于回归预测

**优化器**：AdamW，初始学习率 $10^{-4}$

**训练策略**：固定 10 个 epoch + early stopping；Time-IMM 数据集使用 Time-IMM 原始设定的 early stopping

**Batch size**：根据数据集规模调整

**模型维度**：series representation 维度从 {128, 256, 512} 中选择，LLM 隐藏维度为 3584（Qwen2.5-7B）

**关键设计选择**：LLM 完全冻结，不参与梯度更新，仅作为文本特征提取器。这大幅减少了训练参数量，同时保留了 LLM 的预训练知识。

### 关键创新
- 提出 Non-Fusion 范式：不追求表征层对齐，而是利用 LLM 因果推理能力生成未来趋势指导，通过 MoE 在功能层面融合
- 设计双路由 MoE（TMoE+SMoE）：文本路由提供因果知识，时序路由提供全局趋势感知，互补地增强预测
- MMoE 作为即插即用模块替换 Transformer FFN，可适配多种骨干网络，无需修改架构
- SMoE 的路由结果与 Mann-Kendall 趋势检验高度一致，赋予模型天然的可解释性

---
## 📊 实验与结果
- **数据集:** Time-MMD（9个领域）、Time-IMM（7个不规则数据集）
- **Baseline:** PatchTST、iTransformer、TimeXer、Autoformer、Time-MMD、AutoTimes、Time-LLM 等
- **主要结论:** TiMi 在绝大部分数据集上取得最优，MMoE 在三种 Transformer 骨干上平均提升 12-18%，SMoE 路由结果与 MK 趋势检验高度一致

> 对比 series-metadata（语义对齐）和 series-textual（语义不对齐但因果信息更丰富）两类多模态时序数据，说明后者更具挑战性也更有价值
![[TiMi_ .png]]

> 三类融合范式——Early Fusion 将时序嵌入 LLM、Late Fusion 分开编码后拼接、Non-Fusion（TiMi）不做表征对齐而是通过 MoE 功能融合
![[TiMi_ .png]]

> 不规则多模态时序预测结果——TiMi 在全部 7 个 Time-IMM 数据集上 MSE 最低
![[TiMi_ .png]]

## 💡 个人思考与启发
> [!quote] 这一部分最重要。

（待补充）

---
## 🔗 参考文献与链接
（暂无）
