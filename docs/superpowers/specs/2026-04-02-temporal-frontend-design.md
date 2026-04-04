# 时序知识图谱前端设计文档

**日期**: 2026-04-02
**状态**: 已批准

---

## 1. 背景

为时序知识图谱后端功能开发对应的前端界面，支持：
- 实体版本历史查询
- 关系演变查看
- 时间旅行查询
- 全局统计展示

---

## 2. 页面设计

### 2.1 路由设计

```
/temporal              ← 时序查询首页
/temporal/stats       ← 时序统计
```

### 2.2 页面 1: 时序查询首页 (`/temporal`)

#### 功能区域

1. **查询类型选择器**（Tab 切换）
   - 实体历史 | 关系演变 | 时间旅行

2. **查询表单**
   - 实体历史：entity_id 输入框（支持搜索）+ 时间范围筛选
   - 关系演变：source_id + target_id（支持下拉搜索）+ 时间范围筛选
   - 时间旅行：entity_id 输入框 + 日期时间选择器

3. **实体/关系搜索功能**
   - 提供搜索输入框，从现有实体列表自动补全
   - 支持按名称搜索

4. **结果展示**
   - 实体历史：版本列表卡片（分页，每页10条），显示 version、timestamp、change_summary
   - 关系演变：时间线展示 + 权重变化图表
   - 时间旅行：实体快照详情

5. **摘要面板**（右侧或底部）
   - 实体摘要 / 关系摘要
   - 重要性评分、趋势指标

6. **侧边栏导航集成**
   - 在 Sidebar 添加"时序查询"菜单项

### 2.3 页面 2: 时序统计 (`/temporal/stats`)

#### 功能区域

1. **统计卡片**
   - 总实体数 / 总版本数 / 总快照数

2. **热点实体列表**（分页）
   - 按版本数排序的 Top 10 实体
   - 每页 10 条，支持翻页

3. **趋势图表**
   - 每日新增版本数趋势（折线图）

4. **刷新按钮**
   - 手动刷新统计数据

---

## 3. API 调用

使用现有的 `api` 实例，添加 `temporalApi`：

```typescript
// 查询实体历史
POST /api/v1/temporal/query
{ entity_id, query_type: "history" }

// 查询关系演变
POST /api/v1/temporal/query
{ source_id, target_id, query_type: "history" }

// 时间旅行查询
POST /api/v1/temporal/query
{ entity_id, timestamp, query_type: "at_time" }

// 获取摘要
POST /api/v1/temporal/summary
{ level: "entity", entity_id, entity_name, entity_type }

// 获取全局统计
POST /api/v1/temporal/summary
{ level: "global" }

// 获取服务状态
GET /api/v1/temporal/status
```

---

## 4. 组件设计

### 新增文件

```
frontend/src/
├── pages/
│   └── TemporalQuery.tsx     # 时序查询页面
├── components/
│   └── temporal/
│       ├── EntityHistory.tsx
│       ├── RelationshipTimeline.tsx
│       ├── TimeTravel.tsx
│       ├── TemporalSummary.tsx
│       └── TemporalStats.tsx
└── lib/
    └── api.ts                # 添加 temporalApi
```

---

## 5. 验证方案

```bash
# 1. 启动前端
cd frontend && npm run dev

# 2. 访问 /temporal 页面

# 3. 测试各查询功能
- 输入 entity_id 查询历史
- 选择两个实体查询关系演变
- 选择时间点查询历史状态

# 4. 访问 /temporal/stats 页面
- 查看全局统计
```

---

## 6. 已确认事项

- [x] 页面数量：2个
- [x] 功能范围：实体历史、关系演变、时间旅行、全局统计
- [x] UI 风格：与现有页面保持一致（使用现有组件库）
- [x] 实体搜索：支持下拉自动补全搜索
- [x] 分页：实体历史列表分页（每页10条）
- [x] 侧边栏导航：添加"时序查询"菜单项
- [x] 刷新功能：统计页面支持手动刷新