本节定义 Graph RAG 系统的自动化评估标准，旨在摒弃“肉眼看效果”的作坊式开发，建立基于数据驱动的迭代闭环（Data-Driven Iteration）。

9.1 核心评估框架 (Evaluation Framework)
系统需集成标准的 RAG 评估框架（当前阶段使用 RAGAS，（上线生产后使用TruLens）），实现对检索质量与生成质量的解耦评估。

9.2 关键量化指标 (Key Metrics)
评估套件必须能够定期产出以下核心指标的报告：

检索质量 (Retrieval Metrics):

Context Precision (上下文精度): 检索到的 Chunk 和实体中，真正对回答问题有用的比例有多高（惩罚冗余信息）。

Context Recall (上下文召回率): 回答该问题所需的 Ground Truth 信息，是否都被我们的混合检索器成功找了出来（惩罚遗漏信息）。

生成质量 (Generation Metrics):

Faithfulness (忠实度/防幻觉): LLM 生成的最终答案，必须 100% 能够从检索到的上下文中推导出来。严禁模型利用自身预训练知识“脑补”。

Answer Relevance (回答相关性): 生成的答案是否直接回答了用户的 Query，有无答非所问。

图谱增益特有指标 (Graph Lift - Custom Metric):

Ablation Study (消融实验打分): 评估套件需支持对比测试：纯向量检索得分 vs. 混合检索（向量 + 1跳图遍历）得分。明确量化出 Neo4j 图遍历环节为系统带来的“召回率增益”与“耗时惩罚”的性价比。

9.3 黄金数据集管理 (Golden Dataset Management)
评估不能依赖随机提问。系统上线前需构建并维护一个“黄金评测集”（Golden Dataset）。

数据结构: 包含 [question, expected_answer, expected_contexts]。

冷启动策略: 允许使用更强大的高参数量模型（如 GPT-5 / Claude 4.5 Sonnet）根据业务文档反向生成初始的 Q&A 对，由人工领域专家（SME）审核后入库。评测集规模初期不少于 100 条高质量问答。

9.4 自动化与可视化 (Automation & Dashboard)
持续集成 (CI/CD): 在核心检索逻辑（如 Cypher 语句调整、Embedding 模型切换）发生代码变更提交 PR 时，自动触发评估套件运行核心测试集。

指标追踪: 评估结果需输出至可观测看板（如 MLflow, LangSmith 或企业自建的 Grafana），以便团队追踪版本迭代时的 Metric 趋势。