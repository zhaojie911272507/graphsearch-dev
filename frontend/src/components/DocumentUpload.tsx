import { cn } from '@/lib/utils'
import { useDropzone } from 'react-dropzone'
import { FileUp, FileText, FileCheck } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { useState } from 'react'

interface DocumentUploadProps {
  onUploadSuccess?: (result: any) => void
  onUploadError?: (error: any) => void
  domainKey?: string
  multiple?: boolean
  className?: string
}

const MAX_FILE_SIZE = 50 * 1024 * 1024 // 50 MB
const ACCEPTED_FILE_TYPES = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'text/plain': ['.txt'],
}

export function DocumentUpload({
  onUploadSuccess,
  onUploadError,
  domainKey,
  multiple = false,
  className,
}: DocumentUploadProps) {
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)

  const onDrop = async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return

    setUploading(true)
    setUploadProgress(0)

    try {
      const file = acceptedFiles[0]
      const formData = new FormData()
      formData.append('file', file)
      if (domainKey) {
        formData.append('domain_key', domainKey)
      }

      // Mock progress for UX (real progress would come from server)
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval)
            return prev
          }
          return prev + 10
        })
      }, 300)

      const response = await fetch('/api/v1/documents/upload', {
        method: 'POST',
        body: formData,
      })

      clearInterval(progressInterval)
      setUploadProgress(100)

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Upload failed')
      }

      const result = await response.json()
      setUploading(false)
      setUploadProgress(0)

      if (onUploadSuccess) {
        onUploadSuccess(result)
      }
    } catch (error) {
      setUploading(false)
      setUploadProgress(0)
      console.error('Upload error:', error)
      if (onUploadError) {
        onUploadError(error)
      }
    }
  }

  const { getRootProps, getInputProps, isDragActive, isDragReject, acceptedFiles } = useDropzone({
    onDrop,
    accept: ACCEPTED_FILE_TYPES,
    maxSize: MAX_FILE_SIZE,
    multiple,
  })

  const files = acceptedFiles.map(file => (
    <li key={file.path} className="flex items-center gap-x-2 text-sm">
      <FileCheck className="h-4 w-4 text-green-500" />
      {file.path} - {(file.size / 1024 / 1024).toFixed(2)} MB
    </li>
  ))

  return (
    <div className={cn('w-full', className)}>
      <div
        {...getRootProps()}
        className={cn(
          'border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors',
          'hover:border-primary/50',
          isDragActive ? 'border-primary bg-primary/5' : '',
          isDragReject ? 'border-destructive bg-destructive/5' : '',
          uploading ? 'opacity-50 cursor-not-allowed' : ''
        )}
      >
        <input {...getInputProps()} disabled={uploading} />

        <div className="flex flex-col items-center gap-y-4">
          {uploading ? (
            <>
              <FileUp className="h-12 w-12 text-primary animate-pulse" />
              <div className="flex flex-col items-center gap-y-2">
                <p className="text-sm font-medium">Uploading...</p>
                <div className="w-48 h-2 bg-secondary rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
                <p className="text-xs text-muted-foreground">{uploadProgress}%</p>
              </div>
            </>
          ) : (
            <>
              <FileText className="h-12 w-12 text-muted-foreground" />
              <div className="space-y-2">
                <p className="text-lg font-medium">
                  {isDragActive ? 'Drop the file here...' : 'Drag & Drop your document here'}
                </p>
                <p className="text-sm text-muted-foreground">
                  or click to browse files
                </p>
                <p className="text-xs text-muted-foreground">
                  Supported formats: PDF, DOCX, TXT (max {MAX_FILE_SIZE / 1024 / 1024}MB)
                </p>
              </div>
              <Button variant="outline" size="sm">
                Browse Files
              </Button>
            </>
          )}
        </div>
      </div>

      {files.length > 0 && (
        <div className="mt-4">
          <p className="text-sm font-medium mb-2">Selected files:</p>
          <ul className="space-y-1">{files}</ul>
        </div>
      )}
    </div>
  )
}