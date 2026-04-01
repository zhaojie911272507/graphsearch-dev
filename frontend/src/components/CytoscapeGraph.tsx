import { useEffect, useRef, useState, useCallback } from 'react'
import CytoscapeComponent from 'react-cytoscapejs'
import { Core, LayoutOptions, EventObject } from 'cytoscape'
import { useQuery } from '@tanstack/react-query'
import { graphVizApi } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import {
  Search,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Layout,
  MousePointer,
  Trash2,
  Share2,
  RefreshCw,
  ChevronRight,
  X,
} from 'lucide-react'

type LayoutType = 'dagre' | 'cose' | 'circle' | 'grid' | 'breadthfirst'

interface GraphNode {
  id: string
  label: string
  type: string
  name: string
  quality_score?: number
}

interface GraphEdge {
  source: string
  target: string
  label: string
  weight?: number
}

interface GraphVizData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

// Node color mapping
const getNodeColor = (type: string): string => {
  const colors: Record<string, string> = {
    Document: '#3b82f6',
    Entity: '#10b981',
    Concept: '#8b5cf6',
    Chunk: '#6b7280',
    Annotation: '#f59e0b',
    Vote: '#ec4899',
    User: '#14b8a6',
  }
  return colors[type] || '#9ca3af'
}

interface CytoscapeGraphProps {
  layoutType?: LayoutType
  onNodeSelect?: (node: GraphNode) => void
}

export default function CytoscapeGraph({ layoutType = 'cose', onNodeSelect }: CytoscapeGraphProps) {
  const cyRef = useRef<Core | null>(null)
  const [layout, setLayout] = useState<LayoutType>(layoutType)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [showDetails, setShowDetails] = useState(false)
  const [selectedNodes, setSelectedNodes] = useState<string[]>([])

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['graph-viz'],
    queryFn: () => graphVizApi.getGraph({ limit: 200 }).then(res => res.data as Promise<GraphVizData>),
  })

  // Convert data to Cytoscape elements
  const elements = data
    ? [
        ...data.nodes.map(node => ({
          data: {
            id: node.id,
            label: node.label || node.name,
            type: node.type,
            name: node.name,
            quality_score: node.quality_score,
          },
        })),
        ...data.edges.map((edge, idx) => ({
          data: {
            id: `edge-${idx}`,
            source: edge.source,
            target: edge.target,
            label: edge.label,
          },
        })),
      ] as any[]
    : []

  // Cytoscape stylesheet
  const styleSheet = [
    {
      selector: 'node',
      style: {
        'background-color': (ele: any) => getNodeColor(ele.data('type')),
        'label': 'data(label)',
        'color': '#ffffff',
        'font-size': '10px',
        'text-valign': 'center',
        'text-halign': 'center',
        'width': 40,
        'height': 40,
        'border-width': 2,
        'border-color': '#1f2937',
      },
    },
    {
      selector: 'edge',
      style: {
        'width': 2,
        'line-color': '#9ca3af',
        'target-arrow-color': '#9ca3af',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        'label': 'data(label)',
        'font-size': '8px',
        'color': '#6b7280',
        'text-rotation': 'autorotate',
        'text-margin-y': -10,
      },
    },
    {
      selector: ':selected',
      style: {
        'border-width': 4,
        'border-color': '#fbbf24',
        'background-color': (ele: any) => getNodeColor(ele.data('type')),
      },
    },
    {
      selector: '.highlighted',
      style: {
        'border-width': 4,
        'border-color': '#fbbf24',
        'background-color': '#fbbf24',
      },
    },
    {
      selector: '.dimmed',
      style: {
        'opacity': 0.3,
      },
    },
  ] as any[]

  // Layout options
  const getLayoutOptions = (): LayoutOptions => {
    const commonOptions = {
      animate: true,
      animationDuration: 500,
    }

    switch (layout) {
      case 'dagre':
        return {
          ...commonOptions,
          name: 'dagre',
          rankDir: 'TB',
          nodeSep: 50,
          rankSep: 80,
        } as any
      case 'cose':
        return {
          ...commonOptions,
          name: 'cose',
          nodeRepulsion: 4500,
          idealEdgeLength: 100,
          gravity: 1,
          numIter: 1000,
        } as any
      case 'circle':
        return {
          ...commonOptions,
          name: 'circle',
          radius: 200,
        } as any
      case 'grid':
        return {
          ...commonOptions,
          name: 'grid',
          rows: Math.ceil(Math.sqrt(data?.nodes.length || 10)),
          spacing: 100,
        } as any
      case 'breadthfirst':
        return {
          ...commonOptions,
          name: 'breadthfirst',
          directed: true,
          padding: 10,
        } as any
      default:
        return commonOptions as LayoutOptions
    }
  }

  // Run layout
  const runLayout = useCallback(() => {
    if (cyRef.current) {
      const layout = cyRef.current.layout(getLayoutOptions())
      layout.run()
    }
  }, [layout, data])

  // Search functionality
  const handleSearch = useCallback(() => {
    if (!cyRef.current || !searchQuery.trim()) {
      // Clear highlights
      cyRef.current?.nodes().removeClass('highlighted dimmed')
      return
    }

    const query = searchQuery.toLowerCase()
    const nodes = cyRef.current?.nodes() || []

    nodes.forEach(node => {
      const label = node.data('label')?.toLowerCase() || ''
      const name = node.data('name')?.toLowerCase() || ''
      const type = node.data('type')?.toLowerCase() || ''

      if (label.includes(query) || name.includes(query) || type.includes(query)) {
        node.removeClass('dimmed').addClass('highlighted')
      } else {
        node.removeClass('highlighted').addClass('dimmed')
      }
    })
  }, [searchQuery])

  // Handle node click
  const handleNodeClick = useCallback((event: EventObject) => {
    const node = event.target
    const nodeData = {
      id: node.id(),
      label: node.data('label'),
      type: node.data('type'),
      name: node.data('name'),
      quality_score: node.data('quality_score'),
    }
    setSelectedNode(nodeData)
    setShowDetails(true)
    onNodeSelect?.(nodeData)
  }, [onNodeSelect])

  // Handle node tap (for right-click menu)
  const handleNodeTap = useCallback((event: EventObject) => {
    const node = event.target
    if (event.originalEvent?.ctrlKey || event.originalEvent?.metaKey) {
      // Multi-select with Ctrl/Cmd click
      const nodeId = node.id()
      setSelectedNodes(prev =>
        prev.includes(nodeId)
          ? prev.filter(id => id !== nodeId)
          : [...prev, nodeId]
      )
    }
  }, [])

  // Zoom controls
  const zoomIn = () => cyRef.current?.zoom(cyRef.current.zoom() * 1.2)
  const zoomOut = () => cyRef.current?.zoom(cyRef.current.zoom() / 1.2)
  const fitView = () => cyRef.current?.fit()

  // Delete selected nodes
  const deleteSelected = () => {
    if (selectedNodes.length > 0 && cyRef.current) {
      cyRef.current.nodes(`#${selectedNodes.join(', #')}`).remove()
      setSelectedNodes([])
    }
  }

  // Context menu position
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; nodeId: string } | null>(null)

  // Handle right-click
  const handleCxtTap = useCallback((event: EventObject) => {
    const node = event.target
    const position = event.position
    setContextMenu({
      x: position.x,
      y: position.y,
      nodeId: node.id(),
    })
  }, [])

  // Close context menu
  const closeContextMenu = () => setContextMenu(null)

  useEffect(() => {
    if (data) {
      runLayout()
    }
  }, [data, layout, runLayout])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">加载图数据...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent className="pt-6 text-center">
          <p className="text-red-600">加载图数据失败</p>
          <Button variant="outline" className="mt-4" onClick={() => refetch()}>
            重试
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="relative h-full w-full">
      {/* Toolbar */}
      <div className="absolute top-4 left-4 z-10 flex items-center gap-2 bg-white shadow-lg rounded-lg p-2">
        {/* Search */}
        <div className="flex items-center gap-1">
          <Input
            type="text"
            placeholder="搜索节点..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            className="w-40 h-8 text-sm"
          />
          <Button size="sm" variant="outline" onClick={handleSearch}>
            <Search className="h-4 w-4" />
          </Button>
        </div>

        <div className="w-px h-6 bg-gray-200" />

        {/* Layout selector */}
        <select
          value={layout}
          onChange={(e) => setLayout(e.target.value as LayoutType)}
          className="h-8 text-sm border rounded px-2"
        >
          <option value="dagre">Dagre (层级)</option>
          <option value="cose">Cose (力导向)</option>
          <option value="circle">Circle (圆形)</option>
          <option value="grid">Grid (网格)</option>
          <option value="breadthfirst">Breadthfirst (广度优先)</option>
        </select>

        <Button size="sm" variant="outline" onClick={runLayout}>
          <Layout className="h-4 w-4 mr-1" />
          应用布局
        </Button>

        <div className="w-px h-6 bg-gray-200" />

        {/* Zoom controls */}
        <Button size="sm" variant="outline" onClick={zoomIn}>
          <ZoomIn className="h-4 w-4" />
        </Button>
        <Button size="sm" variant="outline" onClick={zoomOut}>
          <ZoomOut className="h-4 w-4" />
        </Button>
        <Button size="sm" variant="outline" onClick={fitView}>
          <Maximize2 className="h-4 w-4" />
        </Button>

        <div className="w-px h-6 bg-gray-200" />

        {/* Refresh */}
        <Button size="sm" variant="outline" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4" />
        </Button>

        {/* Delete selected (if any) */}
        {selectedNodes.length > 0 && (
          <>
            <div className="w-px h-6 bg-gray-200" />
            <Button size="sm" variant="destructive" onClick={deleteSelected}>
              <Trash2 className="h-4 w-4 mr-1" />
              删除 ({selectedNodes.length})
            </Button>
          </>
        )}
      </div>

      {/* Graph */}
      <CytoscapeComponent
        elements={elements}
        style={{ width: '100%', height: '100%' }}
        stylesheet={styleSheet}
        cy={(cy: any) => {
          cyRef.current = cy
          cy.on('tap', 'node', handleNodeClick)
          cy.on('tap', 'node', handleNodeTap)
          cy.on('cxttap', 'node', handleCxtTap)
          cy.on('tap', () => closeContextMenu())
        }}
        layout={getLayoutOptions()}
        wheelSensitivity={0.3}
        minZoom={0.1}
        maxZoom={5}
      />

      {/* Context Menu */}
      {contextMenu && (
        <div
          className="absolute z-20 bg-white shadow-lg rounded-lg border py-1 min-w-[150px]"
          style={{ left: contextMenu.x + 10, top: contextMenu.y + 10 }}
          onClick={closeContextMenu}
        >
          <button
            className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 flex items-center gap-2"
            onClick={() => {
              setSelectedNode({
                id: contextMenu.nodeId,
                label: cyRef.current?.$(`#${contextMenu.nodeId}`).data('label') || '',
                type: cyRef.current?.$(`#${contextMenu.nodeId}`).data('type') || '',
                name: cyRef.current?.$(`#${contextMenu.nodeId}`).data('name') || '',
              })
              setShowDetails(true)
              closeContextMenu()
            }}
          >
            <MousePointer className="h-4 w-4" />
            查看详情
          </button>
          <button
            className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 flex items-center gap-2"
            onClick={() => {
              // TODO: Implement share functionality
              closeContextMenu()
            }}
          >
            <Share2 className="h-4 w-4" />
            分享
          </button>
          <button
            className="w-full px-4 py-2 text-left text-sm hover:bg-red-50 text-red-600 flex items-center gap-2"
            onClick={() => {
              cyRef.current?.$(`#${contextMenu.nodeId}`).remove()
              closeContextMenu()
            }}
          >
            <Trash2 className="h-4 w-4" />
            删除
          </button>
        </div>
      )}

      {/* Node Details Panel */}
      {showDetails && selectedNode && (
        <div className="absolute top-4 right-4 z-10 w-80">
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">节点详情</CardTitle>
                <Button variant="ghost" size="sm" onClick={() => setShowDetails(false)}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div>
                  <span className="text-xs text-gray-500">类型</span>
                  <div
                    className="inline-block px-2 py-1 rounded text-white text-sm"
                    style={{ backgroundColor: getNodeColor(selectedNode.type) }}
                  >
                    {selectedNode.type}
                  </div>
                </div>
                <div>
                  <span className="text-xs text-gray-500">名称</span>
                  <p className="font-medium">{selectedNode.name}</p>
                </div>
                <div>
                  <span className="text-xs text-gray-500">ID</span>
                  <p className="text-sm text-gray-600 font-mono">{selectedNode.id}</p>
                </div>
                {selectedNode.quality_score !== undefined && (
                  <div>
                    <span className="text-xs text-gray-500">质量评分</span>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2 bg-gray-200 rounded-full">
                        <div
                          className="h-2 bg-green-500 rounded-full"
                          style={{ width: `${selectedNode.quality_score * 100}%` }}
                        />
                      </div>
                      <span className="text-sm">{selectedNode.quality_score.toFixed(2)}</span>
                    </div>
                  </div>
                )}
                <div className="pt-2 flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    className="flex-1"
                    onClick={() => {
                      window.location.href = `/assets/${selectedNode.id}`
                    }}
                  >
                    查看详情
                    <ChevronRight className="h-4 w-4 ml-1" />
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="flex-1"
                    onClick={() => {
                      window.location.href = `/lineage/${selectedNode.id}`
                    }}
                  >
                    血缘追踪
                    <ChevronRight className="h-4 w-4 ml-1" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Legend */}
      <div className="absolute bottom-4 left-4 z-10">
        <Card className="bg-white/90">
          <CardContent className="p-3">
            <div className="text-xs text-gray-500 mb-2">图例</div>
            <div className="grid grid-cols-2 gap-2">
              {['Document', 'Entity', 'Concept', 'Chunk'].map(type => (
                <div key={type} className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: getNodeColor(type) }}
                  />
                  <span className="text-xs">{type}</span>
                </div>
              ))}
            </div>
            <div className="text-xs text-gray-400 mt-2">
              共 {data?.nodes.length || 0} 个节点，{data?.edges.length || 0} 条边
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}