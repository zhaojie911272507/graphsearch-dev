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
import { Input } from '@/components/ui/Input'
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
  History,
  GitCompare,
  ArrowLeftRight,
  Plus,
  Clock,
  User,
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

  // Version management state
  const [selectedVersion, setSelectedVersion] = useState<string | null>(null)
  const [compareVersion, setCompareVersion] = useState<string | null>(null)
  const [showCreateVersionDialog, setShowCreateVersionDialog] = useState(false)
  const [showRollbackDialog, setShowRollbackDialog] = useState(false)
  const [rollbackVersion, setRollbackVersion] = useState<string | null>(null)
  const [versionViewMode, setVersionViewMode] = useState<'timeline' | 'compare'>('timeline')
  const [newVersionName, setNewVersionName] = useState('')
  const [newVersionSummary, setNewVersionSummary] = useState('')

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

  // Version history query
  const { data: versions, isLoading: versionsLoading, refetch: refetchVersions } = useQuery({
    queryKey: ['ontologyVersions'],
    queryFn: () => ontologyApi.getVersions(50).then(res => res.data),
  })

  // Version diff query
  const { data: versionDiff, isLoading: diffLoading } = useQuery({
    queryKey: ['ontologyVersionDiff', selectedVersion, compareVersion],
    queryFn: () => {
      if (!selectedVersion) return Promise.resolve(null)
      return ontologyApi.getOntologyDiff(selectedVersion, compareVersion || undefined).then(res => res.data)
    },
    enabled: !!selectedVersion,
  })

  // Create version mutation
  const createVersionMutation = useMutation({
    mutationFn: (data: { version: string; change_summary: string; changes: string[] }) =>
      ontologyApi.createVersion(data),
    onSuccess: () => {
      toast({ title: '版本创建成功', variant: 'default' })
      setShowCreateVersionDialog(false)
      setNewVersionName('')
      setNewVersionSummary('')
      refetchVersions()
    },
    onError: () => {
      toast({ title: '版本创建失败', variant: 'destructive' })
    },
  })

  // Rollback mutation
  const rollbackMutation = useMutation({
    mutationFn: (version: string) => ontologyApi.rollbackOntology(version),
    onSuccess: () => {
      toast({ title: `已回滚到版本 ${rollbackVersion}`, variant: 'default' })
      setShowRollbackDialog(false)
      setRollbackVersion(null)
      refetchVersions()
      refetch()
    },
    onError: () => {
      toast({ title: '回滚失败', variant: 'destructive' })
    },
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
          {/* Version Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TabsList>
                <TabsTrigger
                  value="timeline"
                  onClick={() => setVersionViewMode('timeline')}
                >
                  <Clock className="h-4 w-4 mr-1" />
                  时间线
                </TabsTrigger>
                <TabsTrigger
                  value="compare"
                  onClick={() => setVersionViewMode('compare')}
                >
                  <GitCompare className="h-4 w-4 mr-1" />
                  对比
                </TabsTrigger>
              </TabsList>
            </div>
            <Button onClick={() => setShowCreateVersionDialog(true)}>
              <Plus className="h-4 w-4 mr-2" />
              创建版本
            </Button>
          </div>

          {versionsLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : !versions || versions.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <History className="h-16 w-16 text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold mb-2">暂无版本历史</h3>
                <p className="text-muted-foreground text-center mb-4">
                  创建第一个本体版本以记录变更历史
                </p>
                <Button onClick={() => setShowCreateVersionDialog(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  创建版本
                </Button>
              </CardContent>
            </Card>
          ) : versionViewMode === 'timeline' ? (
            // Timeline View
            <div className="space-y-4">
              {versions.map((version: any, index: number) => (
                <Card key={version.version} className={version.is_active ? 'border-primary' : ''}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Tag className="h-5 w-5 text-primary" />
                        <CardTitle className="text-lg">{version.version}</CardTitle>
                        {version.is_active && (
                          <Badge variant="default">当前活跃</Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setSelectedVersion(version.version)
                            setCompareVersion(versions[index + 1]?.version || null)
                            setVersionViewMode('compare')
                          }}
                        >
                          <GitCompare className="h-4 w-4 mr-1" />
                          对比
                        </Button>
                        {!version.is_active && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setRollbackVersion(version.version)
                              setShowRollbackDialog(true)
                            }}
                          >
                            <RotateCw className="h-4 w-4 mr-1" />
                            回滚
                          </Button>
                        )}
                      </div>
                    </div>
                    <CardDescription>{version.change_summary}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between text-sm text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <User className="h-4 w-4" />
                        {version.created_by}
                      </div>
                      <div className="flex items-center gap-1">
                        <Clock className="h-4 w-4" />
                        {new Date(version.created_at).toLocaleString('zh-CN')}
                      </div>
                    </div>
                    {version.changes && version.changes.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {version.changes.map((change: string, idx: number) => (
                          <Badge key={idx} variant="outline">{change}</Badge>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            // Compare View
            <div className="space-y-4">
              {/* Version Selection */}
              <Card>
                <CardContent className="py-4">
                  <div className="flex items-center gap-4">
                    <div className="flex-1">
                      <label className="text-sm text-muted-foreground mb-1 block">比较版本</label>
                      <select
                        className="w-full border rounded px-3 py-2"
                        value={selectedVersion || ''}
                        onChange={(e) => setSelectedVersion(e.target.value)}
                      >
                        <option value="">选择版本...</option>
                        {versions.map((v: any) => (
                          <option key={v.version} value={v.version}>{v.version}</option>
                        ))}
                      </select>
                    </div>
                    <ArrowLeftRight className="h-5 w-5 mt-6" />
                    <div className="flex-1">
                      <label className="text-sm text-muted-foreground mb-1 block">对比版本</label>
                      <select
                        className="w-full border rounded px-3 py-2"
                        value={compareVersion || ''}
                        onChange={(e) => setCompareVersion(e.target.value)}
                      >
                        <option value="">选择版本...</option>
                        {versions.map((v: any) => (
                          <option key={v.version} value={v.version}>{v.version}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Diff Results */}
              {diffLoading ? (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
                </div>
              ) : versionDiff ? (
                <Card>
                  <CardHeader>
                    <CardTitle>版本对比结果</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {/* Added Entity Types */}
                      {versionDiff.added_entity_types && versionDiff.added_entity_types.length > 0 && (
                        <div>
                          <h4 className="text-sm font-medium text-green-600 mb-2">新增实体类型</h4>
                          <div className="flex flex-wrap gap-2">
                            {versionDiff.added_entity_types.map((type: string) => (
                              <Badge key={type} className="bg-green-100 text-green-800">{type}</Badge>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Removed Entity Types */}
                      {versionDiff.removed_entity_types && versionDiff.removed_entity_types.length > 0 && (
                        <div>
                          <h4 className="text-sm font-medium text-red-600 mb-2">删除实体类型</h4>
                          <div className="flex flex-wrap gap-2">
                            {versionDiff.removed_entity_types.map((type: string) => (
                              <Badge key={type} className="bg-red-100 text-red-800">{type}</Badge>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Modified Entity Types */}
                      {versionDiff.modified_entity_types && versionDiff.modified_entity_types.length > 0 && (
                        <div>
                          <h4 className="text-sm font-medium text-yellow-600 mb-2">修改实体类型</h4>
                          <div className="flex flex-wrap gap-2">
                            {versionDiff.modified_entity_types.map((type: string) => (
                              <Badge key={type} className="bg-yellow-100 text-yellow-800">{type}</Badge>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Added Relation Types */}
                      {versionDiff.added_relation_types && versionDiff.added_relation_types.length > 0 && (
                        <div>
                          <h4 className="text-sm font-medium text-green-600 mb-2">新增关系类型</h4>
                          <div className="flex flex-wrap gap-2">
                            {versionDiff.added_relation_types.map((type: string) => (
                              <Badge key={type} className="bg-green-100 text-green-800">{type}</Badge>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Removed Relation Types */}
                      {versionDiff.removed_relation_types && versionDiff.removed_relation_types.length > 0 && (
                        <div>
                          <h4 className="text-sm font-medium text-red-600 mb-2">删除关系类型</h4>
                          <div className="flex flex-wrap gap-2">
                            {versionDiff.removed_relation_types.map((type: string) => (
                              <Badge key={type} className="bg-red-100 text-red-800">{type}</Badge>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Modified Relation Types */}
                      {versionDiff.modified_relation_types && versionDiff.modified_relation_types.length > 0 && (
                        <div>
                          <h4 className="text-sm font-medium text-yellow-600 mb-2">修改关系类型</h4>
                          <div className="flex flex-wrap gap-2">
                            {versionDiff.modified_relation_types.map((type: string) => (
                              <Badge key={type} className="bg-yellow-100 text-yellow-800">{type}</Badge>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* No changes */}
                      {(!versionDiff.added_entity_types?.length) &&
                       (!versionDiff.removed_entity_types?.length) &&
                       (!versionDiff.modified_entity_types?.length) &&
                       (!versionDiff.added_relation_types?.length) &&
                       (!versionDiff.removed_relation_types?.length) &&
                       (!versionDiff.modified_relation_types?.length) && (
                        <p className="text-muted-foreground text-center py-4">两个版本之间没有差异</p>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ) : selectedVersion ? (
                <Card>
                  <CardContent className="py-8 text-center text-muted-foreground">
                    选择要对比的版本查看差异
                  </CardContent>
                </Card>
              ) : null}
            </div>
          )}

          {/* Create Version Dialog */}
          <Dialog open={showCreateVersionDialog} onOpenChange={setShowCreateVersionDialog}>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>创建本体版本</DialogTitle>
                <DialogDescription>
                  创建一个新的本体版本快照，记录当前状态
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium">版本号</label>
                  <Input
                    placeholder="例如: v1.0.0"
                    value={newVersionName}
                    onChange={(e) => setNewVersionName(e.target.value)}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">变更摘要</label>
                  <Input
                    placeholder="描述本次变更的内容"
                    value={newVersionSummary}
                    onChange={(e) => setNewVersionSummary(e.target.value)}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowCreateVersionDialog(false)}>
                  取消
                </Button>
                <Button
                  onClick={() => {
                    if (newVersionName && newVersionSummary) {
                      createVersionMutation.mutate({
                        version: newVersionName,
                        change_summary: newVersionSummary,
                        changes: newVersionSummary.split(',').map(s => s.trim()).filter(Boolean),
                      })
                    }
                  }}
                  disabled={!newVersionName || !newVersionSummary || createVersionMutation.isPending}
                >
                  {createVersionMutation.isPending ? '创建中...' : '创建'}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>

          {/* Rollback Confirmation Dialog */}
          <Dialog open={showRollbackDialog} onOpenChange={setShowRollbackDialog}>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>确认回滚</DialogTitle>
                <DialogDescription>
                  确定要回滚到版本 {rollbackVersion} 吗？此操作将记录到审计日志。
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowRollbackDialog(false)}>
                  取消
                </Button>
                <Button
                  variant="destructive"
                  onClick={() => {
                    if (rollbackVersion) {
                      rollbackMutation.mutate(rollbackVersion)
                    }
                  }}
                  disabled={rollbackMutation.isPending}
                >
                  {rollbackMutation.isPending ? '回滚中...' : '确认回滚'}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
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
