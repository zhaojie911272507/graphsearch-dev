'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { intelligenceApi } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import { Textarea } from '@/components/ui/Textarea'
import { CheckCircle2, XCircle, Edit2, AlertCircle } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { zhCN } from 'date-fns/locale'

export function ReviewQueue() {
  const [selectedTab, setSelectedTab] = useState('pending')
  const [voteComment, setVoteComment] = useState('')
  const [selectedItem, setSelectedItem] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const { data: queueItems, isLoading } = useQuery({
    queryKey: ['reviewQueue', selectedTab],
    queryFn: () => intelligenceApi.getReviewQueue({ status_filter: selectedTab, limit: 50 })
      .then(res => res.data),
  })

  const voteMutation = useMutation({
    mutationFn: ({ itemId, voteType, comment }: { itemId: string; voteType: string; comment: string }) =>
      intelligenceApi.voteReview(itemId, { vote_type: voteType, comment }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reviewQueue'] })
      setSelectedItem(null)
      setVoteComment('')
    },
  })

  const handleVote = (itemId: string, voteType: string) => {
    voteMutation.mutate({ itemId, voteType, comment: voteComment })
  }

  const getPriorityColor = (priority: number) => {
    if (priority >= 0.8) return 'bg-red-500'
    if (priority >= 0.5) return 'bg-yellow-500'
    return 'bg-green-500'
  }

  const getStatusBadge = (status: string) => {
    const badges = {
      PENDING: <Badge variant="secondary">待审核</Badge>,
      REVIEWED: <Badge variant="default">已审核</Badge>,
      ESCALATED: <Badge variant="destructive">需仲裁</Badge>,
    }
    return badges[status as keyof typeof badges] || <Badge>{status}</Badge>
  }

  if (isLoading) {
    return <div className="text-center py-12">加载审核队列...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">协作审核</h1>
          <p className="text-muted-foreground mt-1">
            对自动提取的实体和关系进行人工审核，确保知识图谱质量
          </p>
        </div>
        <div className="flex items-center gap-x-2">
          <Card className="p-3">
            <div className="text-2xl font-bold">{queueItems?.length || 0}</div>
            <div className="text-xs text-muted-foreground">待审核项</div>
          </Card>
        </div>
      </div>

      <Tabs value={selectedTab} onValueChange={setSelectedTab}>
        <TabsList>
          <TabsTrigger value="pending">待审核 (Pending)</TabsTrigger>
          <TabsTrigger value="reviewed">已审核 (Reviewed)</TabsTrigger>
          <TabsTrigger value="escalated">需仲裁 (Escalated)</TabsTrigger>
        </TabsList>

        <TabsContent value={selectedTab} className="space-y-4">
          {queueItems?.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <CheckCircle2 className="h-16 w-16 text-green-500 mb-4" />
                <p className="text-lg font-medium">暂无审核项</p>
                <p className="text-muted-foreground">所有提取项都已审核完成</p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4">
              {queueItems?.map((item: any) => (
                <Card key={item.id} className={selectedItem === item.id ? 'ring-2 ring-primary' : ''}>
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-x-3">
                        <div className={`h-3 w-3 rounded-full ${getPriorityColor(item.priority)}`} />
                        <div>
                          <CardTitle className="text-lg flex items-center gap-x-2">
                            {item.node_name}
                            <Badge variant="outline">{item.node_type}</Badge>
                          </CardTitle>
                          <CardDescription className="flex items-center gap-x-2 mt-1">
                            {getStatusBadge(item.status)}
                            <span className="text-xs">
                              置信度：{(item.auto_confidence * 100).toFixed(0)}%
                            </span>
                            <span className="text-xs">
                              {formatDistanceToNow(new Date(item.created_at), { locale: zhCN, addSuffix: true })}
                            </span>
                          </CardDescription>
                        </div>
                      </div>
                      <Button
                        variant={selectedItem === item.id ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setSelectedItem(selectedItem === item.id ? null : item.id)}
                      >
                        {selectedItem === item.id ? '收起' : '审核'}
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      <div className="flex items-center gap-x-2 text-sm">
                        <AlertCircle className="h-4 w-4 text-muted-foreground" />
                        <span className="text-muted-foreground">审核原因:</span>
                        <span>{item.reason}</span>
                      </div>
                      <div className="bg-secondary/50 rounded-md p-3">
                        <div className="text-xs text-muted-foreground mb-1">来源文档</div>
                        <div className="font-medium">{item.source_document}</div>
                      </div>
                      <div className="bg-secondary/50 rounded-md p-3">
                        <div className="text-xs text-muted-foreground mb-1">原始文本</div>
                        <div className="text-sm">{item.original_text}</div>
                      </div>

                      {/* 投票统计 */}
                      <div className="flex items-center gap-x-4 pt-3 border-t">
                        <div className="flex items-center gap-x-1 text-sm">
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                          <span>{item.approve_count}</span>
                        </div>
                        <div className="flex items-center gap-x-1 text-sm">
                          <XCircle className="h-4 w-4 text-red-500" />
                          <span>{item.reject_count}</span>
                        </div>
                        <div className="flex items-center gap-x-1 text-sm">
                          <Edit2 className="h-4 w-4 text-yellow-500" />
                          <span>{item.modify_count}</span>
                        </div>
                        <div className="text-sm text-muted-foreground">
                          总投票：{item.vote_count}
                        </div>
                      </div>

                      {/* 审核操作区 */}
                      {selectedItem === item.id && (
                        <div className="space-y-3 pt-3 border-t">
                          <Textarea
                            placeholder="输入审核意见（可选）..."
                            value={voteComment}
                            onChange={(e) => setVoteComment(e.target.value)}
                            className="min-h-[80px]"
                          />
                          <div className="flex items-center gap-x-2">
                            <Button
                              className="flex-1 bg-green-600 hover:bg-green-700"
                              onClick={() => handleVote(item.id, 'APPROVE')}
                              disabled={voteMutation.isPending}
                            >
                              <CheckCircle2 className="h-4 w-4 mr-2" />
                              通过
                            </Button>
                            <Button
                              variant="destructive"
                              className="flex-1"
                              onClick={() => handleVote(item.id, 'REJECT')}
                              disabled={voteMutation.isPending}
                            >
                              <XCircle className="h-4 w-4 mr-2" />
                              拒绝
                            </Button>
                            <Button
                              variant="secondary"
                              className="flex-1"
                              onClick={() => handleVote(item.id, 'MODIFY')}
                              disabled={voteMutation.isPending}
                            >
                              <Edit2 className="h-4 w-4 mr-2" />
                              修改建议
                            </Button>
                          </div>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
