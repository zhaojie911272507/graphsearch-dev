'use client'

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { ontologyApi } from '@/lib/api'
import type {
  OntologyApplyRecommendationsRequest,
  OntologyRecommendationsBundle,
  OntologyRecommendRequest,
  RecommendedEntityTypeDraft,
  RecommendedRelationTypeDraft,
} from '@/schemas/api-contracts'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { ScrollArea } from '@/components/ui/ScrollArea'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/Dialog'
import { useToast } from '@/contexts/ToastContext'
import { Brain, Sparkles, RotateCw, Check, X, Tag, GitBranch, ArrowRight } from 'lucide-react'

interface EntityExtractPanelProps {
  onSuccess?: () => void
}

export function EntityExtractPanel({ onSuccess }: EntityExtractPanelProps) {
  const [showApplyDialog, setShowApplyDialog] = useState(false)
  const [recommendation, setRecommendation] = useState<OntologyRecommendationsBundle | null>(null)
  const [selectedEntityTypes, setSelectedEntityTypes] = useState<Set<string>>(new Set())
  const [selectedRelationTypes, setSelectedRelationTypes] = useState<Set<string>>(new Set())
  const { toast } = useToast()

  // AI Recommendation mutation
  const recommendMutation = useMutation({
    mutationFn: (data?: OntologyRecommendRequest) => ontologyApi.getRecommendations(data),
    onSuccess: (response) => {
      if (response.data.success) {
        setRecommendation(response.data.recommendations)
        setShowApplyDialog(true)
        setSelectedEntityTypes(new Set(response.data.recommendations.entity_types.map((t) => t.name)))
        setSelectedRelationTypes(new Set(response.data.recommendations.relation_types.map((t) => t.name)))
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
    mutationFn: (data: OntologyApplyRecommendationsRequest) =>
      ontologyApi.applyRecommendations(data),
    onSuccess: (response) => {
      if (response.data.success) {
        toast({
          title: '导入成功',
          description: `已创建 ${response.data.created.entity_types.length} 个实体类型和 ${response.data.created.relation_types.length} 个关系类型`,
        })
        setShowApplyDialog(false)
        setRecommendation(null)
        onSuccess?.()
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

    const entityTypesToApply = recommendation.entity_types.filter((t) => selectedEntityTypes.has(t.name))
    const relationTypesToApply = recommendation.relation_types.filter((t) => selectedRelationTypes.has(t.name))

    applyMutation.mutate({
      entity_types: entityTypesToApply,
      relation_types: relationTypesToApply,
    })
  }

  const toggleEntityType = (name: string) => {
    setSelectedEntityTypes((prev) => {
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
    setSelectedRelationTypes((prev) => {
      const next = new Set(prev)
      if (next.has(name)) {
        next.delete(name)
      } else {
        next.add(name)
      }
      return next
    })
  }

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Brain className="h-5 w-5 text-primary" />
                AI 智能本体抽取
              </CardTitle>
              <CardDescription className="mt-1">
                基于文档内容自动分析并推荐实体类型和关系类型
              </CardDescription>
            </div>
            <Button
              onClick={handleStartAnalysis}
              disabled={recommendMutation.isPending}
              className="gap-2"
            >
              <Sparkles className="h-4 w-4" />
              {recommendMutation.isPending ? '分析中...' : '开始分析'}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm font-medium">
                <Tag className="h-4 w-4 text-primary" />
                实体类型推荐
              </div>
              <div className="text-xs text-muted-foreground">
                {recommendation?.entity_types?.length || 0} 个推荐实体类型
              </div>
            </div>
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm font-medium">
                <GitBranch className="h-4 w-4 text-primary" />
                关系类型推荐
              </div>
              <div className="text-xs text-muted-foreground">
                {recommendation?.relation_types?.length || 0} 个推荐关系类型
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

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
                      {recommendation.entity_types?.map((entityType: RecommendedEntityTypeDraft) => (
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
                      {recommendation.relation_types?.map((relationType: RecommendedRelationTypeDraft) => (
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
    </>
  )
}
