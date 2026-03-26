# GraphRAG 元数据管理前端

## 技术栈

- **React 18** + **TypeScript 5**
- **Vite 5** - 构建工具
- **Tailwind CSS** - 样式框架
- **shadcn/ui** - UI 组件库
- **Zustand** - 状态管理
- **TanStack Query** - 数据获取
- **React Router** - 路由管理

## 快速开始

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 启动开发服务器

```bash
# 确保后端运行在 http://localhost:8000
npm run dev
```

访问 http://localhost:3000

### 3. 构建生产版本

```bash
npm run build
npm run preview
```

## 项目结构

```
frontend/
├── src/
│   ├── components/
│   │   ├── layout/          # 布局组件
│   │   │   ├── Layout.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Header.tsx
│   │   └── ui/              # UI 基础组件
│   │       ├── Button.tsx
│   │       ├── Input.tsx
│   │       ├── Card.tsx
│   │       ├── Badge.tsx
│   │       ├── Dialog.tsx
│   │       ├── Tabs.tsx
│   │       ├── Textarea.tsx
│   │       └── Select.tsx
│   ├── lib/
│   │   ├── api.ts           # API 客户端
│   │   └── utils.ts         # 工具函数
│   ├── pages/               # 页面组件
│   │   ├── AssetCatalog.tsx
│   │   ├── NodeDetail.tsx
│   │   ├── OntologyManager.tsx
│   │   ├── ReviewQueue.tsx
│   │   ├── Explorations.tsx
│   │   └── EvaluationDashboard.tsx
│   ├── store/
│   │   └── appStore.ts      # Zustand 状态管理
│   ├── types/
│   │   └── global.ts        # TypeScript 类型定义
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
└── postcss.config.js
```

## 功能模块

### 1. 资产目录 (Asset Catalog)
- 浏览和搜索知识图谱中的节点
- 按类型筛选（实体、文档、概念、文本块）
- 显示质量评分和关系统计

### 2. 节点详情 (Node Detail)
- 查看节点完整信息
- 血缘溯源（Document → Chunk → Entity）
- 关联关系展示

### 3. 本体管理 (Ontology Manager)
- 实体类型管理（EntityType CRUD）
- 关系类型管理（RelationType CRUD）
- 版本历史

### 4. 协作审核 (Review Queue)
- 审核队列展示
- 投票功能（通过/拒绝/修改）
- 审核统计

### 5. 探索路径 (Explorations)
- 保存图谱探索路径
- 分享和点赞
- 浏览历史

### 6. 评估监控 (Evaluation Dashboard)
- RAGAS 指标展示
- 消融实验对比
- 响应时间统计

## API 配置

开发环境下，Vite 会代理 API 请求到后端：

```typescript
// vite.config.ts
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

## 状态管理

使用 Zustand 进行全局状态管理：

```typescript
// store/appStore.ts
import { create } from 'zustand'

interface AppState {
  sidebarOpen: boolean
  selectedAssetType: string
  searchQuery: string
  // ...
}

export const useAppStore = create<AppState>((set) => ({
  // ...
}))
```

## 数据获取

使用 TanStack Query 进行数据获取和缓存：

```typescript
const { data, isLoading } = useQuery({
  queryKey: ['assets', { type, q }],
  queryFn: () => assetApi.list({ type, q }).then(res => res.data),
})
```

## 下一步开发

1. **图谱可视化** - 集成 Cytoscape.js 显示关系图
2. **血缘追踪视图** - 使用 React Flow 实现流程图
3. **暗色模式切换** - 完善主题系统
4. **国际化** - 添加 i18n 支持

## 故障排除

### 前端无法连接后端
确保后端服务运行在 `http://localhost:8000`

### 样式不生效
检查是否安装了 `tailwindcss` 和 `postcss`

### TypeScript 报错
运行 `npm install` 确保所有依赖已安装
