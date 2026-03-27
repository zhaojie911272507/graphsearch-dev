# 血缘追踪模块测试指南

## 🎯 功能说明

血缘追踪模块用于可视化展示知识图谱中节点的数据来源和派生关系，支持三种视图模式：

- **上游视图**：展示节点的数据来源（Document ← Chunk ← Entity）
- **下游视图**：展示节点的派生数据（Entity → Related Entities）
- **全部视图**：同时展示上下游关系

## 📋 测试步骤

### 1. 准备测试数据

首先需要确保数据库中有数据。如果没有，先摄入一个测试文档：

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "content": "张三，现任XX公司CTO，负责AI产品研发。他在2020年加入公司，之前在YYY公司担任技术总监。",
    "metadata": {
      "title": "员工介绍文档",
      "source": "hr_manual.pdf",
      "date": "2024-03-26"
    }
  }'
```

### 2. 查找要测试的节点

访问资产目录，找到刚才创建的实体：

```bash
# 搜索包含"张三"的实体
curl "http://localhost:8000/api/v1/metadata/assets?q=张三&type=Entity"
```

记录返回结果中的 `id` 值（例如：`"550e8400-e29b-41d4-a716-446655440000"`）

### 3. 测试血缘 API

使用节点 ID 调用血缘接口：

```bash
# 测试全部视图
curl "http://localhost:8000/api/v1/metadata/{node_id}/lineage?direction=both&max_depth=3"

# 测试上游视图
curl "http://localhost:8000/api/v1/metadata/{node_id}/lineage?direction=upstream&max_depth=3"

# 测试下游视图
curl "http://localhost:8000/api/v1/metadata/{node_id}/lineage?direction=downstream&max_depth=3"
```

**预期返回格式**：
```json
{
  "lineage_paths": [
    {
      "path": [
        {"id": "doc-uuid", "type": "Document", "label": "员工介绍文档"},
        {"id": "chunk-uuid", "type": "Chunk", "label": "Chunk #0"},
        {"id": "entity-uuid", "type": "Entity", "label": "张三"}
      ],
      "confidence": 1.0
    }
  ],
  "upstream_count": 1,
  "downstream_count": 0
}
```

### 4. 前端测试

1. **启动前端服务**：
```bash
cd frontend
npm install  # 如果还没安装依赖
npm run dev
```

2. **访问资产目录**：
```
http://localhost:3000/assets
```

3. **找到测试节点**：
   - 在搜索框输入"张三"
   - 点击搜索结果中的"张三"节点

4. **进入血缘视图**：
   - 在节点详情页面，应该有"查看血缘"按钮或链接
   - 点击后跳转到：`http://localhost:3000/assets/{node_id}/lineage`

5. **测试三种模式**：
   - 点击"上游"按钮 → 只显示来源节点
   - 点击"全部"按钮 → 显示完整血缘路径
   - 点击"下游"按钮 → 只显示派生节点

6. **交互测试**：
   - ✅ **拖拽节点**：鼠标拖动节点，检查是否可以自由移动
   - ✅ **缩放**：使用右下角的 MiniMap 或滚轮，检查缩放是否正常
   - ✅ **图例**：查看底部图例，确认颜色和形状对应正确

## 🧪 预期效果

### 上游视图（溯源）
```
┌──────────┐
│ Document │ 员工介绍文档
└────┬─────┘
     │ (HAS_CHUNK)
     ▼
┌──────────┐
│  Chunk   │ "张三，现任XX公司CTO..."
└────┬─────┘
     │ (MENTIONS)
     ▼
┌──────────┐
│  Entity  │ 张三 [中心节点]
└──────────┘
```

### 下游视图（派生）
```
┌──────────┐
│  Entity  │ 张三 [中心节点]
└────┬─────┘
     │ (RELATED_TO)
     ▼
┌──────────┐
│  Entity  │ XX公司
└──────────┘
```

### 全部视图（完整）
显示上游 + 下游的所有路径

## 🐛 常见问题排查

### 问题 1: 前端显示"未找到血缘关系"

**原因**：
- 节点是孤立节点（没有关系）
- 实体提取失败
- 向量索引未创建

**排查步骤**：
```bash
# 1. 检查节点是否存在
curl http://localhost:8000/api/v1/metadata/{node_id}

# 2. 检查节点的关系
# 在 Neo4j Browser 中执行：
MATCH (n {id: '{node_id}'})-[r]-(m)
RETURN n, r, m

# 3. 查看日志
# 后端日志应该显示血缘查询的详细信息
```

### 问题 2: 图谱显示空白或加载失败

**原因**：
- React Flow 依赖未正确安装
- 前端构建失败

**解决方案**：
```bash
# 重新安装依赖
cd frontend
rm -rf node_modules package-lock.json
npm install

# 清除缓存并重启
npm run dev
```

### 问题 3: 血缘路径数量为 0

**原因**：
- max_depth 设置过小
- 查询方向不正确
- 数据质量问题

**调试方法**：
```bash
# 增加深度
curl "http://localhost:8000/api/v1/metadata/{node_id}/lineage?max_depth=5"

# 查看原始数据
# 在 Neo4j Browser 中执行：
MATCH path = (n {id: '{node_id}'})<-[*1..3]-(m)
RETURN path
LIMIT 5
```

## 📊 测试检查清单

- [ ] 后端 API 返回正确的数据格式
- [ ] 前端页面正常加载，无控制台错误
- [ ] 三种视图模式（上游/全部/下游）切换正常
- [ ] 节点颜色正确（Document: 蓝, Entity: 绿, Concept: 紫, Chunk: 灰）
- [ ] 节点形状正确（Document: 矩形, Entity: 椭圆, Concept: 菱形）
- [ ] 边有箭头指示方向
- [ ] 可以拖拽节点
- [ ] 可以缩放视图
- [ ] MiniMap 正常显示
- [ ] 空状态显示友好提示
- [ ] 错误状态显示错误信息

## 🎨 视觉验收标准

| 元素 | 标准 |
|------|------|
| **节点** | 圆角矩形/椭圆，带背景色，白色文字居中 |
| **边** | 灰色线条，带箭头，动画效果 |
| **中心节点** | 加粗边框，更大尺寸，突出显示 |
| **布局** | 上游在左，中心在中，下游在右 |
| **图例** | 4 种节点类型的颜色和形状说明 |
| **计数** | 显示上游/下游节点数量 |

## 📱 响应式测试

测试不同屏幕尺寸：
- [ ] 桌面（1920x1080）
- [ ] 笔记本（1366x768）
- [ ] 平板（768x1024）

## ✅ 完成标志

当你可以：
1. 在资产目录找到任意节点
2. 点击进入血缘视图
3. 看到完整的血缘路径图谱
4. 切换三种视图模式
5. 与图谱交互（拖拽、缩放）

血缘追踪模块即宣告完成！🎉
