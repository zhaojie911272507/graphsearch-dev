import { Link } from 'react-router-dom'
import { buttonVariants } from '@/components/ui/Button'
import { cn } from '@/lib/utils'

export function LineageIndex() {
  return (
    <div className="space-y-4">
      <h1 className="text-3xl font-bold">血缘追踪</h1>
      <p className="text-muted-foreground max-w-lg">
        血缘视图需要指定节点。请先在「资产目录」中打开某个节点，再从节点详情进入血缘。
      </p>
      <Link to="/assets" className={cn(buttonVariants())}>
        前往资产目录
      </Link>
    </div>
  )
}
