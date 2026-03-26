'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ontologyApi } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import {
  GitBranch,
  Tag,
} from 'lucide-react'

export function OntologyManager() {
  const [activeTab, setActiveTab] = useState('entity-types')

  const { data: entityTypes, isLoading: entityTypesLoading } = useQuery({
    queryKey: ['entityTypes'],
    queryFn: () => ontologyApi.getEntityTypes(true, true).then(res => res.data),
  })

  const { data: relationTypes } = useQuery({
    queryKey: ['relationTypes'],
    queryFn: () => ontologyApi.getRelationTypes(true, true).then(res => res.data),
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">本体管理</h1>
          <p className="text-muted-foreground mt-1">
            管理实体类型和关系类型的定义，构建领域知识 Schema
          </p>
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
          {entityTypesLoading ? (
            <div className="text-center py-12">加载实体类型...</div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {entityTypes?.map((type: any) => (
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
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {relationTypes?.map((type: any) => (
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
        </TabsContent>

        <TabsContent value="versions" className="space-y-4">
          <Card>
            <CardContent className="py-12 text-center text-muted-foreground">
              版本历史功能开发中...
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
