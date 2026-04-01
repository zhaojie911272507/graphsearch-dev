'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { evaluationApi } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/Dialog'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import { useToast } from '@/contexts/ToastContext'
import {
  Settings,
  Play,
  Save,
  Copy,
  ArrowRight,
  CheckCircle,
  XCircle,
  FileText,
  Scissors,
  Brain,
  Database,
  Search,
  MessageSquare,
} from 'lucide-react'

// Pipeline stages
type PipelineStage = 'ingestion' | 'chunking' | 'extraction' | 'graph_storage' | 'vector_index' | 'query'

interface StageConfig {
  enabled: boolean
  params: Record<string, any>
}

interface PipelineConfig {
  version: string
  ingestion: StageConfig
  chunking: StageConfig
  extraction: StageConfig
  graph_storage: StageConfig
  vector_index: StageConfig
  query: StageConfig
  created_at: string
  created_by: string
  is_active: boolean
}

// Stage configuration templates
const defaultStageConfigs: Record<PipelineStage, { params: Record<string, any> }> = {
  ingestion: {
    params: {
      source_type: 'file',
      parsers: ['pdf', 'docx', 'txt'],
      max_file_size: 10 * 1024 * 1024, // 10MB
    },
  },
  chunking: {
    params: {
      chunk_size: 500,
      chunk_overlap: 50,
      split_by: 'paragraph',
    },
  },
  extraction: {
    params: {
      model: 'gpt-4o',
      temperature: 0.0,
      max_retries: 3,
      extraction_prompt: 'default',
      batch_size: 10,
    },
  },
  graph_storage: {
    params: {
      batch_size: 100,
      index_type: 'node_label',
      create_constraints: true,
    },
  },
  vector_index: {
    params: {
      embedding_model: 'm3e-large',
      dimension: 1024,
      metric: 'cosine',
      index_type: 'hnsw',
    },
  },
  query: {
    params: {
      top_k: 5,
      hybrid_alpha: 0.5,
      rerank: true,
      max_context_chunks: 10,
    },
  },
}

const stageLabels: Record<PipelineStage, { title: string; description: string; icon: any }> = {
  ingestion: { title: '文档摄入', description: '文档解析和加载', icon: FileText },
  chunking: { title: '分块', description: '文本分块策略', icon: Scissors },
  extraction: { title: '实体提取', description: 'LLM 实体和关系提取', icon: Brain },
  graph_storage: { title: '图存储', description: 'Neo4j 图谱存储', icon: Database },
  vector_index: { title: '向量索引', description: '向量嵌入索引', icon: Search },
  query: { title: '查询', description: '检索和生成配置', icon: MessageSquare },
}

export default function PipelineConfig() {
  const [activeTab, setActiveTab] = useState<PipelineStage>('ingestion')
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [showTestDialog, setShowTestDialog] = useState(false)
  const [newVersion, setNewVersion] = useState('')
  const [configName, setConfigName] = useState('')

  // Current config being edited
  const [currentConfig, setCurrentConfig] = useState<Omit<PipelineConfig, 'version' | 'created_at' | 'created_by' | 'is_active'>>({
    ingestion: { enabled: true, params: defaultStageConfigs.ingestion.params },
    chunking: { enabled: true, params: defaultStageConfigs.chunking.params },
    extraction: { enabled: true, params: defaultStageConfigs.extraction.params },
    graph_storage: { enabled: true, params: defaultStageConfigs.graph_storage.params },
    vector_index: { enabled: true, params: defaultStageConfigs.vector_index.params },
    query: { enabled: true, params: defaultStageConfigs.query.params },
  })

  const queryClient = useQueryClient()
  const { toast } = useToast()

  // Fetch configs
  const { data: configsData, isLoading } = useQuery({
    queryKey: ['pipelineConfigs'],
    queryFn: () => evaluationApi.getPipelineConfigs().then(res => res.data),
  })

  const configs = configsData?.configs || []

  // Create config mutation
  const createMutation = useMutation({
    mutationFn: (data: { version: string; config: any; change_summary: string }) =>
      evaluationApi.createPipelineConfig({
        version: data.version,
        retrieval: { ...currentConfig },
        generation: {},
        change_summary: data.change_summary,
      }),
    onSuccess: () => {
      toast({ title: '配置保存成功', variant: 'default' })
      setShowCreateDialog(false)
      queryClient.invalidateQueries({ queryKey: ['pipelineConfigs'] })
    },
    onError: () => {
      toast({ title: '配置保存失败', variant: 'destructive' })
    },
  })

  // Activate config mutation
  const activateMutation = useMutation({
    mutationFn: (version: string) => evaluationApi.activatePipelineConfig(version),
    onSuccess: () => {
      toast({ title: '配置已激活', variant: 'default' })
      queryClient.invalidateQueries({ queryKey: ['pipelineConfigs'] })
    },
    onError: () => {
      toast({ title: '激活失败', variant: 'destructive' })
    },
  })

  // Update param for a stage
  const updateStageParam = (stage: PipelineStage, key: string, value: any) => {
    setCurrentConfig(prev => ({
      ...prev,
      [stage]: {
        ...prev[stage],
        params: {
          ...prev[stage].params,
          [key]: value,
        },
      },
    }))
  }

  // Toggle stage enabled
  const toggleStage = (stage: PipelineStage) => {
    setCurrentConfig(prev => ({
      ...prev,
      [stage]: {
        ...prev[stage],
        enabled: !prev[stage].enabled,
      },
    }))
  }

  // Render parameter input
  const renderParamInput = (stage: PipelineStage, key: string, value: any) => {
    if (typeof value === 'boolean') {
      return (
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={value}
            onChange={(e) => updateStageParam(stage, key, e.target.checked)}
            className="w-4 h-4"
          />
          <span className="text-sm text-muted-foreground">
            {value ? '已启用' : '已禁用'}
          </span>
        </div>
      )
    }

    if (typeof value === 'number') {
      return (
        <Input
          type="number"
          value={value}
          onChange={(e) => updateStageParam(stage, key, Number(e.target.value))}
          className="h-8"
        />
      )
    }

    if (Array.isArray(value)) {
      return (
        <Input
          value={value.join(', ')}
          onChange={(e) => updateStageParam(stage, key, e.target.value.split(',').map(s => s.trim()))}
          placeholder="逗号分隔"
          className="h-8"
        />
      )
    }

    return (
      <Input
        value={value}
        onChange={(e) => updateStageParam(stage, key, e.target.value)}
        className="h-8"
      />
    )
  }

  // Get params for a stage
  const getStageParams = (stage: PipelineStage) => {
    return Object.entries(currentConfig[stage].params)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">RAG 管道配置</h1>
          <p className="text-muted-foreground mt-1">
            配置完整的 RAG 管道：从文档摄入到查询生成
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => setShowTestDialog(true)}>
            <Play className="h-4 w-4 mr-2" />
            测试管道
          </Button>
          <Button onClick={() => setShowCreateDialog(true)}>
            <Save className="h-4 w-4 mr-2" />
            保存配置
          </Button>
        </div>
      </div>

      {/* Stage Tabs */}
      <div className="flex gap-4 overflow-x-auto pb-2">
        {(Object.keys(stageLabels) as PipelineStage[]).map(stage => {
          const label = stageLabels[stage]
          const Icon = label.icon
          const isEnabled = currentConfig[stage].enabled

          return (
            <button
              key={stage}
              onClick={() => setActiveTab(stage)}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg border transition-colors ${
                activeTab === stage
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-primary/50'
              }`}
            >
              <Icon className={`h-5 w-5 ${isEnabled ? 'text-primary' : 'text-muted-foreground'}`} />
              <div className="text-left">
                <div className="font-medium">{label.title}</div>
                <div className="text-xs text-muted-foreground">{label.description}</div>
              </div>
              {isEnabled ? (
                <CheckCircle className="h-4 w-4 text-green-500" />
              ) : (
                <XCircle className="h-4 w-4 text-muted-foreground" />
              )}
            </button>
          )
        })}
      </div>

      {/* Stage Configuration */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>{stageLabels[activeTab].title} 配置</CardTitle>
              <CardDescription>{stageLabels[activeTab].description}</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">启用状态</span>
              <button
                onClick={() => toggleStage(activeTab)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  currentConfig[activeTab].enabled ? 'bg-primary' : 'bg-muted'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    currentConfig[activeTab].enabled ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            {getStageParams(activeTab).map(([key, value]) => (
              <div key={key} className="space-y-2">
                <Label className="text-sm font-medium">{key}</Label>
                {renderParamInput(activeTab, key, value)}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Saved Configs */}
      <Card>
        <CardHeader>
          <CardTitle>已保存的配置</CardTitle>
          <CardDescription>管理不同的管道配置版本</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
            </div>
          ) : configs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              暂无保存的配置
            </div>
          ) : (
            <div className="space-y-3">
              {configs.map((config: any) => (
                <div
                  key={config.version}
                  className={`flex items-center justify-between p-4 border rounded-lg ${
                    config.is_active ? 'border-primary bg-primary/5' : ''
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Settings className="h-5 w-5 text-muted-foreground" />
                    <div>
                      <div className="font-medium">{config.version}</div>
                      <div className="text-sm text-muted-foreground">
                        创建者: {config.created_by} | {new Date(config.created_at).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {config.is_active ? (
                      <Badge variant="default">活跃</Badge>
                    ) : (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => activateMutation.mutate(config.version)}
                        disabled={activateMutation.isPending}
                      >
                        <Play className="h-4 w-4 mr-1" />
                        激活
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        // Load config
                        if (config.retrieval) {
                          setCurrentConfig(config.retrieval as any)
                        }
                      }}
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Config Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>保存管道配置</DialogTitle>
            <DialogDescription>
              创建一个新的管道配置版本
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>版本号</Label>
              <Input
                placeholder="例如: v1.0.0"
                value={newVersion}
                onChange={(e) => setNewVersion(e.target.value)}
              />
            </div>
            <div>
              <Label>配置名称（可选）</Label>
              <Input
                placeholder="例如: 高精度配置"
                value={configName}
                onChange={(e) => setConfigName(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
              取消
            </Button>
            <Button
              onClick={() => {
                if (newVersion) {
                  createMutation.mutate({
                    version: newVersion,
                    config: currentConfig,
                    change_summary: configName || `更新配置 ${newVersion}`,
                  })
                }
              }}
              disabled={!newVersion || createMutation.isPending}
            >
              {createMutation.isPending ? '保存中...' : '保存'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Test Pipeline Dialog */}
      <Dialog open={showTestDialog} onOpenChange={setShowTestDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>测试管道</DialogTitle>
            <DialogDescription>
              使用测试查询验证管道配置
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>测试查询</Label>
              <Input placeholder="输入测试查询..." />
            </div>
            <div className="p-4 bg-muted rounded-lg">
              <div className="text-sm text-muted-foreground mb-2">管道流程预览</div>
              <div className="flex items-center gap-2 flex-wrap">
                {(Object.keys(stageLabels) as PipelineStage[]).map((stage, idx) => (
                  <div key={stage} className="flex items-center">
                    <Badge variant={currentConfig[stage].enabled ? 'default' : 'secondary'}>
                      {stageLabels[stage].title}
                    </Badge>
                    {idx < 5 && <ArrowRight className="h-4 w-4 mx-1 text-muted-foreground" />}
                  </div>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowTestDialog(false)}>
              关闭
            </Button>
            <Button>
              <Play className="h-4 w-4 mr-2" />
              运行测试
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}