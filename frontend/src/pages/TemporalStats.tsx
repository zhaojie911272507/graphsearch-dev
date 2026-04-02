'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Loader2, RefreshCw, Database, Clock, Activity } from 'lucide-react'
import { temporalApi } from '@/lib/api'

interface TemporalStatus {
  running: boolean
  pending_count: number
  last_merge_time: string | null
  interval_minutes: number
}

interface GlobalSummary {
  total_entities: number
  total_versions: number
  total_snapshots: number
  top_entities: Array<{
    entity_id: string
    name: string
    version_count: number
  }>
  entity_trend: {
    added: number
    modified: number
  }
  relationship_density: number
}

export function TemporalStats() {
  const [isLoading, setIsLoading] = useState(true)
  const [status, setStatus] = useState<TemporalStatus | null>(null)
  const [summary, setSummary] = useState<GlobalSummary | null>(null)
  const [error, setError] = useState('')

  const fetchData = async () => {
    setIsLoading(true)
    setError('')

    try {
      const [statusRes, summaryRes] = await Promise.all([
        temporalApi.getStatus(),
        temporalApi.getSummary({ level: 'global' })
      ])

      setStatus(statusRes.data)
      setSummary(summaryRes.data.content)
    } catch (err: any) {
      setError(err.response?.data?.detail || '获取数据失败')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  if (isLoading && !summary) {
    return (
      <div className="container mx-auto p-6 flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold">时序统计</h1>
          <p className="text-muted-foreground">全局时序知识图谱统计信息</p>
        </div>
        <Button onClick={fetchData} disabled={isLoading}>
          {isLoading ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="mr-2 h-4 w-4" />
          )}
          刷新
        </Button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-600 rounded-lg">{error}</div>
      )}

      {/* Status Card */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-lg">服务状态</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${status?.running ? 'bg-green-100' : 'bg-gray-100'}`}>
                <Activity className={`h-5 w-5 ${status?.running ? 'text-green-600' : 'text-gray-500'}`} />
              </div>
              <div>
                <div className="text-sm text-muted-foreground">运行状态</div>
                <div className="font-medium">
                  {status?.running ? '运行中' : '已停止'}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-100">
                <Clock className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <div className="text-sm text-muted-foreground">合并间隔</div>
                <div className="font-medium">{status?.interval_minutes || 5} 分钟</div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-yellow-100">
                <Database className="h-5 w-5 text-yellow-600" />
              </div>
              <div>
                <div className="text-sm text-muted-foreground">待处理队列</div>
                <div className="font-medium">{status?.pending_count || 0} 项</div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-purple-100">
                <Clock className="h-5 w-5 text-purple-600" />
              </div>
              <div>
                <div className="text-sm text-muted-foreground">上次合并</div>
                <div className="font-medium">
                  {status?.last_merge_time
                    ? new Date(status.last_merge_time).toLocaleString()
                    : '从未'}
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              总实体数
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{summary?.total_entities || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              总版本数
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{summary?.total_versions || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              总快照数
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{summary?.total_snapshots || 0}</div>
          </CardContent>
        </Card>
      </div>

      {/* Top Entities */}
      <Card>
        <CardHeader>
          <CardTitle>热点实体 (Top 10)</CardTitle>
        </CardHeader>
        <CardContent>
          {summary?.top_entities && summary.top_entities.length > 0 ? (
            <div className="space-y-2">
              {summary.top_entities.map((entity, index) => (
                <div
                  key={entity.entity_id}
                  className="flex items-center justify-between p-3 bg-muted/50 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <Badge variant="outline">{index + 1}</Badge>
                    <div>
                      <div className="font-medium">{entity.name || entity.entity_id}</div>
                      <div className="text-sm text-muted-foreground">{entity.entity_id}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm text-muted-foreground">版本数</div>
                    <div className="font-medium">{entity.version_count}</div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center text-muted-foreground py-8">
              暂无热点实体数据
            </div>
          )}
        </CardContent>
      </Card>

      {/* Trend Info */}
      <div className="grid grid-cols-2 gap-4 mt-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              实体趋势
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-sm text-muted-foreground">新增</div>
                <div className="text-2xl font-bold text-green-600">
                  +{summary?.entity_trend?.added || 0}
                </div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">修改</div>
                <div className="text-2xl font-bold text-blue-600">
                  ~{summary?.entity_trend?.modified || 0}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              关系密度
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {((summary?.relationship_density || 0) * 100).toFixed(1)}%
            </div>
            <div className="text-sm text-muted-foreground">
              活跃关系占比
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}