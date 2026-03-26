# 元数据管理与群体智能前端 PRD (v1.0)

**项目名称**: Enterprise Graph RAG - Metadata Management & Collective Intelligence Platform
**技术基调**: React + TypeScript, D3.js/Cytoscape, Neo4j, FastAPI
**对标产品**: Palantir Foundry, MiroFish

---

## 1. 概述 (Overview)

### 1.1 项目愿景

构建一个企业级的知识图谱元数据管理平台，在现有 Graph RAG 系统基础上，增加：
1. **元数据管理** - 数据资产的目录化、可追溯、可审计
2. **本体管理** - 领域知识的 Schema 定义与版本控制
3. **群体智能** - 多人协作标注、审核、知识沉淀
4. **智能应用** - RAG 管道配置、评估监控、Prompt 工厂

### 1.2 目标用户

| 用户角色 | 核心需求 | 使用场景 |
|----------|----------|----------|
| 领域专家 | 本体定义、知识审核 | 定义 EntityType、审核提取质量 |
| 数据分析师 | 数据血缘、影响分析 | 追溯实体来源、评估删除影响 |
| 业务用户 | 知识浏览、协作标注 | 搜索实体、添加评论和标签 |
| 管理员 | 质量监控、系统配置 | 查看 RAGAS 指标、调优参数 |

---

## 2. 功能需求 (Functional Requirements)

### 2.1 元数据管理中心 (Metadata Management)

#### 2.1.1 数据资产目录 (Asset Catalog)

**功能描述**: 提供知识图谱中所有节点的分类型浏览和搜索能力。

**页面结构**:
```
┌─────────────────────────────────────────────────────────────┐
│  搜索框 [输入实体名/文档标题...] 🔍  筛选器 [类型▼ 标签▼]   │
├──────────────┬──────────────────────────────────────────────┤
│  侧边栏      │  主内容区 (卡片网格/列表)                     │
│  ├─ 全部     │  ┌───────┐ ┌───────┐ ┌───────┐              │
│  ├─ 文档     │  │ Entity│ │ Entity│ │ Entity│              │
│  ├─ 实体     │  │ Person│ │ Org   │ │ Loc   │              │
│  ├─ 概念     │  │ ★4.2  │ │ ★3.8  │ │ ★4.5  │              │
│  └─ 标签     │  └───────┘ └───────┘ └───────┘              │
│              │  ... 分页器                                  │
└──────────────┴──────────────────────────────────────────────┘
```

**API 设计**:
```
GET /api/v1/metadata/assets
  Query Params:
    - type: NodeType (DOCUMENT|ENTITY|CONCEPT|CHUNK)
    - entity_type: EntityType (可选，仅当 type=ENTITY)
    - q: string (搜索关键词，匹配 name/title/content)
    - tags: string[] (标签筛选)
    - page: int (默认 1)
    - page_size: int (默认 20)
    - sort_by: string (created_at|name|quality_score)
    - order: asc|desc

Response:
{
  "items": [
    {
      "id": "uuid",
      "node_type": "ENTITY",
      "name": "张三",
      "entity_type": "PERSON",
      "created_at": "2026-03-20T10:00:00Z",
      "quality_score": 0.85,
      "relation_count": 12,
      "document_count": 3,
      "tags": ["高管", "技术团队"],
      "confidence_avg": 0.92
    }
  ],
  "total": 156,
  "page": 1,
  "page_size": 20,
  "total_pages": 8
}
```

**质量评分算法**:
```python
quality_score = (
    0.3 * embedding_completeness +  # embedding 完整度
    0.25 * relation_density +        # 关系密度
    0.25 * confidence_avg +          # 平均置信度
    0.2 * recency_factor             # 新鲜度
)
```

#### 2.1.2 节点详情页 (Node Detail)

**功能描述**: 展示单个节点的完整信息，包括元数据、关联关系、血缘溯源。

**页面结构**:
```
┌─────────────────────────────────────────────────────────────┐
│  ← 返回  │  张三 [PERSON]  │  质量分 85/100  │  [编辑] [...] │
├─────────────────────────────────────────────────────────────┤
│  基本信息                                                    │
│  ├─ ID: abc-123-def-456                                     │
│  ├─ 创建时间：2026-03-20 10:00                              │
│  ├─ 来源文档：产品会议纪要.pdf                               │
│  ├─ 描述：公司 CTO，负责技术战略                             │
│  └─ 标签：[高管] [技术团队] [+ 添加]                         │
├─────────────────────────────────────────────────────────────┤
│  关联关系 (12)                                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  [图谱小窗 - 力导向图，显示直接相连的节点]               ││
│  │   (张三) ─[WORKS_FOR]→ (XX 公司)                         ││
│  │   (张三) ─[LOCATED_IN]→ (北京)                          ││
│  └─────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────┤
│  血缘溯源                                                    │
│  文档 → Chunk #3 → [提取] → 实体 (张三)                       │
│  [查看原始 Chunk 内容]                                        │
├─────────────────────────────────────────────────────────────┤
│  评论与标注 (5)                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  用户 A: 这个实体的职位应该是 CTO 而非 CEO               ││
│  │  用户 B: 已确认 ✓                                        ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

**API 设计**:
```
GET /api/v1/metadata/{node_id}
Response: 完整节点信息 (含关联关系统计)

GET /api/v1/metadata/{node_id}/relations
  Query Params:
    - depth: int (1-3, 默认 1)
    - direction: outgoing|incoming|both
Response: { "relations": [...], "nodes": [...] }

GET /api/v1/metadata/{node_id}/lineage
Response: 血缘路径 (Document → Chunk → Entity)
```

#### 2.1.3 数据血缘追踪 (Data Lineage)

**功能描述**: 可视化展示数据的来源和派生关系，支持影响分析。

**血缘类型**:
| 类型 | 路径 | 用途 |
|------|------|------|
| 溯源血缘 | Entity ← Chunk ← Document | 追溯信息来源 |
| 派生血缘 | Document → Chunk → Entity | 分析影响范围 |
| 引用血缘 | Entity → Entity (RELATED_TO) | 知识关联 |

**页面结构**:
```
┌─────────────────────────────────────────────────────────────┐
│  [溯源视图 ◉] [派生视图 ○]  [引用视图 ○]                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│    ┌──────────┐                                            │
│    │ Document │ 产品会议纪要.pdf                             │
│    └────┬─────┘                                            │
│         │ HAS_CHUNK                                         │
│         ▼                                                   │
│    ┌──────────┐                                            │
│    │  Chunk   │  "会议由 CTO 张三主持，宣布..."                │
│    └────┬─────┘                                            │
│         │ MENTIONS                                          │
│         ▼                                                   │
│    ┌──────────┐     ┌──────────┐                           │
│    │  Entity  │────▶│  Entity  │  (关联实体)                 │
│    │   张三   │     │   XX 公司  │                           │
│    └──────────┘     └──────────┘                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**API 设计**:
```
GET /api/v1/metadata/{node_id}/lineage
  Query Params:
    - direction: upstream|downstream|both
    - max_depth: int (1-5)

Response:
{
  "lineage_paths": [
    {
      "path": [
        {"id": "doc-uuid", "type": "Document", "label": "产品会议纪要.pdf"},
        {"id": "chunk-uuid", "type": "Chunk", "label": "Chunk #3"},
        {"id": "entity-uuid", "type": "Entity", "label": "张三"}
      ],
      "confidence": 0.92
    }
  ]
}
```

---

### 2.2 本体管理工作台 (Ontology Workbench)

#### 2.2.1 实体类型管理 (Entity Type Manager)

**功能描述**: 允许领域专家定义和修改实体类型 Schema。

**内置类型**:
```python
class BuiltInEntityType(str, Enum):
    PERSON = "PERSON"      # 人物
    ORGANIZATION = "ORG"   # 组织/公司
    LOCATION = "LOC"       # 地点
    PRODUCT = "PROD"       # 产品
    EVENT = "EVENT"        # 事件
    DATE = "DATE"          # 日期
    MONEY = "MONEY"        # 金额
    PERCENT = "PERCENT"    # 百分比
```

**自定义类型**:
用户可添加领域特定的实体类型，如：
- `TECHNOLOGY` (技术)
- `REGULATION` (法规)
- `RISK` (风险)

**页面结构**:
```
┌─────────────────────────────────────────────────────────────┐
│  实体类型管理                            [+ 新建类型]         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐│
│  │  PERSON (内置)                         [编辑] [禁用]    ││
│  │  描述：人物实体                                          ││
│  │  实例数：1,234    关系类型：WORKS_FOR, LOCATED_IN...    ││
│  ├─────────────────────────────────────────────────────────┤│
│  │  TECHNOLOGY (自定义)                   [编辑] [删除]    ││
│  │  描述：技术栈、框架、工具                                 ││
│  │  实例数：56       关系类型：USES, DEPENDS_ON...         ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

**API 设计**:
```
GET /api/v1/ontology/entity-types
Response: { "types": [...] }

POST /api/v1/ontology/entity-types
Body:
{
  "name": "TECHNOLOGY",
  "description": "技术栈、框架、工具",
  "color": "#7ee787",
  "icon": "code",
  "extraction_prompt_template": "识别文本中的技术名词..."
}

PUT /api/v1/ontology/entity-types/{type_name}
DELETE /api/v1/ontology/entity-types/{type_name}  (仅自定义)
```

#### 2.2.2 关系类型管理 (Relation Type Manager)

**功能描述**: 定义实体间的关系语义。

**内置关系**:
```python
class BuiltInRelationType(str, Enum):
    HAS_CHUNK = "HAS_CHUNK"       # Document → Chunk
    MENTIONS = "MENTIONS"         # Chunk → Entity
    RELATED_TO = "RELATED_TO"     # Entity ↔ Entity
    BELONGS_TO = "BELONGS_TO"     # Chunk → Document
    DEFINES = "DEFINES"           # Document → Concept
```

**自定义关系**:
- `WORKS_FOR` (PERSON → ORGANIZATION)
- `LOCATED_IN` (PERSON/ORG → LOCATION)
- `USES` (PERSON/ORG → TECHNOLOGY)
- `COMPETES_WITH` (ORGANIZATION ↔ ORGANIZATION)

**关系 Schema**:
```json
{
  "name": "WORKS_FOR",
  "source_types": ["PERSON"],
  "target_types": ["ORGANIZATION"],
  "directionality": "DIRECTED",
  "properties": [
    {"name": "start_date", "type": "DATE"},
    {"name": "position", "type": "STRING"},
    {"name": "is_current", "type": "BOOLEAN"}
  ],
  "extraction_prompt": "识别人物与公司的雇佣关系..."
}
```

#### 2.2.3 本体版本控制 (Schema Versioning)

**功能描述**: 记录本体的变更历史，支持回滚和审计。

**数据模型**:
```python
class OntologyVersion(BaseModel):
    version: str  # "v1.0.0"
    created_at: datetime
    created_by: str  # user_id
    change_summary: str
    changes: list[str]  # ["Added EntityType TECHNOLOGY", "Modified WORKS_FOR properties"]
    is_active: bool
```

**API 设计**:
```
GET /api/v1/ontology/versions
POST /api/v1/ontology/versions  # 创建新版本 (发布变更)
GET /api/v1/ontology/versions/{version}/diff  # 对比差异
POST /api/v1/ontology/versions/{version}/rollback  # 回滚
```

---

### 2.3 群体智能 (Collective Intelligence)

#### 2.3.1 知识标注 (Knowledge Annotation)

**功能描述**: 用户可以对图谱节点添加评论、标签、修正建议。

**标注类型**:
| 类型 | 描述 | 数据结构 |
|------|------|----------|
| Comment | 文字评论 | `{content, parent_id?, is_resolved}` |
| Tag | 标签 | `{name, color, created_by}` |
| Correction | 修正建议 | `{field, old_value, new_value, status}` |
| Confidence | 置信度评分 | `{score: 0.0-1.0, reason}` |

**页面结构**:
```
┌─────────────────────────────────────────────────────────────┐
│  标注面板                               [筛选：全部▼]        │
├─────────────────────────────────────────────────────────────┤
│  [+ 添加标注]                                                │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 💬 用户 A (2026-03-20):                                  ││
│  │    这个实体的职位应该是 CTO 而非 CEO                      ││
│  │    [类型：修正建议] [状态：待审核]                        ││
│  │    [回复] [点赞 (3)] [标记为已解决]                       ││
│  ├─────────────────────────────────────────────────────────┤│
│  │ 🏷️ 标签：[高管] [技术团队] [+ 添加]                       ││
│  ├─────────────────────────────────────────────────────────┤│
│  │ ⭐ 置信度：4.2/5.0 (12 人评分)                            ││
│  │    [1★] [2★] [3★] [4★] [5★]  (点击评分)                 ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

**API 设计**:
```
GET /api/v1/metadata/{node_id}/annotations
  Query Params:
    - type: comment|tag|correction|confidence
    - status: pending|resolved|rejected

POST /api/v1/metadata/{node_id}/annotations
Body:
{
  "type": "correction",
  "content": {
    "field": "description",
    "old_value": "CEO",
    "new_value": "CTO",
    "reason": "根据官方组织架构图"
  }
}

PUT /api/v1/annotations/{annotation_id}
  Body: {"status": "resolved", "resolved_by": "user_id"}

DELETE /api/v1/annotations/{annotation_id}
```

#### 2.3.2 协作审核 (Collaborative Review)

**功能描述**: 多人对提取的实体/关系进行审核和投票，形成集体验证。

**审核流程**:
```
1. 系统自动提取 Entity (置信度 0.72)
       ↓
2. 进入"待审核"队列
       ↓
3. 领域专家审核 → [通过] / [拒绝] / [修改]
       ↓
4. 收集 N 人投票后 → 更新图谱 / 标记为低质量
```

**页面结构**:
```
┌─────────────────────────────────────────────────────────────┐
│  待审核项目 (15)   │  已通过 (234)  │  已拒绝 (12)            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐│
│  │  实体："李四王" [PERSON?]                                ││
│  │  来源：销售报告 Q4.pdf, Chunk #7                         ││
│  │  自动提取置信度：0.62 ⚠️                                 ││
│  │  原始文本："会议由李四王主持..."                          ││
│  │                                                         ││
│  │  [✓ 通过]  [✗ 拒绝]  [✏️ 修改]  [📋 评论]                ││
│  │                                                         ││
│  │  当前投票：2 通过 / 1 拒绝 / 1 修改建议                    ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

**数据模型**:
```python
class AnnotationVote(BaseModel):
    annotation_id: UUID
    user_id: str
    vote_type: str  # "APPROVE" | "REJECT" | "MODIFY"
    comment: str = ""
    created_at: datetime

class ReviewQueueItem(BaseModel):
    node_id: UUID
    reason: str  # 为何进入审核队列
    auto_confidence: float
    votes: list[AnnotationVote]
    status: str  # "PENDING" | "REVIEWED" | "ESCALATED"
```

**API 设计**:
```
GET /api/v1/intelligence/review-queue
  Query Params:
    - status: pending|reviewed|escalated
    - my_turn: bool (是否需要我审核)

POST /api/v1/intelligence/review-queue/{item_id}/vote
Body:
{
  "vote_type": "APPROVE",
  "comment": "确认实体正确"
}
```

#### 2.3.3 探索分享 (Exploration Sharing)

**功能描述**: 保存和分享图谱探索路径和发现。

**探索路径**:
用户在图谱中浏览、缩放、点击的轨迹可被记录：
```python
class ExplorationPath(BaseModel):
    id: UUID
    user_id: str
    title: str
    description: str
    start_node_id: UUID
    visited_nodes: list[UUID]  # 按访问顺序
    highlights: list[UUID]  # 标记为重点的节点
    created_at: datetime
    view_count: int
    likes: int
```

**分享功能**:
- 生成可分享链接 (带 token 的 URL)
- 导出为 PDF/PNG (图谱截图 + 注释)
- 嵌入到第三方系统 (iframe)

**页面结构**:
```
┌─────────────────────────────────────────────────────────────┐
│  我的探索路径                            [+ 保存当前路径]     │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐│
│  │  📍 从"张三"到"XX 公司"的融资历程                         ││
│  │     访问节点：8 个   创建：2026-03-19                    ││
│  │     👁️ 156 次浏览   ⭐ 23 个赞                           ││
│  │     [查看] [编辑] [分享] [删除]                          ││
│  ├─────────────────────────────────────────────────────────┤│
│  │  📍 技术栈演进图谱                                       ││
│  │     访问节点：24 个  创建：2026-03-18                    ││
│  │     👁️ 89 次浏览   ⭐ 12 个赞                            ││
│  │     [查看] [编辑] [分享] [删除]                          ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

**API 设计**:
```
GET /api/v1/intelligence/explorations
  Query Params:
    - user_id: str (可选，查看他人的)
    - sort: created_at|view_count|likes

POST /api/v1/intelligence/explorations
Body:
{
  "title": "XX 公司融资历程",
  "description": "从创始人到 C 轮的完整路径",
  "start_node_id": "uuid",
  "visited_nodes": ["uuid1", "uuid2", ...],
  "highlights": ["uuid3", "uuid4"]
}

POST /api/v1/intelligence/explorations/{id}/share
Response: { "share_url": "https://.../explore/{token}" }
```

---

### 2.4 智能应用工厂 (AI App Builder)

#### 2.4.1 RAG 管道配置 (RAG Pipeline Configurator)

**功能描述**: 可视化配置检索和生成参数。

**配置项**:
```yaml
retrieval:
  vector_search:
    top_k: 10              # 向量检索返回数量
    similarity_threshold: 0.7  # 相似度阈值
  graph_traversal:
    enabled: true
    max_depth: 2           # 图谱遍历深度
    max_neighbors: 50      # 每跳最大节点数

generation:
  model: "gpt-4"
  temperature: 0.1
  max_tokens: 2000
  system_prompt: "你是一个专业的知识助手..."
```

**页面结构**:
```
┌─────────────────────────────────────────────────────────────┐
│  RAG 管道配置                            [保存为新版本]        │
├─────────────────────────────────────────────────────────────┤
│  检索配置                                                    │
│  ├─ 向量检索                                                 │
│  │    Top-K: [10] ◄─────►  相似度阈值：[0.7]                │
│  ├─ 图谱遍历                                                 │
│  │    ☑ 启用    深度：[2]    最大邻居数：[50]                │
│  └─ [▶ 测试检索] (输入测试问题，查看返回结果)                 │
├─────────────────────────────────────────────────────────────┤
│  生成配置                                                    │
│  ├─ 模型：[gpt-4 ▼]    Temperature: [0.1]                   │
│  ├─ System Prompt:                                          │
│  │  ┌─────────────────────────────────────────────────────┐│
│  │  │ 你是一个专业的知识助手，基于提供的上下文回答问题...  ││
│  │  └─────────────────────────────────────────────────────┘│
│  └─ [▶ 测试生成]                                            │
├─────────────────────────────────────────────────────────────┤
│  版本历史                                                    │
│  v1.2 (当前) - 2026-03-20 - 调整 temperature 至 0.1          │
│  v1.1 - 2026-03-18 - 启用图谱遍历                            │
│  v1.0 - 2026-03-15 - 初始版本                                │
└─────────────────────────────────────────────────────────────┘
```

#### 2.4.2 Prompt 工作台 (Prompt Workbench)

**功能描述**: 管理 Extraction 和 Generation 的 Prompt 版本。

**Prompt 模板**:
```python
# 实体提取 Prompt
EXTRACTION_PROMPT_V3 = """
你是一个知识图谱构建专家。请从以下文本中提取实体和关系：

文本：{text}

请按照以下 JSON Schema 输出：
{schema}

要求:
1. 只提取高置信度的实体 (置信度 > 0.7)
2. 关系必须有明确的语义
3. 不确定的实体放入 candidates 列表
"""
```

**页面结构**:
```
┌─────────────────────────────────────────────────────────────┐
│  Prompt 工作台                           [+ 新建 Prompt]     │
├─────────────────────────────────────────────────────────────┤
│  实体提取 Prompt                    │  生成 Prompt           │
│  ├─ v3.0 (当前)                     │  ├─ v2.1 (当前)       │
│  ├─ v2.1                            │  ├─ v2.0              │
│  └─ v1.0                            │  └─ v1.0              │
├─────────────────────────────────────────────────────────────┤
│  编辑区                                                      │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ {{role_definition}}                                     ││
│  │                                                         ││
│  │ 请从以下文本中提取实体和关系：                          ││
│  │ 文本：{{text}}                                          ││
│  │                                                         ││
│  │ 输出格式：{{schema}}                                    ││
│  └─────────────────────────────────────────────────────────┘│
│  变量：{{role_definition}} {{text}} {{schema}}               │
├─────────────────────────────────────────────────────────────┤
│  测试区                                                      │
│  输入文本：[会议由 CTO 张三主持，讨论了新的 AI 战略...]          │
│  [▶ 运行测试]                                                │
│  输出:                                                       │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ {"entities": [{"name": "张三", "type": "PERSON"}...]}   ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

#### 2.4.3 评估 Dashboard (Evaluation Dashboard)

**功能描述**: 实时查看 RAGAS 评估指标趋势。

**核心指标**:
| 指标 | 定义 | 目标值 |
|------|------|--------|
| Context Precision | 检索到的内容中有用信息的比例 | > 0.7 |
| Context Recall | 回答问题所需信息被检索到的比例 | > 0.8 |
| Faithfulness | 生成答案对上下文的忠实度 (防幻觉) | > 0.85 |
| Answer Relevance | 答案与问题的相关性 | > 0.75 |
| Response Latency | 响应时间 (ms) | < 3000ms |

**页面结构**:
```
┌─────────────────────────────────────────────────────────────┐
│  评估 Dashboard                        [时间范围：近 7 天▼]    │
├─────────────────────────────────────────────────────────────┤
│  核心指标卡片                                                │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐   │
│  │Precision  │ │Recall     │ │Faithfulness│ │Relevance  │   │
│  │   0.72    │ │   0.81    │ │    0.88    │ │   0.76    │   │
│  │  ▲ +0.03  │ │  ▼ -0.02  │ │  ▲ +0.05   │ │  ▲ +0.01  │   │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘   │
├─────────────────────────────────────────────────────────────┤
│  指标趋势图                                                  │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  [折线图：过去 7 天各指标的每日均值]                      ││
│  │   │                                                     ││
│  │   │        ╭── Precision                                ││
│  │   │      ╭─╯                                            ││
│  │   │    ╭─╯                                              ││
│  │   └────┴────────────────────────                         ││
│  └─────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────┤
│  消融实验对比                                                │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  纯向量检索 vs 混合检索 (向量 + 图)                        ││
│  │                                                         ││
│  │  指标         │ 向量  │ 混合   │ 提升    │             ││
│  │  Precision    │ 0.65  │ 0.72   │ +10.8%  │             ││
│  │  Recall       │ 0.71  │ 0.81   │ +14.1%  │             ││
│  │  Faithfulness │ 0.86  │ 0.88   │ +2.3%   │             ││
│  │  Latency (ms) │ 1200  │ 2100   │ +75%    │ ⚠️          ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

**API 设计**:
```
GET /api/v1/evaluation/metrics
  Query Params:
    - start_date: date
    - end_date: date
    - granularity: day|week|month
    - metric: precision|recall|faithfulness|relevance (可选)

GET /api/v1/evaluation/ablation-study
Response: {
  "vector_only": {...metrics},
  "hybrid": {...metrics},
  "improvement": {...}
}
```

---

## 3. 技术架构 (Technical Architecture)

### 3.1 前端技术栈

```
┌─────────────────────────────────────────────────────────────┐
│                      前端架构                               │
├─────────────────────────────────────────────────────────────┤
│  框架：React 18 + TypeScript 5                              │
│  构建工具：Vite 5                                           │
│  状态管理：Zustand                                          │
│  UI 组件库：shadcn/ui + Radix UI                             │
│  样式：Tailwind CSS                                         │
│                                                             │
│  图谱可视化：                                               │
│    - Cytoscape.js (主图谱，大规模节点)                       │
│    - D3.js v8 (力导向图，小型子图)                           │
│    - React Flow (血缘图，流程类视图)                         │
│                                                             │
│  数据获取：TanStack Query (React Query)                     │
│  表单处理：React Hook Form + Zod                            │
│  路由：React Router v6                                      │
│  国际化：i18next                                            │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 后端 API 扩展

```
新增路由模块:
app/
├── api/
│   └── routes/
│       ├── metadata.py       # 元数据管理
│       ├── ontology.py       # 本体管理
│       ├── intelligence.py   # 群体智能
│       └── evaluation.py     # 评估监控
├── services/
│   ├── metadata_service.py
│   ├── ontology_service.py
│   ├── intelligence_service.py
│   └── evaluation_service.py
└── visualization/
    └── schemas.py (扩展现有)
```

### 3.3 Neo4j Schema 扩展

```cypher
// 新增：标注相关节点
(:User {id, name, email})
(:Annotation {id, type, content, status, created_at})
(:Tag {id, name, color})
(:Comment {id, content, parent_id, is_resolved})
(:Vote {id, vote_type, score, created_at})

// 新增：本体版本
(:OntologyType {name, description, color, is_builtin})
(:OntologyVersion {version, created_at, change_summary})

// 关系扩展
(:Entity)-[:ANNOTATED_BY]->(:User)
(:Entity)-[:HAS_ANNOTATION]->(:Annotation)
(:Annotation)-[:CREATED_BY]->(:User)
(:Annotation)-[:HAS_TAG]->(:Tag)
(:User)-[:VOTED {score, vote_type}]->(:Annotation)

(:OntologyType)-[:VERSIONED_IN]->(:OntologyVersion)
```

### 3.4 API 完整列表

| 模块 | 方法 | 路径 | 描述 |
|------|------|------|------|
| 元数据 | GET | /api/v1/metadata/assets | 资产列表 |
| 元数据 | GET | /api/v1/metadata/{id} | 节点详情 |
| 元数据 | GET | /api/v1/metadata/{id}/lineage | 血缘追踪 |
| 元数据 | GET | /api/v1/metadata/{id}/annotations | 获取标注 |
| 元数据 | POST | /api/v1/metadata/{id}/annotations | 添加标注 |
| 本体 | GET | /api/v1/ontology/entity-types | 实体类型列表 |
| 本体 | POST | /api/v1/ontology/entity-types | 创建类型 |
| 本体 | GET | /api/v1/ontology/relation-types | 关系类型列表 |
| 本体 | GET | /api/v1/ontology/versions | 版本历史 |
| 群体智能 | GET | /api/v1/intelligence/review-queue | 审核队列 |
| 群体智能 | POST | /api/v1/intelligence/review-queue/{id}/vote | 投票 |
| 群体智能 | GET | /api/v1/intelligence/explorations | 探索路径列表 |
| 群体智能 | POST | /api/v1/intelligence/explorations | 保存路径 |
| 群体智能 | GET | /api/v1/intelligence/recommendations | 智能推荐 |
| 评估 | GET | /api/v1/evaluation/metrics | 评估指标 |
| 评估 | GET | /api/v1/evaluation/ablation-study | 消融实验 |

---

## 4. 实施路线图 (Roadmap)

### Phase 1: 元数据管理 MVP (2 周)

**Week 1**:
- [ ] 前端框架搭建 (Vite + React + TS)
- [ ] 后端 API: 资产列表、节点详情
- [ ] 前端页面：资产目录、节点详情
- [ ] Neo4j: 血缘查询 Cypher

**Week 2**:
- [ ] 后端 API: 血缘追踪、关系统计
- [ ] 前端页面：血缘追踪视图 (React Flow)
- [ ] 质量评分算法实现
- [ ] 集成测试和文档

**交付物**:
- 可浏览的资产目录
- 节点详情和血缘视图
- 基础质量评分

### Phase 2: 本体管理 (1.5 周)

**Week 3**:
- [ ] 后端 API: 实体类型 CRUD、关系类型 CRUD
- [ ] Neo4j: 本体 Schema 设计
- [ ] 前端页面：本体管理列表

**Week 4 (前半)**:
- [ ] 后端 API: 版本控制
- [ ] 前端页面：版本历史、Diff 视图
- [ ] 提取 Prompt 模板配置

**交付物**:
- 完整的本体管理工作台
- 版本控制和回滚

### Phase 3: 群体智能 (2.5 周)

**Week 4 (后半)**:
- [ ] 后端 API: 标注 CRUD、投票
- [ ] Neo4j: 标注相关 Schema
- [ ] 前端页面：标注面板

**Week 5**:
- [ ] 后端 API: 审核队列、探索路径
- [ ] 前端页面：审核工作流
- [ ] 前端页面：探索路径保存和分享

**Week 6 (前半)**:
- [ ] 智能推荐算法 (基于图结构)
- [ ] 分享功能 (生成 token、导出)

**交付物**:
- 完整的协作标注系统
- 审核工作流
- 探索分享功能

### Phase 4: 智能应用 (3 周)

**Week 6 (后半)**:
- [ ] 后端 API: RAG 配置、Prompt 版本
- [ ] 前端页面：RAG 管道配置器

**Week 7**:
- [ ] 后端 API: 评估指标聚合
- [ ] 前端页面：评估 Dashboard
- [ ] RAGAS 集成和数据聚合

**Week 8**:
- [ ] Prompt 工作台
- [ ] 消融实验配置
- [ ] 端到端测试和性能优化

**交付物**:
- 完整的 AI 应用工厂
- 可视化评估 Dashboard
- Prompt 版本管理

---

## 5. 成功标准 (Success Metrics)

### 5.1 功能完整性

| 模块 | 验收标准 |
|------|----------|
| 元数据管理 | 可搜索、浏览、追溯所有节点 |
| 本体管理 | 可自定义 EntityType 和 RelationType |
| 群体智能 | 支持多人同时标注和投票 |
| 智能应用 | 可配置和测试 RAG 管道 |

### 5.2 性能指标

| 指标 | 目标值 |
|------|--------|
| 资产列表加载 | < 500ms (1000 条数据) |
| 血缘追踪查询 | < 1s (3 跳以内) |
| 图谱渲染 | < 2s (500 节点) |
| API 可用性 | > 99.5% |

### 5.3 用户体验

- 资产搜索支持模糊匹配和高亮
- 血缘视图支持拖拽和缩放
- 标注操作支持实时保存 (防丢失)
- 支持键盘快捷键 (提升效率)

---

## 6. 风险与缓解 (Risks & Mitigation)

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Neo4j 查询性能 | 高 | 添加索引、限制查询深度、缓存热点数据 |
| 前端图谱渲染卡顿 | 中 | 使用 Cytoscape.js WebGL 渲染、虚拟滚动 |
| 并发标注冲突 | 中 | 乐观锁 + 冲突检测、最后写入优先 |
| 数据一致性 | 高 | 事务确保原子性、定期审计 |

---

## 7. 附录 (Appendix)

### 7.1 参考项目

- **Palantir Foundry**: https://www.palantir.com/platforms/foundry/
- **MiroFish**: https://github.com/666ghj/MiroFish
- **Apache Atlas**: 元数据管理开源项目
- **DataHub**: LinkedIn 开源数据目录

### 7.2 术语表

| 术语 | 定义 |
|------|------|
| Ontology | 领域知识的 Schema 定义，包括实体类型和关系类型 |
| Lineage | 数据的来源和派生路径 |
| Annotation | 用户对图谱节点的标注 (评论、标签、修正) |
| RAGAS | Retrieval-Augmented Generation Assessment 框架 |

---

## 8. 下一步行动 (Next Steps)

1. [ ] 评审本 PRD 并确认需求优先级
2. [ ] 启动 Phase 1 开发
3. [ ] 每周 demo 和迭代
4. [ ] Phase 1 完成后进行用户测试
