import { useEffect, useState } from 'react'
import cytoscape from 'cytoscape'
import { useQuery } from '@tanstack/react-query'
import { graphVizApi } from '@/lib/api'
import { Card, CardContent } from '@/components/ui/Card'

interface GraphVizData {
  nodes: Array<{
    id: string
    label: string
    type: string
    name: string
    quality_score?: number
  }>
  edges: Array<{
    source: string
    target: string
    label: string
    weight?: number
  }>
}

export function GraphViz() {
  const [cy, setCy] = useState<cytoscape.Core | null>(null)
  const [container, setContainer] = useState<HTMLDivElement | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['graphViz'],
    queryFn: () => graphVizApi.getGraph({ limit: 100 }).then(res => res.data),
  })

  useEffect(() => {
    if (!container) return

    const cyInstance = cytoscape({
      container,
      elements: [],
      style: [
        {
          selector: 'node',
          style: {
            'background-color': '#1f2937',
            'label': 'data(label)',
            'text-valign': 'center',
            'text-halign': 'center',
            'color': '#f3f4f6',
            'font-size': '10px',
            'width': '40px',
            'height': '40px',
            'border-width': '2px',
            'border-color': '#374151',
          },
        },
        {
          selector: 'node[type="Document"]',
          style: {
            'shape': 'rectangle',
            'background-color': '#3b82f6',
            'border-color': '#2563eb',
          },
        },
        {
          selector: 'node[type="Entity"]',
          style: {
            'shape': 'ellipse',
            'background-color': '#10b981',
            'border-color': '#059669',
          },
        },
        {
          selector: 'node[type="Concept"]',
          style: {
            'shape': 'diamond',
            'background-color': '#8b5cf6',
            'border-color': '#7c3aed',
          },
        },
        {
          selector: 'node[type="Chunk"]',
          style: {
            'shape': 'circle',
            'background-color': '#6b7280',
            'border-color': '#4b5563',
          },
        },
        {
          selector: 'edge',
          style: {
            'width': '2px',
            'line-color': '#9ca3af',
            'target-arrow-shape': 'triangle',
            'target-arrow-color': '#9ca3af',
            'curve-style': 'bezier',
            'label': 'data(label)',
            'text-background-color': '#1f2937',
            'text-background-opacity': '0.8',
            'text-background-shape': 'rectangle',
            'color': '#f3f4f6',
            'font-size': '8px',
          },
        },
        {
          selector: 'edge[weight > 0.8]',
          style: {
            'line-color': '#10b981',
            'target-arrow-color': '#10b981',
            'width': '3px',
          },
        },
        {
          selector: ':selected',
          style: {
            'background-color': '#fbbf24',
            'line-color': '#fbbf24',
            'target-arrow-color': '#fbbf24',
            'border-color': '#f59e0b',
          },
        },
      ],
      layout: {
        name: 'cose',
        fit: true,
        padding: 30,
        randomize: false,
        animate: true,
        animationDuration: 1000,
      },
      userZoomingEnabled: true,
      userPanningEnabled: true,
      boxSelectionEnabled: true,
      selectionType: 'single',
    })

    setCy(cyInstance)

    return () => {
      cyInstance.destroy()
    }
  }, [container])

  useEffect(() => {
    if (!cy || !data) return

    // Clear existing elements
    cy.elements().remove()

    // Add nodes
    const nodes = (data.nodes || []).map((node: any) => ({
      data: {
        id: node.id,
        label: node.name.length > 15 ? node.name.substring(0, 12) + '...' : node.name,
        type: node.type,
      },
    }))

    // Add edges
    const edges = (data.edges || []).map((edge: any) => ({
      data: {
        source: edge.source,
        target: edge.target,
        label: edge.label,
        weight: edge.weight || 0,
      },
    }))

    cy.add([...nodes, ...edges])
    cy.layout({ name: 'cose', animate: true }).run()
    cy.fit(undefined, 50)
  }, [cy, data])

  if (isLoading) {
    return <div className="text-center py-12">加载图谱数据...</div>
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">图谱可视化</h1>
        <p className="text-muted-foreground mt-1">
          交互式知识图谱可视化，探索节点和关系
        </p>
      </div>

      <Card>
        <CardContent className="p-0 h-[700px]">
          <div
            ref={setContainer}
            className="w-full h-full"
            style={{ minHeight: '700px' }}
          />
        </CardContent>
      </Card>
    </div>
  )
}
