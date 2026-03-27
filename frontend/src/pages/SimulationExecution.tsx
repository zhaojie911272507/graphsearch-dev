import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { simulationApi } from '@/lib/api'
import { Play, Pause, StopCircle, Users, GitBranch, Clock, Activity, Plus } from 'lucide-react'

interface SimulationSession {
  id: string
  name: string
  status: 'INITIALIZING' | 'RUNNING' | 'PAUSED' | 'COMPLETED' | 'FAILED'
  agent_count: number
  platforms: string[]
  created_at: string
  current_step: number
  total_steps: number
}

export function SimulationExecution() {
  const queryClient = useQueryClient()
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newSessionName, setNewSessionName] = useState('')
  const [agentCount, setAgentCount] = useState('20')
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(['WECHAT', 'XIAOHONGSHU'])

  const { data: sessionsData, isLoading } = useQuery({
    queryKey: ['simulationSessions'],
    queryFn: () => simulationApi.listSessions().then(res => res.data),
  })

  const createSessionMutation = useMutation({
    mutationFn: (data: { name: string; agent_count: number; platforms: string[] }) =>
      simulationApi.createSession(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['simulationSessions'] })
      setShowCreateForm(false)
      setNewSessionName('')
    },
  })

  const startSessionMutation = useMutation({
    mutationFn: (sessionId: string) => simulationApi.startSession(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['simulationSessions'] })
    },
  })

  const pauseSessionMutation = useMutation({
    mutationFn: (sessionId: string) => simulationApi.pauseSession(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['simulationSessions'] })
    },
  })

  const stopSessionMutation = useMutation({
    mutationFn: (sessionId: string) => simulationApi.stopSession(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['simulationSessions'] })
    },
  })

  const sessions: SimulationSession[] = sessionsData?.sessions || []

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'RUNNING': return 'default'
      case 'PAUSED': return 'secondary'
      case 'COMPLETED': return 'success'
      case 'FAILED': return 'destructive'
      case 'INITIALIZING': return 'info'
      default: return 'outline'
    }
  }

  const togglePlatform = (platform: string) => {
    setSelectedPlatforms(prev =>
      prev.includes(platform)
        ? prev.filter(p => p !== platform)
        : [...prev, platform]
    )
  }

  const handleCreateSession = () => {
    createSessionMutation.mutate({
      name: newSessionName || '新模拟会话',
      agent_count: parseInt(agentCount),
      platforms: [...selectedPlatforms],
    })
  }

  const handleStartSession = (id: string) => {
    startSessionMutation.mutate(id)
  }

  const handlePauseSession = (id: string) => {
    pauseSessionMutation.mutate(id)
  }

  const handleStopSession = (id: string) => {
    stopSessionMutation.mutate(id)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">模拟执行</h1>
          <p className="text-muted-foreground mt-1">管理和控制社会模拟会话</p>
        </div>
        <Button onClick={() => setShowCreateForm(true)}>
          <Plus className="h-4 w-4 mr-2" />
          创建会话
        </Button>
      </div>

      {/* 创建新会话 */}
      {showCreateForm && (
        <Card>
          <CardHeader>
            <CardTitle>创建新模拟会话</CardTitle>
            <CardDescription>配置模拟参数并启动新的社会模拟</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="session-name">会话名称</Label>
                <Input
                  id="session-name"
                  placeholder="输入会话名称..."
                  value={newSessionName}
                  onChange={(e) => setNewSessionName(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="agent-count">Agent 数量</Label>
                <Input
                  id="agent-count"
                  type="number"
                  min="1"
                  max="100"
                  value={agentCount}
                  onChange={(e) => setAgentCount(e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>选择平台</Label>
              <div className="flex gap-2">
                <Button
                  variant={selectedPlatforms.includes('WECHAT') ? 'default' : 'outline'}
                  onClick={() => togglePlatform('WECHAT')}
                  className="flex-1"
                >
                  <GitBranch className="h-4 w-4 mr-2" />
                  微信
                </Button>
                <Button
                  variant={selectedPlatforms.includes('XIAOHONGSHU') ? 'default' : 'outline'}
                  onClick={() => togglePlatform('XIAOHONGSHU')}
                  className="flex-1"
                >
                  <GitBranch className="h-4 w-4 mr-2" />
                  小红书
                </Button>
              </div>
            </div>

            <div className="flex gap-2">
              <Button onClick={handleCreateSession} disabled={createSessionMutation.isPending}>
                {createSessionMutation.isPending ? '创建中...' : '创建会话'}
              </Button>
              <Button variant="outline" onClick={() => setShowCreateForm(false)}>
                取消
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 会话列表 */}
      {isLoading ? (
        <div className="text-center py-12">加载会话列表...</div>
      ) : sessions.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Activity className="h-16 w-16 text-muted-foreground mb-4" />
            <p className="text-lg font-medium">暂无模拟会话</p>
            <p className="text-muted-foreground">创建第一个模拟会话开始社会模拟实验</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {sessions.map((session) => (
            <Card key={session.id} className="relative overflow-hidden">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">{session.name}</CardTitle>
                  <Badge variant={getStatusBadgeVariant(session.status)}>
                    {session.status}
                  </Badge>
                </div>
                <CardDescription className="flex items-center gap-4 text-xs">
                  <span className="flex items-center gap-1">
                    <Users className="h-3 w-3" />
                    {session.agent_count} Agents
                  </span>
                  <span className="flex items-center gap-1">
                    <GitBranch className="h-3 w-3" />
                    {session.platforms.join(', ')}
                  </span>
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="flex items-center gap-1 text-muted-foreground">
                      <Clock className="h-3 w-3" />
                      进度
                    </span>
                    <span className="text-muted-foreground">
                      {session.current_step} / {session.total_steps}
                    </span>
                  </div>
                  <div className="h-2 w-full bg-secondary rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary transition-all duration-300"
                      style={{ width: `${(session.current_step / session.total_steps) * 100}%` }}
                    />
                  </div>
                </div>

                <div className="flex gap-2">
                  {session.status === 'RUNNING' && (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handlePauseSession(session.id)}
                      disabled={pauseSessionMutation.isPending}
                      className="flex-1"
                    >
                      <Pause className="h-3 w-3 mr-1" />
                      暂停
                    </Button>
                  )}
                  {session.status === 'PAUSED' && (
                    <Button
                      size="sm"
                      onClick={() => handleStartSession(session.id)}
                      disabled={startSessionMutation.isPending}
                      className="flex-1"
                    >
                      <Play className="h-3 w-3 mr-1" />
                      继续
                    </Button>
                  )}
                  {session.status === 'INITIALIZING' && (
                    <Button
                      size="sm"
                      onClick={() => handleStartSession(session.id)}
                      disabled={startSessionMutation.isPending}
                      className="flex-1"
                    >
                      <Play className="h-3 w-3 mr-1" />
                      启动
                    </Button>
                  )}
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => handleStopSession(session.id)}
                    disabled={stopSessionMutation.isPending}
                    className="flex-1"
                  >
                    <StopCircle className="h-3 w-3 mr-1" />
                    停止
                  </Button>
                </div>

                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>创建时间：{new Date(session.created_at).toLocaleString('zh-CN')}</span>
                  <span>ID: {session.id.slice(0, 8)}...</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
