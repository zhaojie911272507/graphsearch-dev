'use client'

import { useQuery } from '@tanstack/react-query'
import { assetApi } from '@/lib/api'
import { useAppStore } from '@/store/appStore'
import { Input } from '@/components/ui/Input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { FileText, Tag, GitBranch, Star } from 'lucide-react'
import { Link } from 'react-router-dom'

/** Radix Select.Item does not allow an empty string value. */
const ASSET_TYPE_ALL = '__all__'

export function AssetCatalog() {
  const { selectedAssetType, setSelectedAssetType, searchQuery, setSearchQuery } = useAppStore()

  const { data, isLoading } = useQuery({
    queryKey: ['assets', { type: selectedAssetType, q: searchQuery }],
    queryFn: () => assetApi.list({
      type: selectedAssetType || undefined,
      q: searchQuery || undefined,
      page: 1,
      page_size: 20,
    }).then(res => res.data),
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">资产目录</h1>
        <div className="flex items-center gap-x-4">
          <Select
            value={selectedAssetType || ASSET_TYPE_ALL}
            onValueChange={(v) => setSelectedAssetType(v === ASSET_TYPE_ALL ? '' : v)}
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="全部类型" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ASSET_TYPE_ALL}>全部类型</SelectItem>
              <SelectItem value="Entity">实体</SelectItem>
              <SelectItem value="Document">文档</SelectItem>
              <SelectItem value="Concept">概念</SelectItem>
              <SelectItem value="Chunk">文本块</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="flex items-center gap-x-4">
        <Input
          placeholder="搜索资产..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="max-w-sm"
        />
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">加载中...</div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {data?.items?.map((asset: any) => (
            <Link key={asset.id} to={`/assets/${asset.id}`}>
              <Card className="hover:bg-secondary/50 transition-colors cursor-pointer h-full">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-x-2">
                      {asset.node_type === 'Document' && <FileText className="h-5 w-5 text-blue-500" />}
                      {asset.node_type === 'Entity' && <Tag className="h-5 w-5 text-green-500" />}
                      {asset.node_type === 'Concept' && <GitBranch className="h-5 w-5 text-purple-500" />}
                      {asset.node_type === 'Chunk' && <FileText className="h-5 w-5 text-gray-500" />}
                      <CardTitle className="text-lg">{asset.name}</CardTitle>
                    </div>
                    <Badge variant={asset.node_type === 'Entity' ? 'default' : 'secondary'}>
                      {asset.node_type}
                    </Badge>
                  </div>
                  {asset.entity_type && (
                    <div className="text-sm text-muted-foreground mt-1">
                      {asset.entity_type}
                    </div>
                  )}
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between text-sm text-muted-foreground">
                    <div className="flex items-center gap-x-4">
                      <span className="flex items-center gap-x-1">
                        <GitBranch className="h-4 w-4" />
                        {asset.relation_count} 关系
                      </span>
                      <span className="flex items-center gap-x-1">
                        <Star className="h-4 w-4" />
                        {(asset.quality_score * 20).toFixed(0)} 分
                      </span>
                    </div>
                    {asset.tags?.length > 0 && (
                      <div className="flex gap-x-1">
                        {asset.tags.slice(0, 3).map((tag: string) => (
                          <Badge key={tag} variant="outline" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}

      {data?.items?.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          暂无数据
        </div>
      )}
    </div>
  )
}
