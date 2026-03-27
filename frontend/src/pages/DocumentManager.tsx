import { useState } from 'react'
import { DocumentUpload } from '@/components/DocumentUpload'
import { useQuery } from '@tanstack/react-query'
import { documentApi } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
import { FileText, Clock, CheckCircle, XCircle, Search, Trash2 } from 'lucide-react'
import { Link } from 'react-router-dom'

interface DocumentItem {
  id: string
  title: string
  filename: string
  file_size: number
  file_type: string
  upload_status: string
  created_at: string
  parse_error?: string | null
  chunk_count?: number
}

export function DocumentManager() {
  const [searchQuery, setSearchQuery] = useState('')
  const [domainKey] = useState<string | undefined>(undefined)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['documents', { q: searchQuery }],
    queryFn: () => documentApi.list({ q: searchQuery, page: 1, page_size: 20 }).then(res => res.data),
  })

  const handleUploadSuccess = () => {
    refetch()
  }

  const handleDelete = async (documentId: string) => {
    if (!confirm('确定要删除此文档吗？')) {
      return
    }

    try {
      await documentApi.delete(documentId)
      refetch()
    } catch (error) {
      console.error('Delete failed:', error)
      alert('删除文档失败')
    }
  }

  const getStatusBadge = (status: string) => {
    const variants: Record<string, 'default' | 'secondary' | 'success' | 'destructive'> = {
      pending: 'secondary',
      processing: 'secondary',
      complete: 'success',
      failed: 'destructive',
    }

    const icons: Record<string, JSX.Element> = {
      pending: <Clock className="h-3 w-3 mr-1" />,
      processing: <Clock className="h-3 w-3 mr-1 animate-spin" />,
      complete: <CheckCircle className="h-3 w-3 mr-1" />,
      failed: <XCircle className="h-3 w-3 mr-1" />,
    }

    return (
      <Badge variant={variants[status] || 'secondary'}>
        {icons[status] || icons.pending}
        {status}
      </Badge>
    )
  }

  const getFileIcon = (fileType: string) => {
    if (fileType.includes('pdf')) {
      return <FileText className="h-5 w-5 text-red-500" />
    }
    if (fileType.includes('word')) {
      return <FileText className="h-5 w-5 text-blue-500" />
    }
    return <FileText className="h-5 w-5 text-gray-500" />
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">文档管理</h1>
        <div className="relative max-w-sm flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="搜索文档..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">上传新文档</CardTitle>
        </CardHeader>
        <CardContent>
          <DocumentUpload
            onUploadSuccess={handleUploadSuccess}
            onUploadError={(error) => alert(`上传失败: ${error.message}`)}
            domainKey={domainKey}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">文档列表</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-12 text-muted-foreground">加载中...</div>
          ) : (
            <div className="space-y-4">
              {data?.items?.map((doc: DocumentItem) => (
                <Link key={doc.id} to={`/documents/${doc.id}`}>
                  <Card className="hover:bg-secondary/50 transition-colors cursor-pointer">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-x-3 flex-1">
                          <div className="mt-0.5">{getFileIcon(doc.file_type)}</div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-x-2">
                              <h3 className="font-semibold truncate">{doc.title}</h3>
                              {getStatusBadge(doc.upload_status)}
                            </div>
                            <p className="text-sm text-muted-foreground mt-1">
                              {doc.filename}
                            </p>
                            <div className="flex items-center gap-x-4 mt-2 text-xs text-muted-foreground">
                              <span>{formatFileSize(doc.file_size)}</span>
                              <span>·</span>
                              <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                              {doc.chunk_count !== undefined && (
                                <>
                                  <span>·</span>
                                  <span>{doc.chunk_count} chunks</span>
                                </>
                              )}
                            </div>
                            {doc.parse_error && (
                              <p className="text-xs text-destructive mt-2">
                                Error: {doc.parse_error}
                              </p>
                            )}
                          </div>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.preventDefault()
                            e.stopPropagation()
                            handleDelete(doc.id)
                          }}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              ))}

              {data?.items?.length === 0 && (
                <div className="text-center py-12 text-muted-foreground">
                  暂无文档
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}