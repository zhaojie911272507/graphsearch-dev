'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ontologyApi } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/Dialog'
import { ScrollArea } from '@/components/ui/ScrollArea'
import { useToast } from '@/contexts/ToastContext'
import {
  GitBranch,
  Tag,
  Sparkles,
  RotateCw,
  Check,
  X,
  Brain,
  ArrowRight,
} from 'lucide-react'

interface EntityType {
  name: string
  description: string
  color: string
  icon: string
  is_builtin: boolean
  instance_count: number
}

interface RelationType {
  name: string
  description: string
  source_types: string[]
  target_types: string[]
  is_builtin: boolean
  instance_count: number
}

interface Recommendation {
  entity_types: Array<{
    name: string
    description: string
    color: string
    icon: string
    extraction_prompt_template: string
    example_instances?: string[]
  }>
  relation_types: Array<{
    name: string
    description: string
    source_types: string[]
    target_types: string[]
    directionality: string
    extraction_prompt?: string
  }>
}

export function OntologyManager() {
  const [activeTab, setActiveTab] = useState('entity-types')
  const [showApplyDialog, setShowApplyDialog] = useState(false)
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null)
  const [selectedEntityTypes, setSelectedEntityTypes] = useState<Set<string>>(new Set())
  const [selectedRelationTypes, setSelectedRelationTypes] = useState<Set<string>>(new Set())

  const queryClient = useQueryClient()
  const { toast } = useToast()

  const { data: entityTypes, isLoading: entityTypesLoading, refetch } = useQuery({
    queryKey: ['entityTypes'],
    queryFn: () => ontologyApi.getEntityTypes(true, true).then(res => res.data),
  })

  const { data: relationTypes, isLoading: relationTypesLoading } = useQuery({
    queryKey: ['relationTypes'],
    queryFn: () => ontologyApi.getRelationTypes(true, true).then(res => res.data),
  })

  // AI Recommendation mutation
  const recommendMutation = useMutation({
    mutationFn: (data?: any) => ontologyApi.getRecommendations(data),
    onSuccess: (response) => {
      if (response.data.success) {
        setRecommendation(response.data.recommendations)
        setShowApplyDialog(true)
        // Pre-select all recommendations
        setSelectedEntityTypes(new Set(response.data.recommendations.entity_types.map((t: any) => t.name)))
        setSelectedRelationTypes(new Set(response.data.recommendations.relation_types.map((t: any) => t.name)))
      } else {
        toast({
          title: '分析失败',
          description: response.data.message || '无法获取推荐',
          variant: 'destructive',
        })
      }
    },
    onError: () => {
      toast({
        title: '分析失败',
        description: '无法连接到 AI 服务，请检查配置',
        variant: 'destructive',
      })
    },
  })

  // Apply recommendations mutation
  const applyMutation = useMutation({
    mutationFn: (data: { entity_types: any[]; relation_types: any[] }) =>
      ontologyApi.applyRecommendations(data),
    onSuccess: (response) => {
      if (response.data.success) {
        toast({
          title: '导入成功',
          description: `已创建 ${response.data.created.entity_types.length} 个实体类型和 ${response.data.created.relation_types.length} 个关系类型`,
        })
        queryClient.invalidateQueries({ queryKey: ['entityTypes'] })
        queryClient.invalidateQueries({ queryKey: ['relationTypes'] })
        setShowApplyDialog(false)
        setRecommendation(null)
        refetch()
      }
    },
    onError: () => {
      toast({
        title: '导入失败',
        description: '部分类型可能已存在或发生错误',
        variant: 'destructive',
      })
    },
  })

  const handleStartAnalysis = () => {
    recommendMutation.mutate({
      max_entity_types: 10,
      max_relation_types: 8,
    })
  }

  const handleApplySelected = () => {
    if (!recommendation) return

    const entityTypesToApply = recommendation.entity_types.filter((t: any) => selectedEntityTypes.has(t.name))
    const relationTypesToApply = recommendation.relation_types.filter((t: any) => selectedRelationTypes.has(t.name))

    applyMutation.mutate({
      entity_types: entityTypesToApply,
      relation_types: relationTypesToApply,
    })
  }

  const toggleEntityType = (name: string) => {
    setSelectedEntityTypes(prev => {
      const next = new Set(prev)
      if (next.has(name)) {
        next.delete(name)
      } else {
        next.add(name)
      }
      return next
    })
  }

  const toggleRelationType = (name: string) => {
    setSelectedRelationTypes(prev => {
      const next = new Set(prev)
      if (next.has(name)) {
        next.delete(name)
      } else {
        next.add(name)
      }
      return next
    })
  }

  const hasEntityTypes = entityTypes && entityTypes.length > 0
  const hasRelationTypes = relationTypes && relationTypes.length > 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">本体管理</h1>
          <p className="text-muted-foreground mt-1">
            管理实体类型和关系类型的定义，构建领域知识 Schema
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            onClick={handleStartAnalysis}
            disabled={recommendMutation.isPending}
            className="gap-2"
          >
            <Sparkles className="h-4 w-4" />
            {recommendMutation.isPending ? '分析中...' : 'AI 智能推荐'}
          </Button>
          <Button
            variant="outline"
            onClick={() => refetch()}
            disabled={entityTypesLoading || relationTypesLoading}
          >
            <RotateCw className={`h-4 w-4 mr-2 ${entityTypesLoading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <div className="flex items-center justify-between">
          <TabsList>
            <TabsTrigger value="entity-types">实体类型</TabsTrigger>
            <TabsTrigger value="relation-types">关系类型</TabsTrigger>
            <TabsTrigger value="versions">版本历史</TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="entity-types" className="space-y-4">
          {!hasEntityTypes ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Brain className="h-16 w-16 text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold mb-2">暂无实体类型</h3>
                <p className="text-muted-foreground text-center mb-4">
                  内置本体类型已在启动时自动加载<br/>
                  或使用 AI 智能推荐发现更多领域特定的实体类型
                </p>
                <Button onClick={handleStartAnalysis} disabled={recommendMutation.isPending}>
                  <Sparkles className="h-4 w-4 mr-2" />
                  {recommendMutation.isPending ? '分析文档中...' : '开始 AI 分析'}
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {entityTypes?.map((type: EntityType) => (
                <Card key={type.name}>
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-x-2">
                        <div
                          className="h-3 w-3 rounded-full"
                          style={{ backgroundColor: type.color }}
                        />
                        <CardTitle className="text-lg">{type.name}</CardTitle>
                      </div>
                      {type.is_builtin && (
                        <Badge variant="secondary">内置</Badge>
                      )}
                    </div>
                    <CardDescription>{type.description}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">实例数量</span>
                        <span className="font-medium">{type.instance_count}</span>
                      </div>
                      <div className="flex items-center gap-x-2">
                        <Button variant="outline" size="sm" disabled={type.is_builtin}>
                          <Tag className="h-3 w-3 mr-1" />
                          编辑
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="text-destructive"
                          disabled={type.is_builtin}
                        >
                          <GitBranch className="h-3 w-3 mr-1" />
                          删除
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="relation-types" className="space-y-4">
          {!hasRelationTypes ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <GitBranch className="h-16 w-16 text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold mb-2">暂无关系类型</h3>
                <p className="text-muted-foreground text-center mb-4">
                  内置关系类型已在启动时自动加载<br/>
                  或使用 AI 智能推荐发现更多领域特定的关系类型
                </p>
                <Button onClick={handleStartAnalysis} disabled={recommendMutation.isPending}>
                  <Sparkles className="h-4 w-4 mr-2" />
                  {recommendMutation.isPending ? '分析文档中...' : '开始 AI 分析'}
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {relationTypes?.map((type: RelationType) => (
                <Card key={type.name}>
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-x-2">
                        <GitBranch className="h-5 w-5 text-primary" />
                        <CardTitle className="text-lg">{type.name}</CardTitle>
                      </div>
                      {type.is_builtin && (
                        <Badge variant="secondary">内置</Badge>
                      )}
                    </div>
                    <CardDescription>{type.description}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">关系数量</span>
                        <span className="font-medium">{type.instance_count}</span>
                      </div>
                      <div className="flex items-center gap-x-2 text-xs">
                        <Badge variant="outline">
                          {type.source_types.join(' | ') || 'Any'}
                        </Badge>
                        <span>→</span>
                        <Badge variant="outline">
                          {type.target_types.join(' | ') || 'Any'}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-x-2">
                        <Button variant="outline" size="sm" disabled={type.is_builtin}>
                          编辑
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="text-destructive"
                          disabled={type.is_builtin}
                        >
                          删除
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="versions" className="space-y-4">
          <Card>
            <CardContent className="py-12 text-center text-muted-foreground">
              版本历史功能开发中...
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* AI Recommendation Apply Dialog */}
      <Dialog open={showApplyDialog} onOpenChange={setShowApplyDialog}>
        <DialogContent className="max-w-4xl max-h-[80vh]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5" />
              AI 推荐结果
            </DialogTitle>
            <DialogDescription>
              查看并选择要导入的实体类型和关系类型
            </DialogDescription>
          </DialogHeader>

          {recommendation && (
            <div className="space-y-4">
              {/* Analysis Summary */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium">分析摘要</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    {recommendation.entity_types?.length || 0} 个推荐实体类型，
                    {recommendation.relation_types?.length || 0} 个推荐关系类型
                  </p>
                </CardContent>
              </Card>

              <div className="grid gap-4 md:grid-cols-2">
                {/* Entity Types */}
                <div className="space-y-2">
                  <h4 className="font-medium flex items-center gap-2">
                    <Tag className="h-4 w-4" />
                    实体类型
                    <Badge variant="secondary">
                      {Array.from(selectedEntityTypes).length} / {recommendation.entity_types?.length || 0}
                    </Badge>
                  </h4>
                  <ScrollArea className="h-64 border rounded-md p-2">
                    <div className="space-y-2">
                      {recommendation.entity_types?.map((entityType: any) => (
                        <div
                          key={entityType.name}
                          className={`flex items-start gap-2 p-2 rounded-md cursor-pointer transition-colors ${
                            selectedEntityTypes.has(entityType.name)
                              ? 'bg-primary/10 border border-primary'
                              : 'bg-muted hover:bg-muted/50'
                          }`}
                          onClick={() => toggleEntityType(entityType.name)}
                        >
                          <div className="mt-1">
                            {selectedEntityTypes.has(entityType.name) ? (
                              <Check className="h-4 w-4 text-primary" />
                            ) : (
                              <X className="h-4 w-4 text-muted-foreground" />
                            )}
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <div
                                className="h-2 w-2 rounded-full"
                                style={{ backgroundColor: entityType.color }}
                              />
                              <span className="font-medium">{entityType.name}</span>
                            </div>
                            <p className="text-xs text-muted-foreground mt-1">
                              {entityType.description}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </div>

                {/* Relation Types */}
                <div className="space-y-2">
                  <h4 className="font-medium flex items-center gap-2">
                    <GitBranch className="h-4 w-4" />
                    关系类型
                    <Badge variant="secondary">
                      {Array.from(selectedRelationTypes).length} / {recommendation.relation_types?.length || 0}
                    </Badge>
                  </h4>
                  <ScrollArea className="h-64 border rounded-md p-2">
                    <div className="space-y-2">
                      {recommendation.relation_types?.map((relationType: any) => (
                        <div
                          key={relationType.name}
                          className={`flex items-start gap-2 p-2 rounded-md cursor-pointer transition-colors ${
                            selectedRelationTypes.has(relationType.name)
                              ? 'bg-primary/10 border border-primary'
                              : 'bg-muted hover:bg-muted/50'
                          }`}
                          onClick={() => toggleRelationType(relationType.name)}
                        >
                          <div className="mt-1">
                            {selectedRelationTypes.has(relationType.name) ? (
                              <Check className="h-4 w-4 text-primary" />
                            ) : (
                              <X className="h-4 w-4 text-muted-foreground" />
                            )}
                          </div>
                          <div className="flex-1">
                            <div className="font-medium">{relationType.name}</div>
                            <p className="text-xs text-muted-foreground mt-1">
                              {relationType.description}
                            </p>
                            <div className="flex items-center gap-1 mt-1 text-xs">
                              <Badge variant="outline" className="text-xs">
                                {relationType.source_types.join(' | ') || 'Any'}
                              </Badge>
                              <ArrowRight className="h-3 w-3" />
                              <Badge variant="outline" className="text-xs">
                                {relationType.target_types.join(' | ') || 'Any'}
                              </Badge>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </div>
              </div>
            </div>
          )}

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowApplyDialog(false)}
            >
              取消
            </Button>
            <Button
              onClick={handleApplySelected}
              disabled={applyMutation.isPending || selectedEntityTypes.size === 0}
            >
              {applyMutation.isPending ? (
                <>
                  <RotateCw className="h-4 w-4 mr-2 animate-spin" />
                  导入中...
                </>
              ) : (
                <>
                  <Check className="h-4 w-4 mr-2" />
                  导入选中的类型 ({selectedEntityTypes.size + selectedRelationTypes.size})
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
