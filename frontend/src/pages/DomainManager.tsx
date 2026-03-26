'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { domainApi } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Input } from '@/components/ui/Input'
import { Textarea } from '@/components/ui/Textarea'
import { Label } from '@/components/ui/Label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import {
  Plus,
  Trash2,
  Check,
  ChevronDown,
  ChevronUp,
  Activity,
} from 'lucide-react'

export function DomainManager() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState('list')
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [expandedDomain, setExpandedDomain] = useState<string | null>(null)

  const { data: domains, isLoading } = useQuery({
    queryKey: ['domains'],
    queryFn: () => domainApi.list().then(res => res.data),
  })

  const { data: activeDomain } = useQuery({
    queryKey: ['activeDomain'],
    queryFn: () => domainApi.getActive().then(res => res.data).catch(() => null),
  })

  const createDomainMutation = useMutation({
    mutationFn: (data: any) => domainApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['domains'] })
      queryClient.invalidateQueries({ queryKey: ['activeDomain'] })
      setShowCreateForm(false)
    },
  })

  const activateDomainMutation = useMutation({
    mutationFn: (domainKey: string) => domainApi.activate(domainKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['domains'] })
      queryClient.invalidateQueries({ queryKey: ['activeDomain'] })
    },
  })

  const deleteDomainMutation = useMutation({
    mutationFn: (domainKey: string) => domainApi.delete(domainKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['domains'] })
      queryClient.invalidateQueries({ queryKey: ['activeDomain'] })
    },
  })

  const toggleExpand = (domainKey: string) => {
    setExpandedDomain(expandedDomain === domainKey ? null : domainKey)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">领域管理</h1>
          <p className="text-muted-foreground mt-1">
            管理领域定义、配置和本体 Schema
          </p>
        </div>
        <Button onClick={() => setShowCreateForm(!showCreateForm)}>
          <Plus className="h-4 w-4 mr-2" />
          {showCreateForm ? '取消创建' : '创建领域'}
        </Button>
      </div>

      {showCreateForm && <CreateDomainForm onSubmit={createDomainMutation.mutate} />}

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <div className="flex items-center justify-between">
          <TabsList>
            <TabsTrigger value="list">领域列表</TabsTrigger>
            <TabsTrigger value="active">激活领域</TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="list" className="space-y-4">
          {isLoading ? (
            <div className="text-center py-12">加载领域列表...</div>
          ) : domains && domains.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {domains.map((domain: any) => (
                <DomainCard
                  key={domain.domain_key}
                  domain={domain}
                  isActive={activeDomain?.domain_key === domain.domain_key}
                  onActivate={() => activateDomainMutation.mutate(domain.domain_key)}
                  onDelete={() => {
                    if (confirm(`确定要删除领域 "${domain.name}" 吗？`)) {
                      deleteDomainMutation.mutate(domain.domain_key)
                    }
                  }}
                  onExpand={() => toggleExpand(domain.domain_key)}
                  isExpanded={expandedDomain === domain.domain_key}
                />
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                还没有创建任何领域，点击上方按钮创建第一个领域
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="active" className="space-y-4">
          {activeDomain ? (
            <DomainCard
              domain={activeDomain}
              isActive={true}
              onActivate={() => {}}
              onDelete={() => {}}
              onExpand={() => toggleExpand(activeDomain.domain_key)}
              isExpanded={expandedDomain === activeDomain.domain_key}
            />
          ) : (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                暂无激活的领域
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}

function CreateDomainForm({ onSubmit }: { onSubmit: (data: any) => void }) {
  const [formData, setFormData] = useState({
    domain_key: '',
    name: '',
    description: '',
    extraction_prompt_template: '',
    parent_domain_key: '',
    inherits_base_ontology: true,
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit({
      ...formData,
      parent_domain_key: formData.parent_domain_key || null,
    })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>创建新领域</CardTitle>
        <CardDescription>定义领域的基本信息和配置</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="domain_key">领域标识符 *</Label>
              <Input
                id="domain_key"
                value={formData.domain_key}
                onChange={(e) => setFormData({ ...formData, domain_key: e.target.value })}
                placeholder="medical_research"
                required
              />
              <p className="text-sm text-muted-foreground">
                小写字母、数字、下划线或连字符（3-50字符）
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="name">领域名称 *</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="医疗研究"
                required
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">描述</Label>
            <Textarea
              id="description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="医疗研究领域的本体定义和提取规则..."
              rows={3}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="extraction_prompt_template">提取提示模板</Label>
            <Textarea
              id="extraction_prompt_template"
              value={formData.extraction_prompt_template}
              onChange={(e) => setFormData({ ...formData, extraction_prompt_template: e.target.value })}
              placeholder="自定义的实体/关系提取提示模板..."
              rows={5}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="parent_domain_key">父领域</Label>
              <Input
                id="parent_domain_key"
                value={formData.parent_domain_key}
                onChange={(e) => setFormData({ ...formData, parent_domain_key: e.target.value })}
                placeholder="留空表示无父领域"
              />
            </div>

            <div className="space-y-2 flex items-center">
              <Label htmlFor="inherits_base_ontology">继承基础本体</Label>
              <input
                id="inherits_base_ontology"
                type="checkbox"
                checked={formData.inherits_base_ontology}
                onChange={(e) => setFormData({ ...formData, inherits_base_ontology: e.target.checked })}
                className="ml-2"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => {
              document.querySelector('#domain-manager button')?.click()
            }}>
              取消
            </Button>
            <Button type="submit">
              <Check className="h-4 w-4 mr-2" />
              创建领域
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

function DomainCard({
  domain,
  isActive,
  onActivate,
  onDelete,
  onExpand,
  isExpanded,
}: {
  domain: any
  isActive: boolean
  onActivate: () => void
  onDelete: () => void
  onExpand: () => void
  isExpanded: boolean
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-x-2">
              <CardTitle className="text-lg">{domain.name}</CardTitle>
              {isActive && (
                <Badge variant="default">
                  <Activity className="h-3 w-3 mr-1" />
                  激活中
                </Badge>
              )}
            </div>
            <CardDescription>
              {domain.description || '暂无描述'}
            </CardDescription>
            <div className="flex items-center gap-x-2 mt-2">
              <Badge variant="secondary" className="text-xs">
                标识符: {domain.domain_key}
              </Badge>
              {domain.parent_domain_key && (
                <Badge variant="outline" className="text-xs">
                  继承自: {domain.parent_domain_key}
                </Badge>
              )}
            </div>
          </div>
          <div className="flex flex-col gap-y-1">
            {!isActive && (
              <Button
                variant="outline"
                size="sm"
                onClick={onActivate}
                className="text-xs"
              >
                激活
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={onExpand}
              className="text-xs"
            >
              {isExpanded ? (
                <>
                  <ChevronUp className="h-3 w-3 mr-1" />
                  收起
                </>
              ) : (
                <>
                  <ChevronDown className="h-3 w-3 mr-1" />
                  展开
                </>
              )}
            </Button>
          </div>
        </div>
      </CardHeader>

      {isExpanded && (
        <CardContent className="space-y-3 pt-0 border-t">
          <div className="grid grid-cols-2 gap-x-4">
            <div>
              <p className="text-sm font-medium text-muted-foreground">创建者</p>
              <p className="text-sm">{domain.created_by}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">版本</p>
              <p className="text-sm">{domain.version}</p>
            </div>
          </div>

          {domain.extraction_prompt_template && (
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-1">提取提示模板</p>
              <div className="text-xs bg-muted p-2 rounded max-h-32 overflow-auto">
                {domain.extraction_prompt_template}
              </div>
            </div>
          )}

          <div className="flex items-center gap-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={onDelete}
              className="text-destructive"
            >
              <Trash2 className="h-3 w-3 mr-1" />
              删除
            </Button>
          </div>
        </CardContent>
      )}
    </Card>
  )
}
