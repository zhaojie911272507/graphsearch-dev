'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import { Badge } from '@/components/ui/Badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import { Loader2, GitBranch, History, Clock } from 'lucide-react'
import { temporalApi } from '@/lib/api'

// Types
interface EntityVersion {
  entity_id: string
  version: number
  timestamp: string
  properties: Record<string, any>
  change_summary: string
}

interface RelationshipSnapshot {
  source_id: string
  target_id: string
  relation_type: string
  valid_from: string
  valid_to: string | null
  weight: number
}

interface TemporalQueryResult {
  query_type: string
  results: any[]
  metadata: Record<string, any>
}

interface EntitySummary {
  entity_id: string
  entity_name: string
  entity_type: string
  current_description: string
  version_count: number
  change_history: Array<{
    version: number
    timestamp: string
    summary: string
  }>
  importance_score: number
}

interface RelationshipSummary {
  source_id: string
  target_id: string
  relation_type: string
  duration_days: number
  snapshot_count: number
  strength_trend: string
  key_events: Array<{
    timestamp: string
    weight: number
  }>
}

export function TemporalQuery() {
  const [activeTab, setActiveTab] = useState('entity-history')

  // Entity History state
  const [entityId, setEntityId] = useState('')
  const [entityHistory, setEntityHistory] = useState<EntityVersion[]>([])
  const [entitySummary, setEntitySummary] = useState<EntitySummary | null>(null)
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const [historyError, setHistoryError] = useState('')

  // Relationship Timeline state
  const [sourceId, setSourceId] = useState('')
  const [targetId, setTargetId] = useState('')
  const [relationshipHistory, setRelationshipHistory] = useState<RelationshipSnapshot[]>([])
  const [relationshipSummary, setRelationshipSummary] = useState<RelationshipSummary | null>(null)
  const [isLoadingRelationship, setIsLoadingRelationship] = useState(false)
  const [relationshipError, setRelationshipError] = useState('')

  // Time Travel state
  const [timeTravelEntityId, setTimeTravelEntityId] = useState('')
  const [timestamp, setTimestamp] = useState('')
  const [timeTravelResult, setTimeTravelResult] = useState<any>(null)
  const [isLoadingTimeTravel, setIsLoadingTimeTravel] = useState(false)
  const [timeTravelError, setTimeTravelError] = useState('')

  // Query Entity History
  const handleQueryHistory = async () => {
    if (!entityId.trim()) return

    setIsLoadingHistory(true)
    setHistoryError('')
    setEntityHistory([])
    setEntitySummary(null)

    try {
      const response = await temporalApi.query({
        entity_id: entityId,
        query_type: 'history'
      })

      const data: TemporalQueryResult = response.data
      setEntityHistory(data.results)

      // Also get summary
      if (data.results.length > 0) {
        const firstResult = data.results[0]
        const summaryResponse = await temporalApi.getSummary({
          level: 'entity',
          entity_id: entityId,
          entity_name: firstResult.properties?.name || entityId,
          entity_type: firstResult.properties?.entity_type || 'OTHER'
        })
        setEntitySummary(summaryResponse.data.content)
      }
    } catch (err: any) {
      setHistoryError(err.response?.data?.detail || '查询失败')
    } finally {
      setIsLoadingHistory(false)
    }
  }

  // Query Relationship Timeline
  const handleQueryRelationship = async () => {
    if (!sourceId.trim() || !targetId.trim()) return

    setIsLoadingRelationship(true)
    setRelationshipError('')
    setRelationshipHistory([])
    setRelationshipSummary(null)

    try {
      const response = await temporalApi.query({
        source_id: sourceId,
        target_id: targetId,
        query_type: 'history'
      })

      const data: TemporalQueryResult = response.data
      setRelationshipHistory(data.results)

      // Get summary
      if (data.results.length > 0) {
        const summaryResponse = await temporalApi.getSummary({
          level: 'relationship',
          source_id: sourceId,
          target_id: targetId,
          source_name: sourceId,
          target_name: targetId,
          relation_type: data.results[0]?.relation_type || 'RELATED_TO'
        })
        setRelationshipSummary(summaryResponse.data.content)
      }
    } catch (err: any) {
      setRelationshipError(err.response?.data?.detail || '查询失败')
    } finally {
      setIsLoadingRelationship(false)
    }
  }

  // Time Travel Query
  const handleTimeTravel = async () => {
    if (!timeTravelEntityId.trim() || !timestamp) return

    setIsLoadingTimeTravel(true)
    setTimeTravelError('')
    setTimeTravelResult(null)

    try {
      const response = await temporalApi.query({
        entity_id: timeTravelEntityId,
        query_type: 'at_time',
        timestamp: new Date(timestamp).toISOString()
      })

      const data: TemporalQueryResult = response.data
      setTimeTravelResult(data.results[0] || null)
    } catch (err: any) {
      setTimeTravelError(err.response?.data?.detail || '查询失败')
    } finally {
      setIsLoadingTimeTravel(false)
    }
  }

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">时序知识图谱</h1>
        <p className="text-muted-foreground">查询实体和关系的历史演变</p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="entity-history" className="flex items-center gap-2">
            <History className="h-4 w-4" />
            实体历史
          </TabsTrigger>
          <TabsTrigger value="relationship-timeline" className="flex items-center gap-2">
            <GitBranch className="h-4 w-4" />
            关系演变
          </TabsTrigger>
          <TabsTrigger value="time-travel" className="flex items-center gap-2">
            <Clock className="h-4 w-4" />
            时间旅行
          </TabsTrigger>
        </TabsList>

        {/* Entity History Tab */}
        <TabsContent value="entity-history" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>查询实体历史</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-4">
                <div className="flex-1">
                  <Label htmlFor="entity-id">实体 ID</Label>
                  <Input
                    id="entity-id"
                    value={entityId}
                    onChange={(e) => setEntityId(e.target.value)}
                    placeholder="输入实体 ID"
                  />
                </div>
                <div className="flex items-end">
                  <Button
                    onClick={handleQueryHistory}
                    disabled={isLoadingHistory || !entityId.trim()}
                  >
                    {isLoadingHistory && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    查询
                  </Button>
                </div>
              </div>

              {historyError && (
                <div className="text-red-500 text-sm">{historyError}</div>
              )}

              {entityHistory.length > 0 && (
                <div className="space-y-4">
                  {/* Summary Card */}
                  {entitySummary && (
                    <Card className="bg-muted/50">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-lg">实体摘要</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <div className="text-sm text-muted-foreground">实体名称</div>
                            <div className="font-medium">{entitySummary.entity_name}</div>
                          </div>
                          <div>
                            <div className="text-sm text-muted-foreground">实体类型</div>
                            <div className="font-medium">{entitySummary.entity_type}</div>
                          </div>
                          <div>
                            <div className="text-sm text-muted-foreground">版本数量</div>
                            <div className="font-medium">{entitySummary.version_count}</div>
                          </div>
                          <div>
                            <div className="text-sm text-muted-foreground">重要性评分</div>
                            <div className="font-medium">
                              {(entitySummary.importance_score * 100).toFixed(1)}%
                            </div>
                          </div>
                        </div>
                        {entitySummary.current_description && (
                          <div className="mt-4">
                            <div className="text-sm text-muted-foreground">当前描述</div>
                            <div>{entitySummary.current_description}</div>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  )}

                  {/* Version List */}
                  <div className="space-y-2">
                    <h3 className="font-semibold">版本历史</h3>
                    {entityHistory.map((version: any, index: number) => (
                      <Card key={index}>
                        <CardContent className="py-4">
                          <div className="flex justify-between items-start">
                            <div>
                              <div className="flex items-center gap-2">
                                <Badge variant="outline">v{version.version}</Badge>
                                <span className="text-sm text-muted-foreground">
                                  {new Date(version.timestamp).toLocaleString()}
                                </span>
                              </div>
                              {version.change_summary && (
                                <div className="mt-2 text-sm">{version.change_summary}</div>
                              )}
                              {version.properties && (
                                <div className="mt-2 text-sm text-muted-foreground">
                                  {version.properties.name} - {version.properties.description}
                                </div>
                              )}
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Relationship Timeline Tab */}
        <TabsContent value="relationship-timeline" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>查询关系演变</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="source-id">源实体 ID</Label>
                  <Input
                    id="source-id"
                    value={sourceId}
                    onChange={(e) => setSourceId(e.target.value)}
                    placeholder="输入源实体 ID"
                  />
                </div>
                <div>
                  <Label htmlFor="target-id">目标实体 ID</Label>
                  <Input
                    id="target-id"
                    value={targetId}
                    onChange={(e) => setTargetId(e.target.value)}
                    placeholder="输入目标实体 ID"
                  />
                </div>
              </div>

              <Button
                onClick={handleQueryRelationship}
                disabled={isLoadingRelationship || !sourceId.trim() || !targetId.trim()}
              >
                {isLoadingRelationship && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                查询
              </Button>

              {relationshipError && (
                <div className="text-red-500 text-sm">{relationshipError}</div>
              )}

              {relationshipHistory.length > 0 && (
                <div className="space-y-4">
                  {/* Summary */}
                  {relationshipSummary && (
                    <Card className="bg-muted/50">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-lg">关系摘要</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <div className="text-sm text-muted-foreground">关系类型</div>
                            <div className="font-medium">{relationshipSummary.relation_type}</div>
                          </div>
                          <div>
                            <div className="text-sm text-muted-foreground">持续天数</div>
                            <div className="font-medium">{relationshipSummary.duration_days} 天</div>
                          </div>
                          <div>
                            <div className="text-sm text-muted-foreground">快照数量</div>
                            <div className="font-medium">{relationshipSummary.snapshot_count}</div>
                          </div>
                          <div>
                            <div className="text-sm text-muted-foreground">强度趋势</div>
                            <Badge variant={
                              relationshipSummary.strength_trend === 'rising' ? 'default' :
                              relationshipSummary.strength_trend === 'declining' ? 'destructive' :
                              'secondary'
                            }>
                              {relationshipSummary.strength_trend === 'rising' ? '上升 ↑' :
                               relationshipSummary.strength_trend === 'declining' ? '下降 ↓' : '稳定 →'}
                            </Badge>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {/* Timeline */}
                  <div className="space-y-2">
                    <h3 className="font-semibold">关系演变时间线</h3>
                    {relationshipHistory.map((snapshot: any, index: number) => (
                      <Card key={index}>
                        <CardContent className="py-4">
                          <div className="flex items-center gap-4">
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <Badge>{snapshot.relation_type}</Badge>
                                <span className="text-sm text-muted-foreground">
                                  {new Date(snapshot.valid_from).toLocaleString()}
                                </span>
                                {snapshot.valid_to && (
                                  <span className="text-sm text-muted-foreground">
                                    → {new Date(snapshot.valid_to).toLocaleString()}
                                  </span>
                                )}
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="text-sm text-muted-foreground">权重</div>
                              <div className="font-medium">{(snapshot.weight * 100).toFixed(0)}%</div>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Time Travel Tab */}
        <TabsContent value="time-travel" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>时间旅行查询</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="time-travel-entity">实体 ID</Label>
                  <Input
                    id="time-travel-entity"
                    value={timeTravelEntityId}
                    onChange={(e) => setTimeTravelEntityId(e.target.value)}
                    placeholder="输入实体 ID"
                  />
                </div>
                <div>
                  <Label htmlFor="timestamp">时间点</Label>
                  <Input
                    id="timestamp"
                    type="datetime-local"
                    value={timestamp}
                    onChange={(e) => setTimestamp(e.target.value)}
                  />
                </div>
              </div>

              <Button
                onClick={handleTimeTravel}
                disabled={isLoadingTimeTravel || !timeTravelEntityId.trim() || !timestamp}
              >
                {isLoadingTimeTravel && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                查询历史状态
              </Button>

              {timeTravelError && (
                <div className="text-red-500 text-sm">{timeTravelError}</div>
              )}

              {timeTravelResult && (
                <Card className="bg-muted/50">
                  <CardHeader>
                    <CardTitle className="text-lg">
                      {new Date(timeTravelResult.timestamp).toLocaleString()} 时的实体状态
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <div>
                        <span className="text-muted-foreground">版本：</span>
                        <span className="font-medium">{timeTravelResult.version}</span>
                      </div>
                      {timeTravelResult.properties && (
                        <div>
                          <div className="text-muted-foreground">属性：</div>
                          <pre className="mt-2 p-2 bg-background rounded text-sm overflow-auto">
                            {JSON.stringify(timeTravelResult.properties, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}