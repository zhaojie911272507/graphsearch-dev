import { Component, type ErrorInfo, type ReactNode } from 'react'
import { buttonVariants } from '@/components/ui/Button'
import { cn } from '@/lib/utils'

interface Props {
  children: ReactNode
}

interface State {
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  override componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('React render error:', error, info.componentStack)
  }

  override render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4 text-center text-foreground">
          <h1 className="text-xl font-semibold">页面加载出错</h1>
          <p className="mt-2 max-w-md text-sm text-muted-foreground break-words">
            {this.state.error.message}
          </p>
          <button
            type="button"
            className={cn(buttonVariants(), 'mt-6')}
            onClick={() => window.location.reload()}
          >
            刷新重试
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
