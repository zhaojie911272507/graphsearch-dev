import { Link, useLocation } from 'react-router-dom'
import { cn } from '@/lib/utils'
import {
  Database,
  GitBranch,
  Users,
  Map,
  BarChart3,
  Settings,
  Home,
  Network,
  GitCommitHorizontal,
} from 'lucide-react'

const navigation = [
  { name: '首页', href: '/', icon: Home },
  { name: '资产目录', href: '/assets', icon: Database },
  { name: '图谱可视化', href: '/graph', icon: Network },
  { name: '本体管理', href: '/ontology', icon: GitBranch },
  { name: '协作审核', href: '/review', icon: Users },
  { name: '探索路径', href: '/explorations', icon: Map },
  { name: '血缘追踪', href: '/lineage', icon: GitCommitHorizontal, disabled: true },
  { name: '评估监控', href: '/evaluation', icon: BarChart3 },
  { name: '系统设置', href: '/settings', icon: Settings },
]

interface SidebarProps {
  className?: string
}

export function Sidebar({ className }: SidebarProps) {
  const location = useLocation()

  return (
    <div className={cn("flex h-full flex-col gap-y-5 bg-card border-r px-4 py-4", className)}>
      <div className="flex h-16 shrink-0 items-center">
        <h1 className="text-xl font-bold text-foreground">GraphRAG</h1>
      </div>
      <nav className="flex flex-1 flex-col">
        <ul role="list" className="flex flex-1 flex-col gap-y-7">
          <li>
            <ul role="list" className="-mx-2 space-y-1">
              {navigation.map((item) => {
                const isActive = location.pathname === item.href
                return (
                  <li key={item.name}>
                    <Link
                      to={item.href}
                      className={cn(
                        'group flex gap-x-3 rounded-md p-2 text-sm leading-6 font-semibold',
                        item.disabled
                          ? 'text-muted-foreground cursor-not-allowed opacity-50'
                          : isActive
                          ? 'bg-primary text-primary-foreground'
                          : 'text-muted-foreground hover:text-foreground hover:bg-secondary'
                      )}
                    >
                      <item.icon className="h-6 w-6 shrink-0" />
                      {item.name}
                    </Link>
                  </li>
                )
              })}
            </ul>
          </li>
        </ul>
      </nav>
    </div>
  )
}
