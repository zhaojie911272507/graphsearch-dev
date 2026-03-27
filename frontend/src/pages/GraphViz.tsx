import { useEffect, useRef, useState, useCallback } from 'react'
import * as d3 from 'd3'
import { useQuery } from '@tanstack/react-query'
import { graphVizApi } from '@/lib/api'
import { Card, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { ScrollArea } from '@/components/ui/ScrollArea'
import { Badge } from '@/components/ui/Badge'
import { EntityExtractPanel } from '@/components/EntityExtractPanel'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/Dialog'
import { X, Maximize, Minimize, Eye, EyeOff, ChevronRight, FolderOpen, Clock, Tag, Key, FileText, Sigma, Sparkles } from 'lucide-react'

interface GraphNode {
  id: string
  label: string
  type: string
  name: string
  quality_score?: number
  properties?: Record<string, any>
  summary?: string
  labels?: string[]
  created_at?: string
  updated_at?: string
}

interface GraphEdge {
  source: string
  target: string
  label: string
  weight?: number
  properties?: Record<string, any>
}

interface GraphVizData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

interface LinkDatum {
  source: any
  target: any
  label: string
  weight?: number
  properties?: Record<string, any>
  isSelfLoop?: boolean
  selfLoopIndex?: number
  totalSelfLoops?: number
}

interface NodeDatum extends d3.SimulationNodeDatum {
  id: string
  label: string
  type: string
  name: string
  quality_score?: number
  properties?: Record<string, any>
  summary?: string
  labels?: string[]
  created_at?: string
  updated_at?: string
  selfLoops?: LinkDatum[]
}

interface SelfLoopGroup {
  nodeId: string
  nodeName: string
  loops: LinkDatum[]
  isExpanded: boolean
}

// Entity type colors (MiroFish style)
const ENTITY_COLORS: Record<string, string> = {
  Entity: '#10b981',
  Concept: '#8b5cf6',
  Document: '#3b82f6',
  Chunk: '#6b7280',
  Agent: '#f59e0b',
  Memory: '#ec4899',
  Interaction: '#06b6d4',
  SimulationSession: '#84cc16',
  World: '#f43f5e',
  Seed: '#14b8a6',
}

const getNodeColor = (type: string): string => {
  return ENTITY_COLORS[type] || '#6b7280'
}

export function GraphViz() {
  const containerRef = useRef<HTMLDivElement>(null)
  const svgRef = useRef<SVGSVGElement>(null)
  const [selectedNode, setSelectedNode] = useState<NodeDatum | null>(null)
  const [selectedEdge, setSelectedEdge] = useState<LinkDatum | null>(null)
  const [selectedSelfLoopGroup, setSelectedSelfLoopGroup] = useState<SelfLoopGroup | null>(null)
  const [showEdgeLabels, setShowEdgeLabels] = useState(true)
  const [isMaximized, setIsMaximized] = useState(false)
  const [showEntityExtract, setShowEntityExtract] = useState(false)
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 })

  const { data, isLoading } = useQuery({
    queryKey: ['graphViz'],
    queryFn: () =>
      graphVizApi.getGraph({ limit: 100 }).then((res) => res.data as GraphVizData),
  })

  // Calculate dimensions
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const { width, height } = containerRef.current.getBoundingClientRect()
        setDimensions({ width, height })
      }
    }

    updateDimensions()
    window.addEventListener('resize', updateDimensions)
    return () => window.removeEventListener('resize', updateDimensions)
  }, [])

  const drawGraph = useCallback(() => {
    if (!svgRef.current || !data || !dimensions.width) return

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const width = dimensions.width
    const height = Math.max(600, dimensions.height - 48)

    // Create groups
    const linkGroup = svg.append('g').attr('class', 'links')
    const nodeGroup = svg.append('g').attr('class', 'nodes')

    // Process nodes and edges
    const nodesMap = new Map<string, NodeDatum>()
    const links: LinkDatum[] = []

    // Add all nodes
    data.nodes.forEach((node) => {
      nodesMap.set(node.id, {
        ...node,
        x: width / 2 + (Math.random() - 0.5) * 100,
        y: height / 2 + (Math.random() - 0.5) * 100,
        selfLoops: [],
      })
    })

    // Process edges and detect self-loops
    const selfLoopEdges: Record<string, LinkDatum[]> = {}

    data.edges.forEach((edge) => {
      const sourceNode = nodesMap.get(edge.source)
      const targetNode = nodesMap.get(edge.target)

      if (!sourceNode || !targetNode) return

      const linkDatum: LinkDatum = {
        source: sourceNode,
        target: targetNode,
        label: edge.label,
        weight: edge.weight || 0,
        properties: edge.properties,
        isSelfLoop: edge.source === edge.target,
      }

      if (linkDatum.isSelfLoop) {
        if (!selfLoopEdges[edge.source]) {
          selfLoopEdges[edge.source] = []
        }
        selfLoopEdges[edge.source].push(linkDatum)
      } else {
        links.push(linkDatum)
      }
    })

    // Merge self-loops per node
    Object.entries(selfLoopEdges).forEach(([nodeId, selfLoops]) => {
      const node = nodesMap.get(nodeId)
      if (node) {
        node.selfLoops = selfLoops
        // Add a representative self-loop link for visualization
        if (selfLoops.length > 0) {
          links.push({
            ...selfLoops[0],
            totalSelfLoops: selfLoops.length,
          })
        }
      }
    })

    const nodes = Array.from(nodesMap.values())

    // Create force simulation
    const simulation = d3
      .forceSimulation<NodeDatum>(nodes)
      .force('link', d3.forceLink<NodeDatum, LinkDatum>(links).id((d: any) => d.id).distance(150))
      .force('charge', d3.forceManyBody().strength(-500))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collide', d3.forceCollide().radius(35))
      .force('x', d3.forceX(width / 2).strength(0.05))
      .force('y', d3.forceY(height / 2).strength(0.05))

    // Draw links
    const link = linkGroup
      .selectAll<SVGLineElement, LinkDatum>('line')
      .data(links)
      .join('line')
      .attr('stroke', (d) => {
        if (d.isSelfLoop) return '#9ca3af'
        return d.weight && d.weight > 0.8 ? '#10b981' : '#9ca3af'
      })
      .attr('stroke-opacity', 0.6)
      .attr('stroke-width', (d) => {
        if (d.isSelfLoop) return 1.5
        return d.weight && d.weight > 0.8 ? 3 : 2
      })
      .attr('cursor', 'pointer')
      .on('click', (event, d) => {
        event.stopPropagation()
        setSelectedEdge(d)
        setSelectedNode(null)
      })

    // Draw self-loop arcs
    const selfLoopArcs = linkGroup
      .selectAll<SVGPathElement, LinkDatum>('path.self-loop')
      .data(links.filter((d) => d.isSelfLoop || d.totalSelfLoops))
      .join('path')
      .attr('class', 'self-loop')
      .attr('fill', 'none')
      .attr('stroke', '#9ca3af')
      .attr('stroke-opacity', 0.6)
      .attr('stroke-width', 1.5)
      .attr('cursor', 'pointer')
      .on('click', (event, d) => {
        event.stopPropagation()
        setSelectedEdge(d)
        setSelectedNode(null)
      })

    // Draw self-loop count badges
    const selfLoopBadges = nodeGroup
      .selectAll<SVGGElement, NodeDatum>('g.self-loop-badge')
      .data(nodes.filter((n) => n.selfLoops && n.selfLoops.length > 0))
      .join('g')
      .attr('class', 'self-loop-badge')
      .attr('cursor', 'pointer')
      .on('click', (event, d) => {
        event.stopPropagation()
        setSelectedNode(d)
        setSelectedSelfLoopGroup({
          nodeId: d.id,
          nodeName: d.name,
          loops: d.selfLoops!,
          isExpanded: true,
        })
      })

    selfLoopBadges
      .append('circle')
      .attr('r', 10)
      .attr('fill', '#f59e0b')
      .attr('stroke', '#1f2937')
      .attr('stroke-width', 1.5)

    selfLoopBadges
      .append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .attr('fill', '#ffffff')
      .attr('font-size', '8px')
      .attr('font-weight', 'bold')
      .text((d) => (d.selfLoops!.length > 99 ? '99+' : d.selfLoops!.length.toString()))

    // Draw nodes
    const node = nodeGroup
      .selectAll<SVGGElement, NodeDatum>('g.node')
      .data(nodes)
      .join('g')
      .attr('class', 'node')
      .call(
        d3
          .drag<SVGGElement, NodeDatum>()
          .on('start', (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart()
            d.fx = d.x
            d.fy = d.y
          })
          .on('drag', (event, d) => {
            d.fx = event.x
            d.fy = event.y
          })
          .on('end', (event, d) => {
            if (!event.active) simulation.alphaTarget(0)
            d.fx = null
            d.fy = null
          })
      )
      .on('click', (event, d) => {
        event.stopPropagation()
        setSelectedNode(d)
        setSelectedEdge(null)
      })

    // Node circles
    node
      .append('circle')
      .attr('r', 18)
      .attr('fill', (d) => getNodeColor(d.type))
      .attr('stroke', '#1f2937')
      .attr('stroke-width', 2)
      .attr('cursor', 'pointer')

    // Node labels
    node
      .append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '0.3em')
      .attr('fill', '#ffffff')
      .attr('font-size', '10px')
      .attr('pointer-events', 'none')
      .text((d) => (d.label.length > 12 ? d.label.substring(0, 10) + '...' : d.label))

    // Node type indicator (outer ring)
    node
      .append('circle')
      .attr('r', 22)
      .attr('fill', 'none')
      .attr('stroke', (d) => getNodeColor(d.type))
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '2,2')
      .attr('opacity', 0.5)

    // Edge labels
    if (showEdgeLabels) {
      const edgeLabels = svg
        .selectAll<SVGTextElement, LinkDatum>('text.edge-label')
        .data(links.filter((d) => !d.isSelfLoop && !d.totalSelfLoops))
        .join('text')
        .attr('class', 'edge-label')
        .attr('text-anchor', 'middle')
        .attr('dy', '-0.2em')
        .attr('fill', '#9ca3af')
        .attr('font-size', '9px')
        .attr('pointer-events', 'none')
        .attr('background-color', '#1f2937')
        .text((d) => d.label)

      simulation.on('tick', () => {
        link.attr('x1', (d) => d.source.x!).attr('y1', (d) => d.source.y!).attr('x2', (d) => d.target.x!).attr('y2', (d) => d.target.y!)

        selfLoopArcs.attr('d', (d) => {
          const x = d.source.x!
          const y = d.source.y!
          const radius = 25 + (d.selfLoopIndex || 0) * 8
          return `M ${x - radius} ${y} A ${radius} ${radius} 0 1 1 ${x + radius} ${y}`
        })

        edgeLabels.attr('x', (d) => (d.source.x! + d.target.x!) / 2).attr('y', (d) => (d.source.y! + d.target.y!) / 2)

        node.attr('transform', (d) => `translate(${d.x}, ${d.y})`)

        // Update self-loop badge positions
        selfLoopBadges.attr('transform', (d) => {
          const badgeX = d.x! + 28
          const badgeY = d.y! - 28
          return `translate(${badgeX}, ${badgeY})`
        })
      })
    } else {
      simulation.on('tick', () => {
        link.attr('x1', (d) => d.source.x!).attr('y1', (d) => d.source.y!).attr('x2', (d) => d.target.x!).attr('y2', (d) => d.target.y!)

        selfLoopArcs.attr('d', (d) => {
          const x = d.source.x!
          const y = d.source.y!
          const radius = 25 + (d.selfLoopIndex || 0) * 8
          return `M ${x - radius} ${y} A ${radius} ${radius} 0 1 1 ${x + radius} ${y}`
        })

        node.attr('transform', (d) => `translate(${d.x}, ${d.y})`)

        // Update self-loop badge positions
        selfLoopBadges.attr('transform', (d) => {
          const badgeX = d.x! + 28
          const badgeY = d.y! - 28
          return `translate(${badgeX}, ${badgeY})`
        })
      })
    }

    // Store simulation for cleanup
    ;(svg as any).__simulation = simulation
  }, [data, dimensions, showEdgeLabels])

  useEffect(() => {
    if (!isLoading && data) {
      drawGraph()
    }

    return () => {
      if (svgRef.current) {
        const svg = d3.select(svgRef.current)
        const sim = (svg as any).__simulation as d3.Simulation<any, undefined> | undefined
        if (sim) {
          sim.stop()
        }
      }
    }
  }, [isLoading, data, drawGraph])

  // Calculate entity type stats for legend
  const entityStats = data?.nodes.reduce((acc, node) => {
    acc[node.type] = (acc[node.type] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const handleMaximize = () => {
    setIsMaximized(!isMaximized)
  }

  const handleCloseDetail = () => {
    setSelectedNode(null)
    setSelectedEdge(null)
    setSelectedSelfLoopGroup(null)
  }

  if (isLoading) {
    return (
      <div className="text-center py-12">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        <p className="mt-4 text-muted-foreground">加载图谱数据...</p>
      </div>
    )
  }

  return (
    <div className={`space-y-4 ${isMaximized ? 'fixed inset-4 z-50 bg-background' : ''}`}>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">图谱可视化</h1>
          <p className="text-muted-foreground mt-1">交互式知识图谱可视化 (MiroFish 风格)</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setShowEntityExtract(!showEntityExtract)}>
            <Sparkles className="h-4 w-4 mr-2" />
            本体抽取
          </Button>
          <Button variant="outline" size="sm" onClick={() => setShowEdgeLabels(!showEdgeLabels)}>
            {showEdgeLabels ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </Button>
          <Button variant="outline" size="sm" onClick={handleMaximize}>
            {isMaximized ? <Minimize className="h-4 w-4" /> : <Maximize className="h-4 w-4" />}
          </Button>
        </div>
      </div>

      {/* MiroFish Style Dual-Column Layout */}
      <div className={`flex gap-4 ${isMaximized ? 'h-[calc(100vh-100px)]' : ''}`}>
        {/* Left: Graph Container */}
        <div className={`flex-1 ${selectedNode || selectedEdge ? 'flex-[2]' : 'flex-1'} transition-all duration-300`}>
          <Card className="overflow-hidden h-full">
            <CardContent className="p-0 relative h-full">
              <div
                ref={containerRef}
                className="relative h-full"
                style={{ minHeight: isMaximized ? 'unset' : '600px' }}
              >
                <svg ref={svgRef} width="100%" height="100%" className="bg-muted/30" />

                {/* Entity Type Legend - MiroFish Style */}
                <div className="absolute top-4 left-4 bg-card/95 backdrop-blur-sm border border-border rounded-xl p-3 shadow-xl max-h-48 overflow-y-auto">
                  <h3 className="text-sm font-semibold mb-2.5 flex items-center gap-2 sticky top-0 bg-card/95 backdrop-blur-sm py-1">
                    <FolderOpen className="h-4 w-4 text-primary" />
                    实体类型图例
                  </h3>
                  <div className="space-y-2">
                    {Object.entries(entityStats || {}).map(([type, count]) => (
                      <div key={type} className="flex items-center gap-2.5 text-xs group hover:bg-muted/50 p-1 rounded transition-colors cursor-pointer">
                        <div
                          className="w-3 h-3 rounded-full flex-shrink-0 transition-transform group-hover:scale-110"
                          style={{ backgroundColor: getNodeColor(type), boxShadow: `0 0 10px ${getNodeColor(type)}60` }}
                        />
                        <span className="text-muted-foreground flex-1 font-medium">{type}</span>
                        <Badge variant="secondary" className="text-xs h-4.5 px-1.5 min-w-[1.5rem] justify-center bg-muted/80">
                          {count}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Graph Controls */}
                <div className="absolute bottom-4 left-4 flex gap-2">
                  <Badge variant="outline" className="bg-card/80 backdrop-blur">
                    {data?.nodes.length || 0} 节点
                  </Badge>
                  <Badge variant="outline" className="bg-card/80 backdrop-blur">
                    {data?.edges.length || 0} 关系
                  </Badge>
                </div>

                {/* Right: Detail Panel - MiroFish Style */}
                {(selectedNode || selectedEdge || selectedSelfLoopGroup) && (
                  <div className="absolute top-0 right-0 h-full w-96 bg-card border-l border-border shadow-xl overflow-hidden flex flex-col">
                    {/* Panel Header */}
                    <div className="flex items-center justify-between p-4 border-b border-border bg-muted/30">
                      <h3 className="font-semibold text-lg flex items-center gap-2">
                        {selectedNode && (
                          <>
                            <div
                              className="w-3 h-3 rounded-full"
                              style={{ backgroundColor: getNodeColor(selectedNode.type) }}
                            />
                            节点详情
                          </>
                        )}
                        {selectedEdge && !selectedSelfLoopGroup && (
                          <>
                            <Sigma className="h-4 w-4" />
                            关系详情
                          </>
                        )}
                        {selectedSelfLoopGroup && (
                          <>
                            <FolderOpen className="h-4 w-4" />
                            自环关系 ({selectedSelfLoopGroup.loops.length})
                          </>
                        )}
                      </h3>
                      <Button variant="ghost" size="sm" onClick={handleCloseDetail}>
                        <X className="h-4 w-4" />
                      </Button>
                    </div>

                    {/* Panel Content */}
                    <ScrollArea className="flex-1 p-4">
                      {/* Selected Node Detail */}
                      {selectedNode && !selectedSelfLoopGroup && (
                        <div className="space-y-4">
                          {/* Basic Info Card */}
                          <div className="space-y-3">
                            <div className="pb-3 border-b border-border">
                              <h4 className="font-semibold text-lg break-all mb-1">{selectedNode.name}</h4>
                              <div className="flex items-center gap-2 flex-wrap">
                                <Badge variant="secondary" className="text-xs">
                                  {selectedNode.type}
                                </Badge>
                                {selectedNode.labels?.map((label, idx) => (
                                  <Badge key={idx} variant="outline" className="text-xs">
                                    <Tag className="h-3 w-3 mr-1" />
                                    {label}
                                  </Badge>
                                ))}
                              </div>
                            </div>

                            {/* ID */}
                            <div className="space-y-1">
                              <label className="text-xs text-muted-foreground flex items-center gap-1">
                                <Key className="h-3 w-3" />
                                UUID
                              </label>
                              <p className="text-xs font-mono text-muted-foreground break-all bg-muted/50 p-2 rounded">
                                {selectedNode.id}
                              </p>
                            </div>

                            {/* Created Time */}
                            {(selectedNode.created_at || selectedNode.updated_at) && (
                              <div className="space-y-1">
                                <label className="text-xs text-muted-foreground flex items-center gap-1">
                                  <Clock className="h-3 w-3" />
                                  时间信息
                                </label>
                                {selectedNode.created_at && (
                                  <p className="text-xs text-muted-foreground">
                                    创建：{new Date(selectedNode.created_at).toLocaleString('zh-CN')}
                                  </p>
                                )}
                                {selectedNode.updated_at && (
                                  <p className="text-xs text-muted-foreground">
                                    更新：{new Date(selectedNode.updated_at).toLocaleString('zh-CN')}
                                  </p>
                                )}
                              </div>
                            )}

                            {/* Quality Score */}
                            {selectedNode.quality_score !== undefined && selectedNode.quality_score !== null && (
                              <div className="space-y-1">
                                <label className="text-xs text-muted-foreground">质量分数</label>
                                <div className="flex items-center gap-2">
                                  <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                                    <div
                                      className="h-full bg-gradient-to-r from-primary/60 to-primary"
                                      style={{ width: `${Math.min(100, selectedNode.quality_score * 100)}%` }}
                                    />
                                  </div>
                                  <span className="text-sm font-medium tabular-nums">
                                    {selectedNode.quality_score.toFixed(2)}
                                  </span>
                                </div>
                              </div>
                            )}
                          </div>

                          {/* Summary Card */}
                          {selectedNode.summary && (
                            <div className="space-y-1">
                              <label className="text-xs text-muted-foreground flex items-center gap-1">
                                <FileText className="h-3 w-3" />
                                摘要
                              </label>
                              <p className="text-sm text-muted-foreground bg-muted/30 p-3 rounded leading-relaxed">
                                {selectedNode.summary}
                              </p>
                            </div>
                          )}

                          {/* Properties Card */}
                          {selectedNode.properties && Object.keys(selectedNode.properties).length > 0 && (
                            <div className="space-y-2">
                              <label className="text-xs text-muted-foreground font-medium">属性 ({Object.keys(selectedNode.properties).length})</label>
                              <div className="space-y-1.5">
                                {Object.entries(selectedNode.properties).map(([key, value]) => (
                                  <div key={key} className="flex gap-2 text-xs p-2 bg-muted/30 rounded">
                                    <span className="font-medium text-primary min-w-[100px]">{key}:</span>
                                    <span className="text-muted-foreground flex-1 break-all">
                                      {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Self-loops Summary */}
                          {selectedNode.selfLoops && selectedNode.selfLoops.length > 0 && (
                            <div className="space-y-2">
                              <label className="text-xs text-muted-foreground font-medium">自环关系</label>
                              <Button
                                variant="outline"
                                size="sm"
                                className="w-full justify-start"
                                onClick={() => {
                                  setSelectedSelfLoopGroup({
                                    nodeId: selectedNode.id,
                                    nodeName: selectedNode.name,
                                    loops: selectedNode.selfLoops!,
                                    isExpanded: true,
                                  })
                                }}
                              >
                                <FolderOpen className="h-4 w-4 mr-2" />
                                查看 {selectedNode.selfLoops.length} 个自环关系
                                <ChevronRight className="h-4 w-4 ml-auto" />
                              </Button>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Selected Self-Loop Group Detail */}
                      {selectedSelfLoopGroup && (
                        <div className="space-y-3">
                          <div className="pb-3 border-b border-border">
                            <p className="text-sm text-muted-foreground">节点：</p>
                            <p className="font-medium break-all">{selectedSelfLoopGroup.nodeName}</p>
                          </div>

                          <div className="space-y-2">
                            {selectedSelfLoopGroup.loops.map((loop, idx) => (
                              <div
                                key={idx}
                                className="border border-border rounded-lg p-3 space-y-2 hover:bg-muted/30 cursor-pointer transition-colors"
                                onClick={() => {
                                  setSelectedEdge(loop)
                                  setSelectedSelfLoopGroup(null)
                                }}
                              >
                                <div className="flex items-center justify-between">
                                  <Badge variant="outline" className="text-xs">
                                    #{idx + 1}
                                  </Badge>
                                  <span className="text-xs text-muted-foreground">{loop.label}</span>
                                </div>
                                {loop.properties && Object.keys(loop.properties).length > 0 && (
                                  <pre className="text-xs bg-muted/50 p-2 rounded overflow-auto max-h-20">
                                    {JSON.stringify(loop.properties, null, 2)}
                                  </pre>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Selected Edge Detail */}
                      {selectedEdge && !selectedSelfLoopGroup && (
                        <div className="space-y-4">
                          <div className="pb-3 border-b border-border">
                            <div className="flex items-center gap-2 mb-2">
                              <Badge variant="secondary">{selectedEdge.label}</Badge>
                            </div>
                            {selectedEdge.isSelfLoop || selectedEdge.totalSelfLoops ? (
                              <p className="text-sm text-muted-foreground">
                                自环关系：{selectedEdge.totalSelfLoops || 1} 个
                              </p>
                            ) : (
                              <div className="flex items-center gap-2 text-sm">
                                <span className="text-muted-foreground">
                                  {(selectedEdge.source as any).name}
                                </span>
                                <ChevronRight className="h-4 w-4" />
                                <span className="text-muted-foreground">
                                  {(selectedEdge.target as any).name}
                                </span>
                              </div>
                            )}
                          </div>

                          {/* Weight */}
                          {selectedEdge.weight !== undefined && selectedEdge.weight !== null && (
                            <div className="space-y-1">
                              <label className="text-xs text-muted-foreground">权重</label>
                              <div className="flex items-center gap-2">
                                <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-gradient-to-r from-primary/60 to-primary"
                                    style={{ width: `${Math.min(100, selectedEdge.weight * 100)}%` }}
                                  />
                                </div>
                                <span className="text-sm font-medium tabular-nums">
                                  {selectedEdge.weight.toFixed(2)}
                                </span>
                              </div>
                            </div>
                          )}

                          {/* Properties */}
                          {selectedEdge.properties && Object.keys(selectedEdge.properties).length > 0 && (
                            <div className="space-y-2">
                              <label className="text-xs text-muted-foreground font-medium">属性</label>
                              <div className="space-y-1.5">
                                {Object.entries(selectedEdge.properties).map(([key, value]) => (
                                  <div key={key} className="flex gap-2 text-xs p-2 bg-muted/30 rounded">
                                    <span className="font-medium text-primary min-w-[100px]">{key}:</span>
                                    <span className="text-muted-foreground flex-1 break-all">
                                      {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </ScrollArea>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Usage Tips */}
      <div className="text-xs text-muted-foreground text-center">
        拖拽节点可调整位置 • 点击节点/边查看详情 • 滚动缩放 • 拖拽画布平移
      </div>

      {/* Entity Extract Panel Dialog */}
      {showEntityExtract && (
        <Dialog open={showEntityExtract} onOpenChange={setShowEntityExtract}>
          <DialogContent className="max-w-4xl">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5" />
                AI 智能本体抽取
              </DialogTitle>
              <DialogDescription>
                基于文档内容自动分析并推荐实体类型和关系类型
              </DialogDescription>
            </DialogHeader>
            <EntityExtractPanel onSuccess={() => {
              setShowEntityExtract(false)
            }} />
          </DialogContent>
        </Dialog>
      )}
    </div>
  )
}
