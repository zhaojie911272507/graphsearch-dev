# GraphSearch 项目功能增强设计

## 概述

本文档描述 GraphSearch 项目的 6 个新增功能的设计方案，按实现顺序排列：
1. 血缘追踪视图
2. 图谱可视化增强
3. 版本管理 UI
4. RAG 管道配置器
5. 用户认证 (JWT + RBAC)
6. 测试用例

---

## 功能 1: 血缘追踪视图

### 需求摘要
- 双向血缘追踪（上游 + 下游）
- 动态计算深度（根据节点数量自动确定）
- 可按节点类型/关系类型过滤
- Dagre 布局
- 点击节点展开更多血缘

### 技术方案

**后端 API 扩展**
- 扩展 `/api/v1/metadata/{id}/lineage`：
  - 新增参数：`direction` (upstream/downstream/both)，`depth` (auto 或具体数值)，`nodeTypes[]`，`relationTypes[]`
  - 返回：节点列表 + 边列表，支持分页

**前端组件**
- 新增 `LineageGraph.tsx` 组件，使用 React Flow
- 集成 Dagre 布局算法
- 支持节点点击展开更多血缘
- 支持类型过滤面板

### 数据流
```
节点详情页 → 调用 lineage API → 返回双向血缘数据 → React Flow 渲染 → 点击节点展开
```

---

## 功能 2: 图谱可视化增强

### 需求摘要
- 使用 Cytoscape.js 库
- 支持多种布局：Dagre、Cose、Circle、Grid、Breadthfirst
- 完整交互功能：拖拽节点、缩放/平移、节点详情、搜索高亮、右键菜单、多选

### 技术方案

**后端 API**
- 新增 `/api/v1/visualization/graph`：
  - 参数：`layout`，`nodeTypes[]`，`limit`，`offset`
  - 返回：节点列表 + 边列表

**前端组件**
- 新增 `GraphView.tsx` 组件，集成 Cytoscape.js
- 布局切换器：支持 5 种布局
- 交互功能：
  - 拖拽：Cytoscape 内置
  - 缩放/平移：Cytoscape 内置
  - 节点详情：点击显示侧边栏
  - 搜索高亮：输入框搜索，节点高亮
  - 右键菜单：自定义 contextMenu 扩展
  - 多选：Ctrl/Cmd + 点击

### 数据流
```
GraphView 组件 → 调用 graph API → 返回节点/边数据 → Cytoscape 渲染 → 交互处理
```

---

## 功能 3: 版本管理 UI

### 需求摘要
- 支持 Side-by-side 对比和时间线两种展示方式
- 回滚需要确认对话框 + 操作日志记录
- 适用于 EntityType 和 RelationType 的版本管理

### 技术方案

**后端 API 扩展**
- 扩展 `/api/v1/ontology/versions`：
  - 新增 `/compare` 端点：比较两个版本的差异
  - 新增 `/rollback` 端点：执行回滚

**前端组件**
- 新增 `VersionHistory.tsx`：
  - 时间线视图：垂直时间轴，点击版本查看详情
  - 对比视图：Side-by-side diff，差异行高亮（绿色新增、红色删除）
  - 回滚确认弹窗：显示将要恢复的内容，确认后执行
  - 操作日志：记录回滚操作到审计日志

### 数据流
```
Ontology 详情页 → 版本历史 → 选择版本 → 对比/回滚 → 确认 → 执行 + 记录日志
```

---

## 功能 4: RAG 管道配置器

### 需求摘要
- 完整管道配置：文档摄入 → 分块 → 实体提取 → 图存储 → 向量索引 → 查询
- 开放全部参数配置
- 可保存多个配置方案

### 技术方案

**后端 API**
- 已有 `/api/v1/evaluation/pipeline/configs`，需扩展：
  - 新增参数验证
  - 新增 `/test` 端点：用测试数据运行管道

**前端组件**
- 新增 `PipelineConfig.tsx`：
  - 阶段列表：6 个阶段的 Tab
  - 每阶段可展开显示详细参数
  - 模板选择：预设模板（高召回、高精度、平衡）
  - 配置管理：保存、加载、对比、删除

### 管道阶段参数

| 阶段 | 参数 |
|------|------|
| 文档摄入 | `source_type`, `parsers[]`, `max_file_size` |
| 分块 | `chunk_size`, `chunk_overlap`, `split_by` |
| 实体提取 | `model`, `temperature`, `max_retries`, `extraction_prompt` |
| 图存储 | `batch_size`, `index_type` |
| 向量索引 | `embedding_model`, `dimension`, `metric` |
| 查询 | `top_k`, `hybrid_alpha`, `rerank` |

### 数据流
```
PipelineConfig 页面 → 编辑配置 → 保存配置 → 调用 API 存储 → 可执行测试
```

---

## 功能 5: 用户认证 (JWT + RBAC)

### 需求摘要
- JWT 认证方式
- 三种角色：管理员、审核员、普通用户
- 基于角色的权限控制

### 技术方案

**后端模块 `app/auth/`**
- `token.py`：JWT 生成和验证
- `password.py`：密码 hashing（bcrypt）
- `models.py`：User 模型
- `dependencies.py`：认证依赖注入
- `roles.py`：角色枚举和权限装饰器

**后端 API**
- `POST /api/v1/auth/login`：登录，返回 JWT token
- `POST /api/v1/auth/logout`：登出
- `GET /api/v1/auth/me`：获取当前用户信息
- `GET /api/v1/auth/users`：用户列表（仅管理员）
- `POST /api/v1/auth/users`：创建用户（仅管理员）
- `PUT /api/v1/auth/users/{id}/role`：修改角色（仅管理员）

**用户存储**
- 使用 Neo4j 存储用户节点
- 或使用 `app/config` 中的用户配置（简单场景）

**前端**
- 新增 `Login.tsx` 页面
- Axios interceptor：自动在请求头添加 `Authorization: Bearer <token>`
- Route guard：检查 token 和角色权限

### 权限矩阵

| 功能 | 管理员 | 审核员 | 普通用户 |
|------|--------|--------|----------|
| 资产目录 | ✓ | ✓ | ✓ |
| 节点详情 | ✓ | ✓ | ✓ |
| 血缘追踪 | ✓ | ✓ | ✓ |
| Ontology 管理 | ✓ | ✓ | ✗ |
| 审核队列 | ✓ | ✓ | ✗ |
| 探索路径 | ✓ | ✓ | ✓ (自己的) |
| 用户管理 | ✓ | ✗ | ✗ |
| 评估配置 | ✓ | ✗ | ✗ |

---

## 功能 6: 测试用例

### 需求摘要
- 覆盖全部功能模块（包括新增的 6 个功能）
- 单元测试 + 集成测试都要

### 测试结构

```
tests/
├── conftest.py              # 共享 fixtures
├── unit/
│   ├── test_api_*.py        # API 单元测试（6 个功能）
│   ├── test_auth.py         # 认证单元测试
│   ├── test_domain.py       # Domain 模型测试
│   └── test_graph_store.py  # GraphStore 单元测试
└── integration/
    ├── test_api_integration.py    # API 集成测试
    ├── test_lineage_integration.py # 血缘追踪测试
    ├── test_pipeline_integration.py # 管道配置测试
    └── test_auth_integration.py   # 认证集成测试
```

### 测试覆盖

**功能 1 血缘追踪**
- `GET /api/v1/metadata/{id}/lineage` - 各种参数组合

**功能 2 图谱可视化**
- `GET /api/v1/visualization/graph` - 各种布局和过滤

**功能 3 版本管理**
- `GET /api/v1/ontology/versions`
- `POST /api/v1/ontology/versions/{id}/compare`
- `POST /api/v1/ontology/versions/{id}/rollback`

**功能 4 管道配置**
- `GET/POST/PUT/DELETE /api/v1/evaluation/pipeline/configs`
- `POST /api/v1/evaluation/pipeline/configs/{id}/test`

**功能 5 认证**
- `POST /api/v1/auth/login` - 登录成功/失败
- `GET /api/v1/auth/me` - token 验证
- 角色权限测试

**功能 6 测试框架**
- pytest 配置
- fixtures（mocked Neo4j, test client）
- 覆盖率配置

---

## 实施顺序

1. 血缘追踪视图
2. 图谱可视化增强
3. 版本管理 UI
4. RAG 管道配置器
5. 用户认证
6. 测试用例