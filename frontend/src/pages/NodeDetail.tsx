'use client'

import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { assetApi } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { ArrowLeft, GitBranch, Calendar, User } from 'lucide-react'
import { Link } from 'react-router-dom'

export function NodeDetail() {
  const { nodeId } = useParams<{ nodeId: string }>()

  const { data, isLoading } = useQuery({
    queryKey: ['nodeDetail', nodeId],
    queryFn: () => assetApi.getDetail(nodeId!).then(res => res.data),
    enabled: !!nodeId,
  })

  if (isLoading) {
    return <div className="text-center py-12">加载中...</div>
  }

  if (!data) {
    return <div className="text-center py-12 text-muted-foreground">未找到节点</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-x-4">
        <Link to="/assets">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div>
          <h1 className="text-3xl font-bold">{data.name}</h1>
          <div className="flex items-center gap-x-2 mt-1">
            <Badge>{data.node_type}</Badge>
            {data.entity_type && <Badge variant="secondary">{data.entity_type}</Badge>}
            <Badge variant="outline">质量分：{(data.quality_score * 100).toFixed(0)}</Badge>
          </div>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">基本信息</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-x-2 text-sm">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <span className="text-muted-foreground">创建时间:</span>
              <span>{new Date(data.created_at).toLocaleString('zh-CN')}</span>
            </div>
            <div className="flex items-center gap-x-2 text-sm">
              <User className="h-4 w-4 text-muted-foreground" />
              <span className="text-muted-foreground">来源:</span>
              <span>{data.source}</span>
            </div>
            {data.description && (
              <div>
                <span className="text-sm text-muted-foreground">描述:</span>
                <p className="mt-1">{data.description}</p>
              </div>
            )}
            {data.tags?.length > 0 && (
              <div>
                <span className="text-sm text-muted-foreground">标签:</span>
                <div className="flex gap-x-2 mt-1 flex-wrap">
                  {data.tags.map((tag: string) => (
                    <Badge key={tag} variant="secondary">{tag}</Badge>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">关系统计</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">关系总数</span>
              <span className="text-lg font-semibold">{data.relation_count}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">传入关系</span>
              <span className="text-lg font-semibold">{data.incoming_relations?.length || 0}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">传出关系</span>
              <span className="text-lg font-semibold">{data.outgoing_relations?.length || 0}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">关联关系</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {data.outgoing_relations?.map((relation: any, index: number) => (
              <div key={index} className="flex items-center gap-x-4 p-3 bg-secondary/50 rounded-md">
                <GitBranch className="h-5 w-5 text-muted-foreground" />
                <span className="font-medium">{relation.relation_type}</span>
                <ArrowRight className="h-4 w-4 text-muted-foreground" />
                <div className="flex items-center gap-x-2">
                  <Badge variant="outline">{relation.other_node_type}</Badge>
                  <span>{relation.other_node_name}</span>
                </div>
              </div>
            ))}
            {data.incoming_relations?.map((relation: any, index: number) => (
              <div key={`in-${index}`} className="flex items-center gap-x-4 p-3 bg-secondary/50 rounded-md">
                <ArrowRight className="h-4 w-4 text-muted-foreground rotate-180" />
                <span className="font-medium">{relation.relation_type}</span>
                <ArrowRight className="h-4 w-4 text-muted-foreground" />
                <div className="flex items-center gap-x-2">
                  <Badge variant="outline">{relation.other_node_type}</Badge>
                  <span>{relation.other_node_name}</span>
                </div>
              </div>
            ))}
            {(!data.outgoing_relations?.length && !data.incoming_relations?.length) && (
              <div className="text-center py-6 text-muted-foreground">暂无关联关系</div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function ArrowRight({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
    </svg>
  )
}
