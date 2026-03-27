# 文档详情 API 增强

## 概述

增强了文档详情 API 端点 (`GET /api/v1/documents/{document_id}`)，现在返回完整的文档解析内容，包括文本块、实体、概念、实体类型统计和关系类型统计。

## 变更内容

### 修改的文件

- `app/api/routes/documents.py` - `get_document_detail` 端点增强
- `app/persistence/graph_store.py` - 添加 `EntityNode`, `ConceptNode` 导入

### API 响应变更

#### 之前的响应

```json
{
  "id": "uuid",
  "title": "文档标题",
  "filename": "document.pdf",
  "file_size": 1024,
  "file_type": "application/pdf",
  "upload_status": "complete",
  "parse_error": null,
  "created_at": "2026-03-27T10:00:00Z",
  "updated_at": "2026-03-27T10:00:00Z",
  "content_hash": "...",
  "source_url": "",
  "chunk_count": 5
}
```

#### 现在的响应

```json
{
  "id": "uuid",
  "title": "文档标题",
  "filename": "document.pdf",
  "file_size": 1024,
  "file_type": "application/pdf",
  "upload_status": "complete",
  "parse_error": null,
  "created_at": "2026-03-27T10:00:00Z",
  "updated_at": "2026-03-27T10:00:00Z",
  "content_hash": "...",
  "source_url": "",

  "chunks": [
    {
      "id": "chunk-uuid",
      "content": "文本块内容...",
      "chunk_index": 0,
      "section_title": "章节标题",
      "paragraph_type": "paragraph",
      "word_count": 150,
      "sentence_count": 8,
      "semantic_boundary_start": true,
      "semantic_boundary_end": true,
      "previous_chunk_overlap": "",
      "created_at": "2026-03-27T10:00:00Z",
      "updated_at": "2026-03-27T10:00:00Z"
    }
  ],

  "entities": [
    {
      "id": "entity-uuid",
      "name": "实体名称",
      "entity_type": "PERSON",
      "description": "实体描述",
      "reference_count": 2,
      "source_document_ids": ["doc1", "doc2"],
      "created_at": "2026-03-27T10:00:00Z",
      "updated_at": "2026-03-27T10:00:00Z"
    }
  ],

  "concepts": [
    {
      "id": "concept-uuid",
      "name": "概念名称",
      "definition": "概念定义",
      "reference_count": 1,
      "source_document_ids": ["doc1"],
      "created_at": "2026-03-27T10:00:00Z",
      "updated_at": "2026-03-27T10:00:00Z"
    }
  ],

  "entity_types": {
    "PERSON": 5,
    "ORG": 3,
    "LOCATION": 2
  },

  "relation_types": {
    "RELATED_TO": 10,
    "WORKS_FOR": 3
  },

  "statistics": {
    "chunk_count": 10,
    "entity_count": 15,
    "concept_count": 5,
    "relation_count": 20,
    "unique_entity_types": 8,
    "unique_relation_types": 5
  }
}
```

## 新增字段说明

### chunks (文本块列表)

按 `chunk_index` 排序返回所有文本块，包含完整的语义元数据：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 文本块 UUID |
| content | string | 文本内容 |
| chunk_index | integer | 在文档中的索引位置 |
| section_title | string | 所属章节标题 |
| paragraph_type | string | 段落类型 (paragraph/list/code/table/header) |
| word_count | integer | 单词数 |
| sentence_count | integer | 句子数 |
| semantic_boundary_start | boolean | 是否为语义边界开始 |
| semantic_boundary_end | boolean | 是否为语义边界结束 |
| previous_chunk_overlap | string | 与前一个文本块的重叠内容 |

### entities (实体列表)

返回文档引用的所有唯一实体（去重后的）：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 实体 UUID |
| name | string | 实体名称 |
| entity_type | string | 实体类型 |
| description | string | 实体描述 |
| reference_count | integer | 引用该实体的文档数量 |
| source_document_ids | array | 引用该实体的文档 ID 列表 |

### concepts (概念列表)

返回文档引用的所有唯一概念（去重后的）：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 概念 UUID |
| name | string | 概念名称 |
| definition | string | 概念定义 |
| reference_count | integer | 引用该概念的文档数量 |
| source_document_ids | array | 引用该概念的文档 ID 列表 |

### entity_types (实体类型统计)

对象格式，键为实体类型，值为该类型实体的数量：

```json
{
  "PERSON": 10,
  "ORG": 5,
  "LOCATION": 3,
  "DATE": 2
}
```

### relation_types (关系类型统计)

对象格式，键为关系类型，值为该类型关系的数量：

```json
{
  "RELATED_TO": 15,
  "WORKS_FOR": 5,
  "LOCATED_IN": 3
}
```

### statistics (统计信息)

| 字段 | 类型 | 说明 |
|------|------|------|
| chunk_count | integer | 文本块总数 |
| entity_count | integer | 实体总数 |
| concept_count | integer | 概念总数 |
| relation_count | integer | 关系总数 |
| unique_entity_types | integer | 不同实体类型的数量 |
| unique_relation_types | integer | 不同关系类型的数量 |

## 实现细节

### Cypher 查询

**获取文本块**:
```cypher
MATCH (doc:Document {id: $document_id})-[:HAS_CHUNK]->(chunk:Chunk)
RETURN chunk ORDER BY chunk.chunk_index
```

**获取实体**:
```cypher
MATCH (doc:Document {id: $document_id})-[:HAS_CHUNK]->(chunk:Chunk)-[:MENTIONS]->(entity:Entity)
RETURN DISTINCT entity ORDER BY entity.name
```

**获取概念**:
```cypher
MATCH (doc:Document {id: $document_id})-[:HAS_CHUNK]->(chunk:Chunk)-[:MENTIONS]->(concept:Concept)
RETURN DISTINCT concept ORDER BY concept.name
```

**获取实体类型统计**:
```cypher
MATCH (doc:Document {id: $document_id})-[:HAS_CHUNK]->(chunk:Chunk)-[:MENTIONS]->(entity:Entity)
RETURN entity.entity_type as type, count(entity) as count
ORDER BY count DESC
```

**获取关系类型统计**:
```cypher
MATCH (doc:Document {id: $document_id})-[:HAS_CHUNK]->(chunk:Chunk)-[:MENTIONS]->(entity:Entity)-[r]-(other:Entity)
WHERE other IN [
    (doc)-[:HAS_CHUNK]->(c:Chunk)-[:MENTIONS]->(e:Entity) | e
]
RETURN type(r) as relation_type, count(r) as count
ORDER BY count DESC
```

## 使用示例

### 获取文档详情

```bash
curl -X GET "http://localhost:8000/api/v1/documents/{document_id}"
```

### 前端使用示例 (TypeScript)

```typescript
interface DocumentDetail {
  id: string;
  title: string;
  filename: string;
  chunks: Chunk[];
  entities: Entity[];
  concepts: Concept[];
  entity_types: Record<string, number>;
  relation_types: Record<string, number>;
  statistics: {
    chunk_count: number;
    entity_count: number;
    concept_count: number;
    relation_count: number;
  };
}

async function loadDocumentDetail(documentId: string): Promise<DocumentDetail> {
  const response = await fetch(`/api/v1/documents/${documentId}`);
  return response.json();
}
```

## 性能考虑

1. **DISTINCT 查询**: 实体和概念使用 `DISTINCT` 避免重复
2. **ORDER BY**: 结果按名称或索引排序，便于前端展示
3. **单次查询**: 所有数据在一个 API 调用中返回，减少网络往返
4. **Neo4j 索引**: 确保 `:Document(id)` 和 `:Chunk(document_id)` 有索引

## 向后兼容性

- 所有原有字段保持不变
- 新增字段为可选对象/数组，不影响现有客户端
- 无破坏性变更

## 相关文档

- [实体去重功能文档](./ENTITY_DEDUPLICATION.md)
- [语义分块实现](./SEMANTIC_CHUNKING.md) (待创建)
