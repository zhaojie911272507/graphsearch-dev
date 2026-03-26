import { useCallback, useEffect, useState } from 'react'
import ReactFlow, {
  ReactFlowProvider,
  MiniMap,
  Controls,
  Background,
  BackgroundVariant,
  useNodesState,
  useEdgesState,
  Node,
  Edge,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { useQuery } from '@tanstack/react-query'
import { assetApi } from '@/lib/api'
import { useParams } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { ArrowLeft, GitBranch } from 'lucide-react'
import { Link } from 'react-router-dom'

type LineageDirection = 'upstream' | 'downstream' | 'both'

function LineageFlow() {
  const { nodeId } = useParams<{ nodeId: string }>()
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [direction, setDirection] = useState<LineageDirection>('both')

  const { data, isLoading } = useQuery({
    queryKey: ['lineage', nodeId, direction],
    queryFn: () =>
      assetApi
        .getLineage(nodeId!, direction !== 'both' ? direction : undefined, 3)
        .then(res => res.data),
    enabled: !!nodeId,
  })

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

  useEffect(() => {
    if (!data) return

    const newNodes: Node[] = []
    const newEdges: Edge[] = []

    // Add the central node
    if (data.node) {
      newNodes.push({
        id: data.node.id,
        position: { x: 400, y: 300 },
        data: {
          label: data.node.name,
          type: data.node.node_type,
        },
        style: {
          backgroundColor: getNodeColor(data.node.node_type),
          border: `2px solid ${getNodeColor(data.node.node_type)}`,
          width: 120,
          height: 40,
        },
        type: getNodeShape(data.node.node_type),
      })
    }

    // Process upstream nodes
    if (direction === 'upstream' || direction === 'both') {
      data.upstream?.forEach((item: any, index: number) => {
        const nodeId = `up-${index}`
        newNodes.push({
          id: nodeId,
          position: { x: 200, y: 150 + index * 100 },
          data: {
            label: item.node.name,
            type: item.node.node_type,
          },
          style: {
            backgroundColor: getNodeColor(item.node.node_type),
            border: `2px solid ${getNodeColor(item.node.node_type)}`,
            width: 100,
            height: 35,
          },
          type: getNodeShape(item.node.node_type),
        })

        newEdges.push({
          id: `e-${nodeId}-${data.node?.id}`,
          source: nodeId,
          target: data.node?.id,
          label: item.relation_type,
          animated: true,
          style: {
            stroke: '#9ca3af',
            strokeWidth: 2,
          },
        })
      })
    }

    // Process downstream nodes
    if (direction === 'downstream' || direction === 'both') {
      data.downstream?.forEach((item: any, index: number) => {
        const nodeId = `down-${index}`
        newNodes.push({
          id: nodeId,
          position: { x: 600, y: 150 + index * 100 },
          data: {
            label: item.node.name,
            type: item.node.node_type,
          },
          style: {
            backgroundColor: getNodeColor(item.node.node_type),
            border: `2px solid ${getNodeColor(item.node.node_type)}`,
            width: 100,
            height: 35,
          },
          type: getNodeShape(item.node.node_type),
        })

        newEdges.push({
          id: `e-${data.node?.id}-${nodeId}`,
          source: data.node?.id,
          target: nodeId,
          label: item.relation_type,
          animated: true,
          style: {
            stroke: '#9ca3af',
            strokeWidth: 2,
          },
        })
      })
    }

    setNodes(newNodes)
    setEdges(newEdges)
  }, [data, direction, getNodeColor, getNodeShape, setNodes, setEdges])

  if (isLoading) {
    return <div className="text-center py-12">加载血缘关系...</div>
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
      </div>

      <Card className="h-[700px]">
        <CardHeader>
          <CardTitle>血缘追踪</CardTitle>
        </CardHeader>
        <CardContent className="h-[calc(100%-60px)]">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            fitView
            fitViewOptions={{ padding: 0.2 }}
          >
            <Controls />
            <MiniMap />
            <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
          </ReactFlow>
        </CardContent>
      </Card>
    </div>
  )
}

export function LineageTracking() {
  return (
    <ReactFlowProvider>
      <LineageFlow />
    </ReactFlowProvider>
  )
}
