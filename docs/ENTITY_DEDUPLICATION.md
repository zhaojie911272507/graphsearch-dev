# 跨文档实体共享功能实现文档

## 概述

本文档描述了知识图谱系统中跨文档实体共享（Entity Deduplication）功能的实现。该功能允许不同文档中提取的相同实体（同名同类型）在图谱中合并为单一节点，从而实现知识的跨文档关联和复用。

## 问题背景

### 原有实现的问题

在原有系统中：
- 每个文档的实体提取使用随机 UUID（`uuid4`）
- 相同实体（如 "Apple Inc."）在不同文档中会生成不同的节点
- 删除文档时，会删除该文档提取的所有实体，即使这些实体可能与其他文档相关
- 无法实现跨文档的知识关联和推理

### 需求

1. **实体去重**：相同名称和类型的实体应该合并为一个节点
2. **引用追踪**：记录哪些文档引用了每个实体
3. **安全删除**：删除文档时，只有当实体不再被任何文档引用时才删除
4. **向后兼容**：保持与现有代码的兼容性，可选择是否启用去重

## 实现方案

### 1. 确定性 UUID 生成

使用实体名称和类型生成确定性的 UUID，确保相同名称和类型的实体在不同文档中获得相同的 ID。

**实现位置**: `app/extraction/extractor.py`

```python
import hashlib

# Entity 确定性 ID 生成
def generate_entity_id(name: str, entity_type: EntityType) -> UUID:
    """Generate deterministic UUID for entity based on name and type."""
    dedup_key = f"{name}|{entity_type.value}"
    return UUID(hex=hashlib.md5(dedup_key.encode()).hexdigest())

# Concept 确定性 ID 生成
def generate_concept_id(name: str) -> UUID:
    """Generate deterministic UUID for concept based on name."""
    return UUID(hex=hashlib.md5(name.encode()).hexdigest())
```

**设计理由**:
- 使用 MD5 哈希：128 位输出，正好对应 UUID 的 128 位
- 包含 `entity_type`：区分同名但不同类型的实体（如 "Apple" 公司 vs "Apple" 水果）
- 简单高效：无需额外的数据库查询即可确定 ID

### 2. 引用计数和来源追踪

在 `EntityNode` 和 `ConceptNode` 中添加引用追踪字段。

**实现位置**: `app/domain/nodes.py`

```python
class EntityNode(BaseNode):
    """Represents a named entity extracted from text.

    When entity_deduplication is enabled, entities are merged by name + entity_type
    across documents, and reference_count tracks how many documents reference this entity.
    """
    node_type: NodeType = Field(default=NodeType.ENTITY, frozen=True)
    name: str = Field(..., min_length=1, max_length=300)
    entity_type: EntityType = Field(...)
    description: str = Field(default="")

    # 新增字段
    reference_count: int = Field(default=1,
        description="Number of documents referencing this entity")
    source_document_ids: list[str] = Field(
        default_factory=list,
        description="List of document IDs referencing this entity"
    )

class ConceptNode(BaseNode):
    """Represents an abstract concept or topic.

    When concept_deduplication is enabled, concepts are merged by name
    across documents, and reference_count tracks how many documents reference this concept.
    """
    node_type: NodeType = Field(default=NodeType.CONCEPT, frozen=True)
    name: str = Field(..., min_length=1, max_length=300)
    definition: str = Field(default="")

    # 新增字段
    reference_count: int = Field(default=1,
        description="Number of documents referencing this concept")
    source_document_ids: list[str] = Field(
        default_factory=list,
        description="List of document IDs referencing this concept"
    )
```

### 3. 去重存储方法

**实现位置**: `app/persistence/graph_store.py`

#### 3.1 实体去重存储

```python
async def upsert_entities_with_dedup(
    self,
    entities: list[EntityNode],
    document_id: str,
) -> int:
    """Upsert entities with deduplication by name + entity_type.

    Uses MERGE on (name, entity_type) to share entities across documents.
    Updates reference_count and source_document_ids for tracking.
    """
    query = """
    UNWIND $batch AS row
    MERGE (e:Entity {name: row.name, entity_type: row.entity_type})
    SET e.description = COALESCE(e.description, row.description, ''),
        e.updated_at = row.updated_at
    WITH e, row
    // Add source document if not already present
    SET e.source_document_ids = COALESCE(e.source_document_ids, []) +
        CASE WHEN $doc_id IN e.source_document_ids THEN [] ELSE [$doc_id] END
    // Update reference count
    SET e.reference_count = size(COALESCE(e.source_document_ids, [])) +
        CASE WHEN $doc_id IN COALESCE(e.source_document_ids, []) THEN 0 ELSE 1 END
    RETURN e
    """
```

#### 3.2 概念去重存储

```python
async def upsert_concepts_with_dedup(
    self,
    concepts: list[ConceptNode],
    document_id: str,
) -> int:
    """Upsert concepts with deduplication by name."""
    query = """
    UNWIND $batch AS row
    MERGE (c:Concept {name: row.name})
    SET c.definition = COALESCE(c.definition, row.definition, ''),
        c.updated_at = row.updated_at
    WITH c, row
    SET c.source_document_ids = COALESCE(c.source_document_ids, []) +
        CASE WHEN $doc_id IN c.source_document_ids THEN [] ELSE [$doc_id] END
    SET c.reference_count = size(COALESCE(c.source_document_ids, [])) +
        CASE WHEN $doc_id IN COALESCE(c.source_document_ids, []) THEN 0 ELSE 1 END
    RETURN c
    """
```

### 4. 智能删除逻辑

**实现位置**: `app/persistence/graph_store.py`

```python
async def delete_document_with_entity_dedup(
    self,
    document_id: str,
) -> dict[str, int]:
    """Delete a document when entity deduplication is enabled.

    This deletes:
    - The document node
    - All chunks belonging to the document
    - MENTIONS relationships from chunks to entities/concepts

    For entities/concepts:
    - Removes the document from their source_document_ids
    - Decrements their reference_count
    - Only deletes the entity if reference_count reaches 0
    """
    # Step 1: Delete document, chunks, and collect affected entities
    query = """
    MATCH (doc:Document {id: $document_id})
    OPTIONAL MATCH (doc)-[:HAS_CHUNK]->(chunk:Chunk)
    OPTIONAL MATCH (chunk)-[:MENTIONS]->(entity)
    WHERE entity:Entity OR entity:Concept

    WITH doc,
         collect(DISTINCT chunk) as chunks,
         collect(DISTINCT entity) as entities,
         collect(DISTINCT entity.id) as entity_ids

    // Delete chunks (this also deletes MENTIONS relationships)
    FOREACH (c IN chunks | DETACH DELETE c)

    // Delete the document
    DETACH DELETE doc

    RETURN 1 as documents_deleted,
           size(chunks) as chunks_deleted,
           entities as affected_entities,
           entity_ids as affected_entity_ids
    """

    # Step 2: Update entities - remove document from source_document_ids
    update_query = """
    UNWIND $entity_ids AS eid
    MATCH (e:Entity {id: eid})
    SET e.source_document_ids = [d IN e.source_document_ids WHERE d <> $document_id]
    SET e.reference_count = size(e.source_document_ids)
    WITH e
    WHERE size(e.source_document_ids) = 0
    DETACH DELETE e
    """

    # Step 3: Update concepts similarly
    update_concepts_query = """
    MATCH (c:Concept)-[:MENTIONS]<-[:HAS_CHUNK]-(doc:Document {id: $document_id})
    SET c.source_document_ids = [d IN c.source_document_ids WHERE d <> $document_id]
    SET c.reference_count = size(c.source_document_ids)
    WITH c
    WHERE size(c.source_document_ids) = 0
    DETACH DELETE c
    """
```

### 5. API 端点更新

**实现位置**: `app/api/routes/documents.py`

#### 5.1 上传端点

```python
@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    domain_key: Optional[str] = Form(None),
    use_dedup: Optional[bool] = Form(False),  # 新增参数
    ...
) -> UploadResponse:
    """Upload and process a single document file.

    Args:
        use_dedup: If True, enable entity deduplication by name + entity_type.
    """
    # ... 省略处理逻辑 ...

    if use_dedup:
        # 使用去重存储
        await store.upsert_nodes([doc_node, *embedded_chunks])
        await store.upsert_entities_with_dedup(all_entities, str(doc_node.id))
        await store.upsert_concepts_with_dedup(all_concepts, str(doc_node.id))
    else:
        # 标准存储（向后兼容）
        all_nodes = [doc_node, *embedded_chunks, *all_entities, *all_concepts]
        await store.upsert_nodes(all_nodes)
```

#### 5.2 删除端点

```python
@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    store: GraphStoreDep,
    delete_entities: bool = True,
    use_dedup: bool = False,  # 新增参数
) -> None:
    """Delete a document from the knowledge graph.

    Args:
        delete_entities: If True, also delete entities/concepts.
        use_dedup: If True, use deduplication-aware deletion logic.
    """
    if use_dedup:
        # 去重模式删除
        result = await store.delete_document_with_entity_dedup(document_id)
    elif delete_entities:
        # 删除文档和所有关联实体
        result = await store.delete_node_and_connected(document_id, "Document")
    else:
        # 只删除文档和 chunks，保留实体
        result = await store.delete_document_and_chunks_only(document_id)
```

## 使用示例

### 启用实体去重上传文档

```bash
# 使用 curl 上传文档并启用实体去重
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@document1.pdf" \
  -F "use_dedup=true"

# 上传第二个文档，相同实体将合并
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@document2.pdf" \
  -F "use_dedup=true"
```

### 删除文档

```bash
# 使用去重逻辑删除（推荐）
curl -X DELETE "http://localhost:8000/api/v1/documents/{doc_id}?use_dedup=true"

# 传统模式删除（删除所有关联实体）
curl -X DELETE "http://localhost:8000/api/v1/documents/{doc_id}?use_dedup=false&delete_entities=true"

# 仅删除文档和 chunks，保留实体
curl -X DELETE "http://localhost:8000/api/v1/documents/{doc_id}?use_dedup=false&delete_entities=false"
```

## 数据模型变更

### Neo4j 节点属性变更

#### Entity 节点

**之前**:
```cypher
(:Entity {
    id: "uuid-随机生成",
    name: "Apple Inc.",
    entity_type: "ORG",
    description: "...",
    created_at: "...",
    updated_at: "..."
})
```

**之后** (启用去重):
```cypher
(:Entity {
    id: "uuid-基于名称哈希",
    name: "Apple Inc.",
    entity_type: "ORG",
    description: "...",
    created_at: "...",
    updated_at: "...",
    reference_count: 3,                    # 新增
    source_document_ids: ["doc1", "doc2"]  # 新增
})
```

#### Concept 节点

**之前**:
```cypher
(:Concept {
    id: "uuid-随机生成",
    name: "Machine Learning",
    definition: "...",
    created_at: "...",
    updated_at: "..."
})
```

**之后** (启用去重):
```cypher
(:Concept {
    id: "uuid-基于名称哈希",
    name: "Machine Learning",
    definition: "...",
    created_at: "...",
    updated_at: "...",
    reference_count: 5,                    # 新增
    source_document_ids: ["doc1", ...]     # 新增
})
```

## 性能考虑

### 优势

1. **减少节点数量**：相同实体只存储一份，减少图谱大小
2. **提高查询效率**：跨文档查询时无需合并多个相同实体
3. **支持知识推理**：通过共享实体发现文档间的隐含关联

### 潜在开销

1. **引用计数更新**：删除文档时需要额外更新实体的引用计数
2. **列表操作**：`source_document_ids` 列表的维护需要额外的存储和计算

### 优化建议

1. 对于大型图谱，考虑对 `source_document_ids` 使用 Neo4j 的 `RELATIONSHIP` 而非列表属性
2. 定期清理 `reference_count = 0` 的孤立实体
3. 对 `Entity.name` 和 `Concept.name` 创建唯一约束以加速 MERGE 操作

## 向后兼容性

### 默认行为

- 默认 `use_dedup=false`，保持原有行为
- 现有文档和实体不受影响
- 可选择性对新文档启用去重

### 混合模式注意事项

在同一系统中同时使用去重和非去重模式时：
- 去重模式的实体使用确定性 UUID
- 非去重模式的实体使用随机 UUID
- 相同名称的实体可能存在多个节点（一个去重 + 多个非去重）

**建议**: 一旦启用去重，应始终保持启用以确保一致性。

## 测试建议

### 单元测试

1. 测试确定性 UUID 生成的一致性
2. 测试引用计数的增减逻辑
3. 测试删除文档时的实体保留/删除逻辑

### 集成测试

1. 上传两个包含相同实体的文档，验证实体合并
2. 删除一个文档，验证实体的引用计数正确更新
3. 删除所有引用文档，验证实体被正确清理

## 未来扩展

1. **实体消歧**: 处理同名但不同的实体（如两个不同的人 "John Smith"）
2. **置信度评分**: 为实体合并添加置信度阈值
3. **手动合并**: 提供 API 手动合并已知的相同实体
4. **版本历史**: 记录实体的合并和拆分历史

## 相关文件清单

- `app/extraction/extractor.py` - 实体提取和确定性 ID 生成
- `app/domain/nodes.py` - EntityNode 和 ConceptNode 模型
- `app/persistence/graph_store.py` - 去重存储和删除方法
- `app/api/routes/documents.py` - API 端点更新

## 参考资料

- [Neo4j MERGE 语法](https://neo4j.com/docs/cypher-manual/current/clauses/merge/)
- [知识图谱实体对齐综述](https://arxiv.org/abs/2008.01791)
- MD5 哈希用于确定性 UUID 生成的 RFC 4122 标准
