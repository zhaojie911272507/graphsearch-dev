# Lineage Tracking View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement bidirectional lineage tracking with dynamic depth, type filtering, Dagre layout, and click-to-expand functionality.

**Architecture:**
- Backend: Extend existing `/api/v1/metadata/{node_id}/lineage` API with new parameters (node_types, relation_types, depth=auto) and return edge data
- Frontend: Update LineageTracking.tsx with dagre layout, filter panel, and expand-on-click

**Tech Stack:** FastAPI, Neo4j, React Flow, dagre

---

## File Structure

```
app/
├── api/
│   ├── routes/
│   │   └── metadata.py                    # MODIFY: Add lineage params
│   └── schemas/
│       └── metadata.py                     # MODIFY: Update LineageResponseSchema
└── persistence/
    └── graph_store.py                      # MODIFY: get_node_lineage method

frontend/src/
├── pages/
│   └── LineageTracking.tsx                # MODIFY: Add layout & filtering
├── lib/
│   └── api.ts                              # MODIFY: Update assetApi.getLineage
└── types/
    └── global.ts                           # MODIFY: Add LineageNode types
```

---

### Task 1: Extend Backend Lineage API with Filtering

**Files:**
- Modify: `app/api/routes/metadata.py:278-323`
- Modify: `app/api/schemas/metadata.py`
- Modify: `app/persistence/graph_store.py:1127-1175`

- [ ] **Step 1: Update LineageResponseSchema to include edge data and new fields**

File: `app/api/schemas/metadata.py`

Add new fields to `LineageResponseSchema`:
```python
class LineageResponseSchema(BaseModel):
    lineage_paths: list[LineagePathSchema]
    upstream_count: int
    downstream_count: int
    # NEW: Add these fields
    nodes: list[dict] = []  # Flattened nodes for React Flow
    edges: list[dict] = []  # Flattened edges for React Flow
    available_node_types: list[str] = []  # For filter dropdown
    available_relation_types: list[str] = []  # For filter dropdown
```

- [ ] **Step 2: Update get_node_lineage endpoint to accept new parameters**

File: `app/api/routes/metadata.py`

Update the endpoint at line 284-323:
```python
@router.get(
    "/{node_id}/lineage",
    response_model=LineageResponseSchema,
    summary="Get data lineage",
    description="Trace the lineage of a node with filtering and dynamic depth.",
)
async def get_node_lineage(
    node_id: UUID,
    store: GraphStoreDep,
    direction: str = Query(default="both", description="upstream, downstream, or both"),
    max_depth: int = Query(default=0, ge=0, le=10, description="0 = auto-calculate"),
    node_types: list[str] = Query(default=[], description="Filter by node types"),
    relation_types: list[str] = Query(default=[], description="Filter by relation types"),
) -> LineageResponseSchema:
    """Get lineage information for a node."""
    try:
        lineage_data = await store.get_node_lineage(
            str(node_id),
            direction=direction,
            max_depth=max_depth if max_depth > 0 else None,  # None triggers auto-calc
            node_types=node_types or None,
            relation_types=relation_types or None,
        )
        # ... return with new fields
```

- [ ] **Step 3: Update GraphStore.get_node_lineage method**

File: `app/persistence/graph_store.py`

Update the method signature and add filtering:
```python
async def get_node_lineage(
    self,
    node_id: str,
    direction: str = "both",
    max_depth: int | None = None,
    node_types: list[str] | None = None,
    relation_types: list[str] | None = None,
) -> dict[str, object]:
    """Get lineage paths for a node with optional filtering."""

    # Auto-calculate depth if not provided
    if max_depth is None:
        # Query to count nodes at each depth level
        # and find optimal depth that returns ~100 nodes
        max_depth = await self._calculate_optimal_lineage_depth(node_id, direction)

    # Add WHERE clauses for filtering
    node_type_filter = ""
    if node_types:
        node_type_filter = "WHERE ANY(t IN labels(node) WHERE t IN $node_types)"

    relation_type_filter = ""
    if relation_types:
        relation_type_filter = "AND type(r) IN $relation_types"

    # Update queries to include filters and return edge data
    # ...

    return {
        "paths": paths,
        "upstream_count": upstream_count,
        "downstream_count": downstream_count,
        "nodes": flattened_nodes,  # NEW
        "edges": flattened_edges,  # NEW
        "available_node_types": all_node_types,  # NEW
        "available_relation_types": all_relation_types,  # NEW
    }
```

- [ ] **Step 4: Add helper method for optimal depth calculation**

File: `app/persistence/graph_store.py`

Add new method:
```python
async def _calculate_optimal_lineage_depth(
    self, node_id: str, direction: str, target_nodes: int = 100
) -> int:
    """Calculate optimal depth that returns approximately target_nodes."""
    # Start at depth 1, increment until we hit target or max 5
    async with self.driver.session(database=self._settings.database) as session:
        for depth in range(1, 6):
            query = f"""
            MATCH (start {{id: $node_id}}){'<-[*1..' + str(depth) + ']-' if direction in ('upstream', 'both') else ''}(source)
            {'-[*1..' + str(depth) + ']->' if direction in ('downstream', 'both') else ''}(derived)
            RETURN count(DISTINCT source) + count(DISTINCT derived) as node_count
            """
            result = await session.run(query, node_id=node_id)
            record = await result.single()
            if record and record["node_count"] >= target_nodes:
                return depth
        return 5  # Default max
```

- [ ] **Step 5: Run test to verify API works**

Run: `uvicorn app.main:app --reload` then:
```bash
curl "http://localhost:8000/api/v1/metadata/{node_id}/lineage?direction=both&node_types=Document,Entity"
```

Expected: JSON response with nodes, edges, and available filter types

- [ ] **Step 6: Commit**

```bash
git add app/api/routes/metadata.py app/api/schemas/metadata.py app/persistence/graph_store.py
git commit -m "feat: extend lineage API with filtering and dynamic depth"
```

---

### Task 2: Add Dagre Layout to Frontend Lineage Component

**Files:**
- Modify: `frontend/package.json` - Add dagre dependency
- Modify: `frontend/src/pages/LineageTracking.tsx`

- [ ] **Step 1: Install dagre and dagre-d3 for layout algorithms**

Run:
```bash
cd frontend
npm install dagre
npm install -D @types/dagre
```

- [ ] **Step 2: Update LineageTracking.tsx to use Dagre layout**

File: `frontend/src/pages/LineageTracking.tsx`

Add imports and layout function:
```typescript
import dagre from 'dagre'
import { Position } from 'reactflow'

// Add Dagre layout function
const getLayoutedElements = (nodes: Node[], edges: Edge[], direction = 'TB') => {
  const dagreGraph = new dagre.graphlib.Graph()
  dagreGraph.setDefaultEdgeLabel(() => ({}))

  const nodeWidth = 170
  const nodeHeight = 50

  dagreGraph.setGraph({ rankdir: direction, nodesep: 50, ranksep: 80 })

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight })
  })

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target)
  })

  dagre.layout(dagreGraph)

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id)
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
      targetPosition: direction === 'LR' ? Position.Left : Position.Top,
      sourcePosition: direction === 'LR' ? Position.Right : Position.Bottom,
    }
  })

  return { nodes: layoutedNodes, edges }
}
```

- [ ] **Step 3: Apply Dagre layout when data changes**

File: `frontend/src/pages/LineageTracking.tsx`

Update the useEffect that processes lineage data to apply Dagre layout:
```typescript
useEffect(() => {
  if (!data) return

  const { nodes: processedNodes, edges: processedEdges } = processLineageData(data)

  // Apply Dagre layout
  const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
    processedNodes,
    processedEdges,
    'TB'
  )

  setNodes(layoutedNodes)
  setEdges(layoutedEdges)

  setTimeout(() => {
    if (reactFlowInstance) {
      reactFlowInstance.fitView({ padding: 0.2 })
    }
  }, 100)
}, [data, direction, processLineageData, setNodes, setEdges, reactFlowInstance])
```

- [ ] **Step 4: Run test to verify layout works**

Run: Open browser to lineage page, verify nodes are laid out top-to-bottom with proper spacing

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/LineageTracking.tsx frontend/package.json
git commit -m "feat: add Dagre layout to lineage tracking view"
```

---

### Task 3: Add Type Filtering Panel

**Files:**
- Modify: `frontend/src/pages/LineageTracking.tsx`
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Update API to pass filter params**

File: `frontend/src/lib/api.ts`

```typescript
getLineage: (
  nodeId: string,
  direction?: string,
  max_depth?: number,
  node_types?: string[],      // NEW
  relation_types?: string[]   // NEW
) =>
  api.get(`/metadata/${nodeId}/lineage`, {
    params: { direction, max_depth, node_types, relation_types }
  }),
```

- [ ] **Step 2: Add filter state and UI to LineageTracking**

File: `frontend/src/pages/LineageTracking.tsx`

Add state variables:
```typescript
const [selectedNodeTypes, setSelectedNodeTypes] = useState<string[]>([])
const [selectedRelationTypes, setSelectedRelationTypes] = useState<string[]>([])
const [availableNodeTypes, setAvailableNodeTypes] = useState<string[]>([])
const [availableRelationTypes, setAvailableRelationTypes] = useState<string[]>([])
```

- [ ] **Step 3: Update query to include filter params**

```typescript
const { data, isLoading, error } = useQuery({
  queryKey: ['lineage', nodeId, direction, selectedNodeTypes, selectedRelationTypes],
  queryFn: () =>
    assetApi
      .getLineage(
        nodeId!,
        direction !== 'both' ? direction : undefined,
        0, // 0 triggers auto-calc
        selectedNodeTypes.length > 0 ? selectedNodeTypes : undefined,
        selectedRelationTypes.length > 0 ? selectedRelationTypes : undefined
      )
      .then(res => res.data),
  enabled: !!nodeId,
})
```

- [ ] **Step 4: Add filter panel UI**

In the render, add a filter section:
```typescript
<div className="flex items-center gap-x-4">
  {/* Existing direction buttons */}

  {/* NEW: Node type filter */}
  <select
    multiple
    value={selectedNodeTypes}
    onChange={(e) => setSelectedNodeTypes(Array.from(e.target.selectedOptions, o => o.value))}
    className="border rounded px-2 py-1 text-sm"
  >
    {availableNodeTypes.map(type => (
      <option key={type} value={type}>{type}</option>
    ))}
  </select>

  {/* NEW: Relation type filter */}
  <select
    multiple
    value={selectedRelationTypes}
    onChange={(e) => setSelectedRelationTypes(Array.from(e.target.selectedOptions, o => o.value))}
    className="border rounded px-2 py-1 text-sm"
  >
    {availableRelationTypes.map(type => (
      <option key={type} value={type}>{type}</option>
    ))}
  </select>
</div>
```

- [ ] **Step 5: Update available types when data loads**

```typescript
useEffect(() => {
  if (data) {
    setAvailableNodeTypes(data.available_node_types || [])
    setAvailableRelationTypes(data.available_relation_types || [])
  }
}, [data])
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/LineageTracking.tsx frontend/src/lib/api.ts
git commit -m "feat: add type filtering to lineage tracking"
```

---

### Task 4: Add Click-to-Expand Functionality

**Files:**
- Modify: `frontend/src/pages/LineageTracking.tsx`

- [ ] **Step 1: Add expand state**

```typescript
const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set())
const [isExpanding, setIsExpanding] = useState(false)
```

- [ ] **Step 2: Add node click handler**

```typescript
const onNodeClick = useCallback(async (event: React.MouseEvent, node: Node) => {
  // If node already expanded, just show details
  if (expandedNodes.has(node.id)) {
    // Show detail panel
    return
  }

  // Expand the node (load more lineage)
  setIsExpanding(true)
  try {
    const expandData = await assetApi.getLineage(
      node.id,
      direction !== 'both' ? direction : undefined,
      1, // Get 1 hop from this node
      selectedNodeTypes.length > 0 ? selectedNodeTypes : undefined,
      selectedRelationTypes.length > 0 ? selectedRelationTypes : undefined
    ).then(res => res.data)

    // Merge new nodes and edges
    const { nodes: newNodes, edges: newEdges } = processLineageData(expandData)
    setNodes(prev => {
      const existingIds = new Set(prev.map(n => n.id))
      const uniqueNewNodes = newNodes.filter(n => !existingIds.has(n.id))
      const allNodes = [...prev, ...uniqueNewNodes]
      return getLayoutedElements(allNodes, edgesRef.current, 'TB').nodes
    })
    setEdges(prev => {
      const existingIds = new Set(prev.map(e => e.id))
      const uniqueNewEdges = newEdges.filter(e => !existingIds.has(e.id))
      return [...prev, ...uniqueNewEdges]
    })

    setExpandedNodes(prev => new Set([...prev, node.id]))
  } finally {
    setIsExpanding(false)
  }
}, [direction, selectedNodeTypes, selectedRelationTypes, expandedNodes])
```

- [ ] **Step 3: Add edges ref to persist between renders**

```typescript
const edgesRef = useRef<Edge[]>([])
useEffect(() => {
  edgesRef.current = edges
}, [edges])
```

- [ ] **Step 4: Add onClick to ReactFlow**

```typescript
<ReactFlow
  nodes={nodes}
  edges={edges}
  onNodesChange={onNodesChange}
  onEdgesChange={onEdgesChange}
  onNodeClick={onNodeClick}  // ADD THIS
  onInit={setReactFlowInstance}
  fitView
  fitViewOptions={{ padding: 0.2 }}
  proOptions={{ hideAttribution: true }}
>
```

- [ ] **Step 5: Add loading indicator for expand**

```typescript
{isExpanding && (
  <div className="absolute top-4 right-4 bg-white shadow-lg rounded-lg p-3 z-10">
    <div className="flex items-center gap-2">
      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
      <span className="text-sm">加载更多...</span>
    </div>
  </div>
)}
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/LineageTracking.tsx
git commit -m "feat: add click-to-expand to lineage tracking"
```

---

### Task 5: End-to-End Testing and Polish

- [ ] **Step 1: Test the complete flow**

Manual testing:
1. Navigate to a node detail page
2. Click "血缘追踪" button
3. Verify bidirectional lineage loads with Dagre layout
4. Test node type filter
5. Test relation type filter
6. Click a node to expand its lineage
7. Verify layout updates correctly

- [ ] **Step 2: Handle edge cases**

- Empty lineage paths - show "无血缘关系" message (already handled)
- API errors - show error state (already handled)
- Very large graphs - consider virtualization
- Single node (no relations) - show isolated node

- [ ] **Step 3: Final commit**

```bash
git add .
git commit -m "feat: complete lineage tracking view with filtering and expand"
```

---

## Implementation Complete

After completing all tasks, the lineage tracking feature will have:
- ✅ Bidirectional lineage (upstream + downstream)
- ✅ Dynamic depth calculation (auto-calc optimal depth)
- ✅ Node type filtering
- ✅ Relation type filtering
- ✅ Dagre layout algorithm
- ✅ Click-to-expand functionality
- ✅ React Flow with controls and minimap