import { Bell, Search, User } from 'lucide-react'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'

export function Header() {
  return (
    <header className="flex h-16 shrink-0 items-center gap-x-4 border-b bg-card px-6">
      <div className="flex flex-1 gap-x-4 self-stretch lg:gap-x-6">
        <div className="relative w-full max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="search"
            placeholder="搜索实体、文档、概念..."
            className="pl-10"
          />
        </div>
        <div className="flex items-center gap-x-4 lg:gap-x-6 ml-auto">
          <Button variant="ghost" size="icon">
            <Bell className="h-5 w-5" />
          </Button>
          <div className="flex items-center gap-x-2">
            <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center">
              <User className="h-4 w-4 text-primary-foreground" />
            </div>
            <span className="text-sm font-medium">当前用户</span>
          </div>
        </div>
      </div>
    </header>
  )
}
