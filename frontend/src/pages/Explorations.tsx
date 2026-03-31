'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { intelligenceApi } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Textarea } from '@/components/ui/Textarea'
import {
  Map,
  Eye,
  Heart,
  Share2,
  Plus,
  Trash2,
  Edit,
  Save,
  Globe,
  Lock,
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { zhCN } from 'date-fns/locale'
import { useToast } from '@/contexts/ToastContext'

export function Explorations() {
  const [isCreating, setIsCreating] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newDescription, setNewDescription] = useState('')
  const queryClient = useQueryClient()

  const { data: explorations, isLoading } = useQuery({
    queryKey: ['explorations'],
    queryFn: () => intelligenceApi.getExplorations({ limit: 50 }).then(res => res.data),
  })

  const createMutation = useMutation({
    mutationFn: (data: { title: string; description: string; start_node_id: string; visited_nodes: string[] }) =>
      intelligenceApi.createExploration(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['explorations'] })
      setIsCreating(false)
      setNewTitle('')
      setNewDescription('')
    },
  })

  const handleCreate = () => {
    createMutation.mutate({
      title: newTitle,
      description: newDescription,
      start_node_id: 'mock-node-id',
      visited_nodes: [],
    })
  }

  const handleShare = async (id: string) => {
    const { toast } = useToast()
    try {
      const response = await fetch(`/api/v1/intelligence/explorations/${id}/share`, {
        method: 'POST',
      })
      const data = await response.json()
      await navigator.clipboard.writeText(`${window.location.origin}${data.share_url}`)
      toast({
        title: '分享成功',
        description: '分享链接已复制到剪贴板',
      })
    } catch (error) {
      console.error('Failed to share:', error)
      toast({
        title: '分享失败',
        description: '请稍后重试',
        variant: 'destructive',
      })
    }
  }

  const handleLike = async (id: string) => {
    try {
      await fetch(`/api/v1/intelligence/explorations/${id}/like`, { method: 'POST' })
      queryClient.invalidateQueries({ queryKey: ['explorations'] })
    } catch (error) {
      console.error('Failed to like:', error)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">探索路径</h1>
          <p className="text-muted-foreground mt-1">
            保存和分享您在知识图谱中的探索路径和发现
          </p>
        </div>
        <Button onClick={() => setIsCreating(true)}>
          <Plus className="h-4 w-4 mr-2" />
          保存当前路径
        </Button>
      </div>

      {/* 创建对话框 */}
      {isCreating && (
        <Card>
          <CardHeader>
            <CardTitle>保存探索路径</CardTitle>
            <CardDescription>为当前探索路径添加标题和描述</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">标题</label>
              <Input
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder="例如：从张三到 XX 公司的融资历程"
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">描述</label>
              <Textarea
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                placeholder="描述这条探索路径的内容和发现..."
              />
            </div>
            <div className="flex items-center gap-x-2">
              <Button onClick={handleCreate} disabled={!newTitle.trim()}>
                <Save className="h-4 w-4 mr-2" />
                保存
              </Button>
              <Button variant="outline" onClick={() => setIsCreating(false)}>
                取消
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <div className="text-center py-12">加载探索路径...</div>
      ) : explorations?.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Map className="h-16 w-16 text-muted-foreground mb-4" />
            <p className="text-lg font-medium">暂无探索路径</p>
            <p className="text-muted-foreground">开始浏览图谱并保存您的第一条探索路径</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {explorations?.map((exploration: any) => (
            <Card key={exploration.id} className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-x-2">
                    <Map className="h-5 w-5 text-primary" />
                    <CardTitle className="text-lg">{exploration.title}</CardTitle>
                  </div>
                  {exploration.is_public ? (
                    <Globe className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <Lock className="h-4 w-4 text-muted-foreground" />
                  )}
                </div>
                <CardDescription className="line-clamp-2">
                  {exploration.description || '无描述'}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-sm text-muted-foreground">
                    <span>访问节点：{exploration.visited_nodes?.length || 0}</span>
                    <span>高亮：{exploration.highlights?.length || 0}</span>
                  </div>
                  <div className="flex items-center justify-between pt-3 border-t">
                    <div className="flex items-center gap-x-3">
                      <button
                        className="flex items-center gap-x-1 text-sm text-muted-foreground hover:text-red-500 transition-colors"
                        onClick={() => handleLike(exploration.id)}
                      >
                        <Heart className="h-4 w-4" />
                        {exploration.likes || 0}
                      </button>
                      <span className="flex items-center gap-x-1 text-sm text-muted-foreground">
                        <Eye className="h-4 w-4" />
                        {exploration.view_count || 0}
                      </span>
                    </div>
                    <div className="flex items-center gap-x-1">
                      <Button variant="ghost" size="icon" onClick={() => handleShare(exploration.id)}>
                        <Share2 className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon">
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" className="text-destructive">
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    创建于 {formatDistanceToNow(new Date(exploration.created_at), { locale: zhCN, addSuffix: true })}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
