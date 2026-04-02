'use client'

import { useState, useRef, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import { Slider } from '@/components/ui/Slider'
import { ScrollArea } from '@/components/ui/ScrollArea'
import { Badge } from '@/components/ui/Badge'
import { Loader2, Send, Sparkles, FileText, GitBranch, Layers, Clock } from 'lucide-react'

interface RetrievedChunk {
  chunk_id: string
  content: string
  score: number
  document_title: string
  chunk_index: number
}

interface RetrievedEntity {
  name: string
  entity_type: string
  count: number
}

interface RetrievedRelation {
  source_name: string
  target_name: string
  relation_type: string
}

interface RetrievalContext {
  chunks: RetrievedChunk[]
  entities: RetrievedEntity[]
  relations: RetrievedRelation[]
}

interface QueryResult {
  answer: string
  context?: RetrievalContext
  model?: string
  latency_ms?: number
}

export function GraphQuery() {
  const [question, setQuestion] = useState('')
  const [topK, setTopK] = useState(10)
  const [traversalDepth, setTraversalDepth] = useState(2)
  const [isLoading, setIsLoading] = useState(false)
  const [answer, setAnswer] = useState('')
  const [context, setContext] = useState<RetrievalContext | null>(null)
  const [latency, setLatency] = useState<number | null>(null)
  const [model, setModel] = useState('')
  const [error, setError] = useState('')
  const [showSettings, setShowSettings] = useState(false)

  const answerRef = useRef<HTMLDivElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [])

  // Auto-scroll to answer
  useEffect(() => {
    if (answerRef.current) {
      answerRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [answer])

  const handleQuery = async () => {
    if (!question.trim()) return

    // Reset state
    setAnswer('')
    setContext(null)
    setLatency(null)
    setModel('')
    setError('')
    setIsLoading(true)

    try {
      const response = await fetch('/api/v1/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
        },
        body: JSON.stringify({
          question: question.trim(),
          top_k: topK,
          traversal_depth: traversalDepth,
          include_sources: true,
        }),
      })

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}))
        throw new Error(errData.detail || `Request failed: ${response.status}`)
      }

      const contentType = response.headers.get('content-type') || ''

      if (contentType.includes('text/event-stream')) {
        // Streaming response
        const reader = response.body?.getReader()
        if (!reader) throw new Error('No response body')

        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const event = JSON.parse(line.slice(6))

                if (event.type === 'context') {
                  setContext(event.data)
                } else if (event.type === 'token') {
                  setAnswer(prev => prev + event.data)
                } else if (event.type === 'done') {
                  setLatency(event.data.latency_ms)
                  setModel(event.data.model)
                }
              } catch {
                // Ignore parse errors for incomplete events
              }
            }
          }
        }
      } else {
        // Non-streaming response (fallback)
        const data: QueryResult = await response.json()
        setAnswer(data.answer)
        setContext(data.context || null)
        setLatency(data.latency_ms || null)
        setModel(data.model || '')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleQuery()
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Sparkles className="h-8 w-8 text-primary" />
            图谱问答
          </h1>
          <p className="text-muted-foreground mt-1">
            基于知识图谱的混合检索问答系统
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowSettings(!showSettings)}
        >
          {showSettings ? '隐藏设置' : '显示设置'}
        </Button>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="text-base">检索参数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-3">
                <Label className="flex justify-between">
                  <span>Top-K (检索文本块数量)</span>
                  <Badge variant="secondary">{topK}</Badge>
                </Label>
                <Slider
                  value={[topK]}
                  onValueChange={([v]) => setTopK(v)}
                  min={1}
                  max={50}
                  step={1}
                />
              </div>
              <div className="space-y-3">
                <Label className="flex justify-between">
                  <span>图遍历深度</span>
                  <Badge variant="secondary">{traversalDepth}</Badge>
                </Label>
                <Slider
                  value={[traversalDepth]}
                  onValueChange={([v]) => setTraversalDepth(v)}
                  min={1}
                  max={5}
                  step={1}
                />
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Query Input */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-3">
            <Input
              placeholder="输入您的问题，例如：什么是Graph RAG？它如何工作？"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={handleKeyDown}
              className="flex-1 text-lg"
              disabled={isLoading}
            />
            <Button
              onClick={handleQuery}
              disabled={isLoading || !question.trim()}
              size="lg"
              className="gap-2"
            >
              {isLoading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Send className="h-5 w-5" />
              )}
              提问
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Error Display */}
      {error && (
        <Card className="border-destructive/50 bg-destructive/5">
          <CardContent className="pt-4">
            <p className="text-destructive">错误: {error}</p>
          </CardContent>
        </Card>
      )}

      {/* Loading State */}
      {isLoading && !answer && (
        <Card>
          <CardContent className="flex items-center justify-center py-12">
            <div className="text-center space-y-3">
              <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
              <p className="text-muted-foreground">正在检索知识图谱并生成答案...</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Answer Display */}
      {(answer || isLoading) && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              回答
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div ref={answerRef} className="prose prose-sm max-w-none whitespace-pre-wrap">
              {answer}
              {isLoading && (
                <span className="inline-flex ml-1">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                </span>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Context/Chunks Display */}
      {context && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Retrieved Chunks */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <FileText className="h-5 w-5" />
                检索到的文本块 ({context.chunks.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px]">
                <div className="space-y-4">
                  {context.chunks.map((chunk) => (
                    <div
                      key={chunk.chunk_id}
                      className="p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <Badge variant="outline">
                          Chunk {chunk.chunk_index}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          相似度: {(chunk.score * 100).toFixed(1)}%
                        </span>
                      </div>
                      <p className="text-sm line-clamp-4">{chunk.content}</p>
                      {chunk.document_title && (
                        <p className="text-xs text-muted-foreground mt-2">
                          来源: {chunk.document_title}
                        </p>
                      )}
                    </div>
                  ))}
                  {context.chunks.length === 0 && (
                    <p className="text-muted-foreground text-sm">未检索到相关文本</p>
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>

          {/* Entities and Relations */}
          <div className="space-y-6">
            {/* Entities */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Layers className="h-5 w-5" />
                  检索到的实体 ({context.entities.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[180px]">
                  <div className="flex flex-wrap gap-2">
                    {context.entities.map((entity, idx) => (
                      <Badge key={idx} variant="secondary" className="text-sm py-1">
                        {entity.name}
                        <span className="ml-1 text-xs text-muted-foreground">
                          ({entity.entity_type})
                        </span>
                      </Badge>
                    ))}
                    {context.entities.length === 0 && (
                      <p className="text-muted-foreground text-sm">未检索到实体</p>
                    )}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>

            {/* Relations */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <GitBranch className="h-5 w-5" />
                  图关系 ({context.relations.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[180px]">
                  <div className="space-y-2">
                    {context.relations.map((rel, idx) => (
                      <div
                        key={idx}
                        className="flex items-center gap-2 text-sm p-2 rounded bg-accent/50"
                      >
                        <span className="font-medium">{rel.source_name}</span>
                        <span className="text-muted-foreground">--[{rel.relation_type}]--&gt;</span>
                        <span className="font-medium">{rel.target_name}</span>
                      </div>
                    ))}
                    {context.relations.length === 0 && (
                      <p className="text-muted-foreground text-sm">未检索到关系</p>
                    )}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* Performance Stats */}
      {(latency !== null || model) && (
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          {latency !== null && (
            <div className="flex items-center gap-1">
              <Clock className="h-4 w-4" />
              <span>响应时间: {latency.toFixed(0)}ms</span>
            </div>
          )}
          {model && (
            <div className="flex items-center gap-1">
              <Sparkles className="h-4 w-4" />
              <span>模型: {model}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}