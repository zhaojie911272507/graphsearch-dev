import { useParams } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { documentApi } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { FileText, Clock, CheckCircle, XCircle, ArrowLeft, RefreshCw, Trash2 } from 'lucide-react'
import { Link } from 'react-router-dom'

interface DocumentDetailData {
  id: string
  title: string
  filename: string
  file_size: number
  file_type: string
  upload_status: string
  parse_error?: string | null
  created_at: string
  updated_at: string
  content_hash?: string
  source_url?: string
  chunk_count?: number
}

export function DocumentDetail() {
  const { documentId } = useParams<{ documentId: string }>()
  const [document, setDocument] = useState<DocumentDetailData | null>(null)
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    if (!documentId) return

    const fetchDocument = async () => {
      try {
        setLoading(true)
        const response = await documentApi.getDetail(documentId)
        setDocument(response.data)
      } catch (error) {
        console.error('Failed to fetch document:', error)
        alert('Failed to load document details')
      } finally {
        setLoading(false)
      }
    }

    fetchDocument()
  }, [documentId])

  const handleRefresh = () => {
    if (documentId) {
      setLoading(true)
      documentApi.getDetail(documentId)
        .then(res => {
          setDocument(res.data)
          setLoading(false)
        })
        .catch(err => {
          console.error('Refresh failed:', err)
          alert('Refresh failed')
          setLoading(false)
        })
    }
  }

  const handleDelete = async () => {
    if (!documentId || !document) return

    if (!confirm(`确定要删除文档 "${document.title}" 吗？`)) {
      return
    }

    try {
      setDeleting(true)
      await documentApi.delete(documentId)
      alert('文档已删除')
      window.history.back()
    } catch (error) {
      console.error('Delete failed:', error)
      alert('删除文档失败')
    } finally {
      setDeleting(false)
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
      return <FileText className="h-8 w-8 text-red-500" />
    }
    if (fileType.includes('word')) {
      return <FileText className="h-8 w-8 text-blue-500" />
    }
    return <FileText className="h-8 w-8 text-gray-500" />
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-x-4">
          <Link to="/documents">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              返回
            </Button>
          </Link>
          <h1 className="text-3xl font-bold">文档详情</h1>
        </div>
        <div className="text-center py-12 text-muted-foreground">加载中...</div>
      </div>
    )
  }

  if (!document) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-x-4">
          <Link to="/documents">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              返回
            </Button>
          </Link>
          <h1 className="text-3xl font-bold">文档详情</h1>
        </div>
        <div className="text-center py-12 text-destructive">文档不存在</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-x-4">
          <Link to="/documents">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              返回
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold">{document.title}</h1>
            <p className="text-muted-foreground">{document.filename}</p>
          </div>
        </div>
        <div className="flex items-center gap-x-2">
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={loading}>
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
          <Button variant="destructive" size="sm" onClick={handleDelete} disabled={deleting}>
            <Trash2 className="h-4 w-4 mr-2" />
            {deleting ? '删除中...' : '删除'}
          </Button>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Document Info */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-x-2">
              {getFileIcon(document.file_type)}
              <span>文档信息</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">状态</span>
                <span>{getStatusBadge(document.upload_status)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">文件大小</span>
                <span>{formatFileSize(document.file_size)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">文件类型</span>
                <span>{document.file_type}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">创建时间</span>
                <span>{new Date(document.created_at).toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">更新时间</span>
                <span>{new Date(document.updated_at).toLocaleString()}</span>
              </div>
              {document.chunk_count !== undefined && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">文本块数量</span>
                  <span>{document.chunk_count}</span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Metadata */}
        <Card>
          <CardHeader>
            <CardTitle>元数据</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">文档 ID</span>
                <span className="font-mono text-xs">{document.id}</span>
              </div>
              {document.content_hash && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">内容哈希</span>
                  <span className="font-mono text-xs truncate max-w-xs">{document.content_hash}</span>
                </div>
              )}
              {document.source_url && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">来源链接</span>
                  <a
                    href={document.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline truncate max-w-xs"
                  >
                    {document.source_url}
                  </a>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Error Message */}
      {document.parse_error && (
        <Card>
          <CardHeader>
            <CardTitle className="text-destructive flex items-center gap-x-2">
              <XCircle className="h-5 w-5" />
              <span>解析错误</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="bg-destructive/10 border border-destructive/20 rounded p-4 text-sm overflow-auto">
              {document.parse_error}
            </pre>
          </CardContent>
        </Card>
      )}

      {/* Related Assets */}
      <Card>
        <CardHeader>
          <CardTitle>相关资产</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            相关文本块和实体将在后续版本中显示
          </div>
        </CardContent>
      </Card>
    </div>
  )
}