import { Link, useLocation } from 'react-router-dom'
import { cn } from '@/lib/utils'
import {
  Database,
  Users,
  Settings,
  Home,
  Network,
  FileText,
  Search,
  type LucideIcon,
} from 'lucide-react'

type NavItem = {
  name: string
  href: string
  icon: LucideIcon
  disabled?: boolean
  category?: string
}

// 主要导航
const mainNav: NavItem[] = [
  { name: '首页', href: '/', icon: Home },
  { name: '资产目录', href: '/assets', icon: Database },
  { name: '文档管理', href: '/documents', icon: FileText },
  { name: '图谱可视化', href: '/graph', icon: Network },
  { name: '图谱问答', href: '/graph/query', icon: Search },
  { name: '系统设置', href: '/settings', icon: Settings },
]

interface NavSectionProps {
  title: string
  items: NavItem[]
  location: ReturnType<typeof useLocation>
}

function NavSection({ title, items, location }: NavSectionProps) {
  return (
    <div className="mb-6">
      <h3 className="mb-2 px-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {title}
      </h3>
      <ul role="list" className="space-y-1">
        {items.map((item) => {
          const isActive = location.pathname === item.href
          return (
            <li key={item.name}>
              <Link
                to={item.href}
                className={cn(
                  'group flex items-center gap-x-3 rounded-lg px-2 py-2 text-sm font-medium transition-smooth',
                  item.disabled
                    ? 'cursor-not-allowed opacity-50 text-muted-foreground'
                    : isActive
                      ? 'bg-primary text-primary-foreground shadow-md'
                      : 'text-muted-foreground hover:bg-surface-hover hover:text-foreground',
                )}
                aria-disabled={item.disabled}
              >
                <item.icon
                  className={cn(
                    'h-5 w-5 shrink-0 transition-transform group-hover:scale-110',
                    isActive ? 'text-primary-foreground' : 'text-muted-foreground',
                  )}
                />
                {item.name}
              </Link>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

interface SidebarProps {
  className?: string
}

export function Sidebar({ className }: SidebarProps) {
  const location = useLocation()

  return (
    <div
      className={cn(
        'flex h-full flex-col gap-y-6 bg-surface border-r px-4 py-5',
        className,
      )}
    >
      {/* Logo */}
      <div className="flex h-16 shrink-0 items-center px-2">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary shadow-lg">
            <Network className="h-5 w-5 text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-foreground">GraphRAG</h1>
          </div>
        </div>
      </div>

      {/* 导航 */}
      <nav className="flex flex-1 flex-col overflow-y-auto">
        <NavSection title="主要功能" items={mainNav} location={location} />
      </nav>

      {/* 底部信息 */}
      <div className="mt-auto border-t border-border pt-4">
        <div className="rounded-lg bg-surface-elevated p-3">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/20">
              <Users className="h-4 w-4 text-primary" />
            </div>
            <div className="flex-1 overflow-hidden">
              <p className="truncate text-sm font-medium text-foreground">当前用户</p>
              <p className="truncate text-xs text-muted-foreground">在线</p>
            </div>
          </div>
        </div>
        <p className="mt-4 px-2 text-xs text-center text-muted-foreground">
          GraphRAG v1.0.0
        </p>
      </div>
    </div>
  )
}
