import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { BarChart3, TrendingUp, Users, GitBranch, FileText, Download, RefreshCw } from 'lucide-react'

interface Report {
  id: string
  sessionId: string
  sessionName: string
  type: 'DAILY_SUMMARY' | 'WEEKLY_ANALYSIS' | 'INTERACTION_ANALYSIS' | 'MEMORY_EVOLUTION' | 'NETWORK_ANALYSIS'
  generatedAt: string
  summary: string
  status: 'completed' | 'generating' | 'failed'
}

const mockReports: Report[] = [
  {
    id: 'report-001',
    sessionId: 'sim-001',
    sessionName: '社交媒体模拟 - 微信 + 小红书',
    type: 'DAILY_SUMMARY',
    generatedAt: '2026-03-27 12:00',
    summary: '本次模拟共产生 1,245 次交互，活跃 Agent 数量 18/20，热门话题集中在 AI 技术发展、社交媒体趋势等领域。',
    status: 'completed',
  },
  {
    id: 'report-002',
    sessionId: 'sim-001',
    sessionName: '社交媒体模拟 - 微信 + 小红书',
    type: 'NETWORK_ANALYSIS',
    generatedAt: '2026-03-27 11:00',
    summary: '社交网络分析显示形成了 3 个主要社群，中心度最高的 Agent 为用户_007 和用户_015。',
    status: 'completed',
  },
  {
    id: 'report-003',
    sessionId: 'sim-002',
    sessionName: '社群互动模拟',
    type: 'WEEKLY_ANALYSIS',
    generatedAt: '2026-03-26 18:00',
    summary: '周度分析显示用户参与度呈上升趋势，峰值出现在第 3 天和第 5 天。',
    status: 'completed',
  },
]

const reportTypeLabels: Record<Report['type'], string> = {
  DAILY_SUMMARY: '每日摘要',
  WEEKLY_ANALYSIS: '每周分析',
  INTERACTION_ANALYSIS: '交互分析',
  MEMORY_EVOLUTION: '记忆演化',
  NETWORK_ANALYSIS: '网络分析',
}

const reportTypeIcons: Record<Report['type'], React.ElementType> = {
  DAILY_SUMMARY: FileText,
  WEEKLY_ANALYSIS: BarChart3,
  INTERACTION_ANALYSIS: TrendingUp,
  MEMORY_EVOLUTION: GitBranch,
  NETWORK_ANALYSIS: Users,
}

export function SimulationReports() {
  const [reports] = useState<Report[]>(mockReports)
  const [selectedType, setSelectedType] = useState<string>('all')

  const filteredReports = selectedType === 'all'
    ? reports
    : reports.filter(r => r.type === selectedType)

  const handleGenerateReport = () => {
    // TODO: 调用 API 生成报告
    console.log('生成报告...')
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">报告分析</h1>
          <p className="text-muted-foreground mt-1">查看和分析社会模拟生成的报告</p>
        </div>
        <Button onClick={handleGenerateReport}>
          <RefreshCw className="h-4 w-4 mr-2" />
          生成报告
        </Button>
      </div>

      {/* 统计卡片 */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总报告数</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{reports.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">已完成</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {reports.filter(r => r.status === 'completed').length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">活跃会话</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">2</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总交互数</CardTitle>
            <GitBranch className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">1,245</div>
          </CardContent>
        </Card>
      </div>

      {/* 报告列表 */}
      <Tabs defaultValue="all" className="space-y-4">
        <div className="flex items-center justify-between">
          <TabsList>
            <TabsTrigger value="all">全部</TabsTrigger>
            <TabsTrigger value="DAILY_SUMMARY">每日摘要</TabsTrigger>
            <TabsTrigger value="WEEKLY_ANALYSIS">每周分析</TabsTrigger>
            <TabsTrigger value="NETWORK_ANALYSIS">网络分析</TabsTrigger>
          </TabsList>
          <Select value={selectedType} onValueChange={setSelectedType}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="排序方式" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部类型</SelectItem>
              <SelectItem value="DAILY_SUMMARY">每日摘要</SelectItem>
              <SelectItem value="WEEKLY_ANALYSIS">每周分析</SelectItem>
              <SelectItem value="INTERACTION_ANALYSIS">交互分析</SelectItem>
              <SelectItem value="MEMORY_EVOLUTION">记忆演化</SelectItem>
              <SelectItem value="NETWORK_ANALYSIS">网络分析</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <TabsContent value="all" className="space-y-4">
          {filteredReports.map((report) => {
            const Icon = reportTypeIcons[report.type]
            return (
              <Card key={report.id}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                        <Icon className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <CardTitle className="text-lg">{report.sessionName}</CardTitle>
                        <CardDescription className="flex items-center gap-2">
                          <Badge variant="secondary" className="text-xs">
                            {reportTypeLabels[report.type]}
                          </Badge>
                          <span className="text-xs text-muted-foreground">
                            {report.generatedAt}
                          </span>
                        </CardDescription>
                      </div>
                    </div>
                    <Button variant="outline" size="sm">
                      <Download className="h-3 w-3 mr-2" />
                      导出
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{report.summary}</p>
                  <div className="mt-4 flex gap-2">
                    <Button variant="default" size="sm">查看详情</Button>
                    <Button variant="ghost" size="sm">分析图表</Button>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </TabsContent>
      </Tabs>
    </div>
  )
}
