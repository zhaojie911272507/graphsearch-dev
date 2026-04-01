import { useCallback, useEffect, useRef, useState } from 'react'
import ReactFlow, {
  MiniMap,
  Controls,
  Background,
  BackgroundVariant,
  useNodesState,
  useEdgesState,
  Node,
  Edge,
  ReactFlowInstance,
  MarkerType,
  Position,
} from 'reactflow'
import dagre from 'dagre'
import 'reactflow/dist/style.css'
import { useQuery } from '@tanstack/react-query'
import { assetApi } from '@/lib/api'
import { useParams } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { ArrowLeft, GitBranch, AlertCircle, XCircle, Filter } from 'lucide-react'
import { Link } from 'react-router-dom'

type LineageDirection = 'upstream' | 'downstream' | 'both'

// Dagre layout function
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

export default function LineageTracking() {
  const { nodeId } = useParams<{ nodeId: string }>()
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [direction, setDirection] = useState<LineageDirection>('both')
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance | null>(null)
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set())
  const [isExpanding, setIsExpanding] = useState(false)

  // Filter states
  const [selectedNodeTypes, setSelectedNodeTypes] = useState<string[]>([])
  const [selectedRelationTypes, setSelectedRelationTypes] = useState<string[]>([])
  const [availableNodeTypes, setAvailableNodeTypes] = useState<string[]>([])
  const [availableRelationTypes, setAvailableRelationTypes] = useState<string[]>([])

  // Ref to persist edges for layout calculations
  const edgesRef = useRef<Edge[]>([])
  useEffect(() => {
    edgesRef.current = edges
  }, [edges])

  const { data, isLoading, error } = useQuery({
    queryKey: ['lineage', nodeId, direction, selectedNodeTypes, selectedRelationTypes],
    queryFn: () =>
      assetApi
        .getLineage(
          nodeId!,
          direction !== 'both' ? direction : undefined,
          0, // 0 triggers auto-calculate
          selectedNodeTypes.length > 0 ? selectedNodeTypes : undefined,
          selectedRelationTypes.length > 0 ? selectedRelationTypes : undefined
        )
        .then(res => res.data),
    enabled: !!nodeId,
  })

  // Update available types when data loads
  useEffect(() => {
    if (data) {
      setAvailableNodeTypes(data.available_node_types || [])
      setAvailableRelationTypes(data.available_relation_types || [])
    }
  }, [data])

  const getNodeColor = useCallback((type: string) => {
    switch (type) {
      case 'Document':
        return '#3b82f6'
      case 'Entity':
        return '#10b981'
      case 'Concept':
        return '#8b5cf6'
      case 'Chunk':
        return '#6b7280'
      default:
        return '#9ca3af'
    }
  }, [])

  const getNodeShape = useCallback((type: string) => {
    switch (type) {
      case 'Document':
        return 'rectangle'
      case 'Entity':
        return 'ellipse'
      case 'Concept':
        return 'diamond'
      default:
        return 'circle'
    }
  }, [])

  // Helper to parse lineage paths and build nodes/edges
  const processLineageData = useCallback((lineageData: any) => {
    if (!lineageData || !lineageData.lineage_paths) {
      return { nodes: [], edges: [] }
    }

    const newNodes = new Map<string, Node>()
    const newEdges = new Map<string, Edge>()

    // Parse each lineage path
    lineageData.lineage_paths.forEach((pathItem: any, pathIndex: number) => {
      const pathNodes = pathItem.path || []

      // Add all nodes in the path
      pathNodes.forEach((node: any, nodeIndex: number) => {
        const nodeId = node.id || `node-${pathIndex}-${nodeIndex}`

        if (!newNodes.has(nodeId)) {
          // Calculate position based on path depth
          const x = 100 + nodeIndex * 200
          const y = 100 + pathIndex * 120

          newNodes.set(nodeId, {
            id: nodeId,
            position: { x, y },
            data: {
              label: node.label || node.name || nodeId,
              type: node.type || node.node_type || 'Unknown',
            },
            style: {
              backgroundColor: getNodeColor(node.type || node.node_type || 'Unknown'),
              border: `2px solid ${getNodeColor(node.type || node.node_type || 'Unknown')}`,
              width: nodeIndex === 0 || nodeIndex === pathNodes.length - 1 ? 140 : 100,
              height: 40,
              borderRadius: '4px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              fontSize: '12px',
              fontWeight: nodeIndex === 0 || nodeIndex === pathNodes.length - 1 ? 'bold' : 'normal',
            },
            type: getNodeShape(node.type || node.node_type || 'Unknown'),
          })
        }

        // Create edges between consecutive nodes
        if (nodeIndex < pathNodes.length - 1) {
          const nextNode = pathNodes[nodeIndex + 1]
          const nextNodeId = nextNode.id || `node-${pathIndex}-${nodeIndex + 1}`
          const edgeId = `e-${nodeId}-${nextNodeId}`

          if (!newEdges.has(edgeId)) {
            newEdges.set(edgeId, {
              id: edgeId,
              source: nodeId,
              target: nextNodeId,
              animated: true,
              style: {
                stroke: '#9ca3af',
                strokeWidth: 2,
              },
              markerEnd: {
                type: MarkerType.Arrow,
              },
            })
          }
        }
      })
    })

    return {
      nodes: Array.from(newNodes.values()),
      edges: Array.from(newEdges.values()),
    }
  }, [getNodeColor, getNodeShape])

  useEffect(() => {
    if (error) {
      console.error('Failed to fetch lineage:', error)
    }
  }, [error])

  useEffect(() => {
    if (!data) return

    // Use backend-provided nodes/edges if available, otherwise process from paths
    let processedNodes: Node[] = []
    let processedEdges: Edge[] = []

    if (data.nodes && data.nodes.length > 0) {
      // Use nodes from backend
      processedNodes = data.nodes.map((node: any) => ({
        id: node.id,
        position: { x: 0, y: 0 }, // Will be set by Dagre
        data: {
          label: node.name || node.label || node.id,
          type: node.node_type || node.type || 'Unknown',
        },
        style: {
          backgroundColor: getNodeColor(node.node_type || node.type || 'Unknown'),
          border: `2px solid ${getNodeColor(node.node_type || node.type || 'Unknown')}`,
          width: 140,
          height: 40,
          borderRadius: '4px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white',
          fontSize: '12px',
          fontWeight: 'bold',
        },
      }))

      processedEdges = data.edges.map((edge: any, idx: number) => ({
        id: `e-${idx}`,
        source: edge.source,
        target: edge.target,
        label: edge.label || '',
        animated: true,
        style: {
          stroke: '#9ca3af',
          strokeWidth: 2,
        },
        markerEnd: {
          type: MarkerType.Arrow,
        },
      }))
    } else {
      // Fallback: process from lineage_paths
      const result = processLineageData(data)
      processedNodes = result.nodes
      processedEdges = result.edges
    }

    // Apply Dagre layout
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      processedNodes,
      processedEdges,
      'TB'
    )

    setNodes(layoutedNodes)
    setEdges(layoutedEdges)

    // Fit view after nodes are updated
    setTimeout(() => {
      if (reactFlowInstance) {
        reactFlowInstance.fitView({ padding: 0.2 })
      }
    }, 100)
  }, [data, direction, processLineageData, setNodes, setEdges, reactFlowInstance])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">加载血缘关系...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent className="pt-6 text-center">
          <div className="flex flex-col items-center justify-center py-8">
            <XCircle className="h-16 w-16 text-red-500 mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">加载失败</h3>
            <p className="text-gray-600">无法加载血缘数据，请稍后重试或联系管理员</p>
            <Button variant="outline" className="mt-4" onClick={() => window.location.reload()}>
              重试
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!data?.lineage_paths || data.lineage_paths.length === 0) {
    return (
      <Card>
        <CardContent className="pt-6 text-center">
          <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600">未找到该节点的血缘关系</p>
          <p className="text-sm text-gray-500 mt-2">
            此节点可能是孤立节点，或血缘深度设置过小
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Link to={`/assets/${nodeId}`}>
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              返回节点详情
            </Button>
          </Link>
        </div>

        <div className="flex items-center gap-x-4">
          <div className="text-sm text-gray-600">
            <span className="font-medium">上游：</span>
            {data.upstream_count || 0} 个节点
            <span className="mx-2">|</span>
            <span className="font-medium">下游：</span>
            {data.downstream_count || 0} 个节点
          </div>

          <div className="flex gap-x-2">
            <Button
              variant={direction === 'upstream' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setDirection('upstream')}
            >
              <GitBranch className="h-4 w-4 mr-1" />
              上游
            </Button>
            <Button
              variant={direction === 'both' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setDirection('both')}
            >
              <GitBranch className="h-4 w-4 mr-1" />
              全部
            </Button>
            <Button
              variant={direction === 'downstream' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setDirection('downstream')}
            >
              <GitBranch className="h-4 w-4 mr-1" />
              下游
            </Button>
          </div>

          {/* Node type filter */}
          {availableNodeTypes.length > 0 && (
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-gray-500" />
              <select
                multiple
                className="border rounded px-2 py-1 text-sm min-w-[120px] h-8"
                value={selectedNodeTypes}
                onChange={(e) => {
                  const values = Array.from(e.target.selectedOptions, o => o.value)
                  setSelectedNodeTypes(values)
                }}
              >
                {availableNodeTypes.map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>
          )}

          {/* Relation type filter */}
          {availableRelationTypes.length > 0 && (
            <div className="flex items-center gap-2">
              <select
                multiple
                className="border rounded px-2 py-1 text-sm min-w-[120px] h-8"
                value={selectedRelationTypes}
                onChange={(e) => {
                  const values = Array.from(e.target.selectedOptions, o => o.value)
                  setSelectedRelationTypes(values)
                }}
              >
                {availableRelationTypes.map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>
          )}

          {/* Clear filters */}
          {(selectedNodeTypes.length > 0 || selectedRelationTypes.length > 0) && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setSelectedNodeTypes([])
                setSelectedRelationTypes([])
              }}
            >
              清除过滤
            </Button>
          )}
        </div>
      </div>

      {/* Loading indicator for expand */}
      {isExpanding && (
        <div className="absolute top-20 right-4 bg-white shadow-lg rounded-lg p-3 z-10">
          <div className="flex items-center gap-2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
            <span className="text-sm">加载更多...</span>
          </div>
        </div>
      )}

      <Card className="h-[700px]">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>血缘追踪</CardTitle>
              <CardDescription>
                展示节点的数据来源和派生关系
              </CardDescription>
            </div>
            <div className="text-sm bg-blue-50 text-blue-700 px-3 py-1 rounded-full">
              共 {data.lineage_paths.length} 条路径
            </div>
          </div>
        </CardHeader>
        <CardContent className="h-[calc(100%-80px)]">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onInit={setReactFlowInstance}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            proOptions={{ hideAttribution: true }}
            onNodeClick={async (_event, node) => {
              if (expandedNodes.has(node.id)) {
                // Already expanded, show details (could navigate to node detail)
                return
              }
              // Expand node lineage
              setIsExpanding(true)
              try {
                const expandData = await assetApi.getLineage(
                  node.id,
                  direction !== 'both' ? direction : undefined,
                  1,
                  selectedNodeTypes.length > 0 ? selectedNodeTypes : undefined,
                  selectedRelationTypes.length > 0 ? selectedRelationTypes : undefined
                ).then(res => res.data)

                // Merge new nodes and edges
                let newNodes: Node[] = []
                let newEdges: Edge[] = []

                if (expandData.nodes && expandData.nodes.length > 0) {
                  newNodes = expandData.nodes.map((n: any) => ({
                    id: n.id,
                    position: { x: 0, y: 0 },
                    data: {
                      label: n.name || n.label || n.id,
                      type: n.node_type || n.type || 'Unknown',
                    },
                    style: {
                      backgroundColor: getNodeColor(n.node_type || n.type || 'Unknown'),
                      border: `2px solid ${getNodeColor(n.node_type || n.type || 'Unknown')}`,
                      width: 100,
                      height: 40,
                      borderRadius: '4px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'white',
                      fontSize: '12px',
                    },
                  }))

                  newEdges = expandData.edges.map((e: any, idx: number) => ({
                    id: `e-expand-${idx}`,
                    source: e.source,
                    target: e.target,
                    label: e.label || '',
                    animated: true,
                    style: { stroke: '#9ca3af', strokeWidth: 2 },
                    markerEnd: { type: MarkerType.Arrow },
                  }))
                }

                // Merge with existing
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
              } catch (err) {
                console.error('Failed to expand node:', err)
              } finally {
                setIsExpanding(false)
              }
            }}
          >
            <Controls />
            <MiniMap />
            <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
          </ReactFlow>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">图例说明</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded-sm bg-blue-500"></div>
              <span className="text-sm">Document</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded-full bg-green-500"></div>
              <span className="text-sm">Entity</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-purple-500" style={{ clipPath: 'polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)' }}></div>
              <span className="text-sm">Concept</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-gray-500 rounded"></div>
              <span className="text-sm">Chunk</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
