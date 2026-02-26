---

# 🛠️ 企业级 Graph RAG 系统需求文档 (v1.1 - Updated)

**项目名称**: Enterprise Graph Retrieval-Augmented Generation System
**文档状态**: Draft / Review
**技术基调**: Production-Ready, Modular, Type-Safe, Async-First
**环境约束**: Local Inference (Embeddings), Neo4j Persistence

---

## 1. 概述 (Overview)

本项目旨在构建一个高并发、可扩展的企业级图检索增强生成（Graph RAG）系统。系统通过结合向量检索（Vector Search）的语义匹配能力与图数据库（Graph DB）的结构化关联能力，解决传统 RAG 在处理复杂关系推理和跨文档上下文缺失的问题。

---

## 2. 技术栈与开发规范 (Tech Stack & Standards)

### 2.1 核心技术栈

* **语言**: **Python 3.13+** (需验证依赖库兼容性)
* **Web 框架**: FastAPI (Async)
* **图数据库**: **Neo4j** (使用官方 `neo4j` Python Driver)
* **编排框架**: LangChain / LangGraph
* **Embedding 模型**: **M3E-Large (Local)**
* 加载库: `sentence-transformers` / `torch`
* 模型路径: `./mode_files/embeddingmodel/m3e-large/`


* **LLM**: OpenAI (或其他兼容 API) 用于推理和实体提取
* **数据校验**: Pydantic v2

### 2.2 代码规范 (The Vibe)

* **强类型约束**: 全面使用 Python Type Hints。
* **模块化设计**: 严禁“面条代码” (Spaghetti Code)，遵循单一职责原则。
* **异步优先**: I/O 密集型操作（DB、网络请求）必须使用 `async/await`。
* **错误处理**: 严禁裸露的 `try-except`，必须具备自定义异常类和结构化错误日志。

---

## 3. 数据层需求：本体定义 (Ontology & Modeling)

系统必须基于强校验的数据模型构建，严禁使用非结构化的 Dict 传递核心数据。

### 3.1 节点定义 (Node Schema)

所有节点需继承自基础模型，包含 `UUID` 和 `metadata`。需定义以下 `Enum` 类型：

| 节点类型 (Type) | 描述 | 关键属性 |
| --- | --- | --- |
| **Document** | 原始文档 | `title`, `source_url`, `created_at` |
| **Chunk** | 文本切片 | `content`, `embedding` (Array[float]), `chunk_index` |
| **Entity** | 提取出的实体 | `name`, `entity_type` (e.g., PERSON, ORG) |
| **Concept** | 抽象概念 | `name`, `definition` |

### 3.2 关系定义 (Relationship Schema)

边 (Edge) 必须包含权重和方向性：

* **关系类型**: `HAS_CHUNK`, `MENTIONS`, `RELATED_TO`
* **属性要求**: `source_id`, `target_id`, `weight` (float, 0.0-1.0)
* **完整性校验**: 关系的源节点和目标节点 ID 必须存在。

---

## 4. 摄入层需求：非结构化提取 (Extraction Pipeline)

### 4.1 Embedding 服务 (Local)

由于使用本地模型，需封装一个单例模式的 Embedding Service。

* **加载逻辑**: 系统启动时从 `./mode_files/embeddingmodel/m3e-large/` 加载模型到内存（或 GPU）。
* **性能优化**:
* 如果使用 CPU，需优化 `torch` 线程设置。
* 提供 `embed_documents` (Batch) 和 `embed_query` (Single) 接口。


* **维度校验**: M3E-Large 输出维度通常为 1024，需在 Pydantic 模型中强制校验向量长度。

### 4.2 核心逻辑 (`GraphExtractor`)

实现异步服务，将非结构化文本转化为符合上述 Ontology 的图结构。

* **LLM 解析**: 使用 Function Calling 或 JSON Mode 强制 LLM 输出符合 Pydantic Schema 的 JSON 数据。
* **并发控制**:
* 使用 `asyncio.gather` 并行处理多个 Chunks。
* 必须引入 `Semaphore` 机制以限制并发数。


* **容错机制**:
* 针对 LLM 格式错误（Hallucination），需实现“重试 2 次 -> 优雅降级”的策略。



---

## 5. 持久化层需求：Neo4j 适配器 (Persistence Layer)

### 5.1 GraphStore 适配器

基于 **Neo4j Python Driver** 构建高可用适配器。

* **连接管理**:
* 实现 Context Manager (`__aenter__`, `__aexit__`) 自动管理 `GraphDatabase.driver` 生命周期。


* **批量写入 (Batching)**:
* **禁止**单条插入。
* 必须使用 Cypher `UNWIND` 语法进行高吞吐量的批量节点/边插入。
* 示例: `UNWIND $batch AS row MERGE (n:Chunk {id: row.id}) ...`


* **幂等性 (Idempotency)**:
* 使用 `MERGE` 关键字替代 `CREATE`，避免重复数据。


* **向量索引 (Vector Index)**:
* **必需**: 针对 `Chunk` 节点的 `embedding` 属性创建 Neo4j 向量索引 (Vector Index)。
* 索引配置需匹配 m3e-large 的维度 (1024) 和相似度度量 (Cosine)。



---

## 6. 检索层需求：混合检索策略 (Retrieval Engine)

### 6.1 混合检索算法 (Hybrid Search)

实现 `GraphRetriever` 类，执行以下多阶段检索逻辑：

1. **向量初筛 (Vector Search)**:
* 调用本地 Embedding Service 将 Query 转化为向量。
* 使用 Cypher 查询 Neo4j 向量索引 (`db.index.vector.queryNodes`) 获取 Top-K `Chunk`。


2. **图遍历扩展 (Graph Traversal)**:
* 以 Top-K Chunk 为起点，向外进行 1-2 跳 (Hops) 的遍历。
* 获取关联的 `Entity` 和 `Concept` 节点以补充上下文。


3. **上下文组装**:
* 将检索到的文本块和图谱关系（如 "Entity A -> RELATED_TO -> Entity B"）合并为 LLM 的 Context。



---

## 7. 服务层与可观测性 (Service & Observability)

### 7.1 API 封装 (FastAPI)

* **依赖注入**: `GraphStore` 和 `EmbeddingService` 必须通过 FastAPI `Depends` 注入，确保单例复用。
* **端点定义**:
* `POST /ingest`: 接收文档，触发后台任务。
* `POST /query`: 接收查询，返回流式 (Streaming) 答案。



### 7.2 部署注意事项

* **Docker 挂载**: 部署时需将宿主机的 `./mode_files/` 目录映射至容器内相同路径，或在 Dockerfile 中构建层。
* **Python 3.13 兼容性**: 在 `requirements.txt` 中锁定兼容的 `neo4j` 和 `torch` 版本。

---

## 8. 交付物 (Deliverables)

1. 完整的源代码 (含 Python 3.13+ 环境配置)
2. OpenAPI/Swagger 文档
3. Docker Compose 文件 (包含 Neo4j 服务及本地模型卷挂载配置)
4. 单元测试覆盖率报告 (>80%)