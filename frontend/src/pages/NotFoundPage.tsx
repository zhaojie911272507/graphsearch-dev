import { Link } from 'react-router-dom'
import { buttonVariants } from '@/components/ui/Button'
import { cn } from '@/lib/utils'

export function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <h1 className="text-2xl font-semibold text-foreground">页面不存在</h1>
      <p className="mt-2 text-sm text-muted-foreground">该路径没有对应功能，请从左侧菜单进入。</p>
      <Link to="/" className={cn(buttonVariants(), 'mt-6')}>
        返回首页
      </Link>
    </div>
  )
}
