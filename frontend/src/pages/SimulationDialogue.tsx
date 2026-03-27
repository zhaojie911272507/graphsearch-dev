import { useState, useRef, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
import { ScrollArea } from '@/components/ui/ScrollArea'
import { Send, Users, Bot } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Agent {
  id: string
  name: string
  avatar: string
  status: 'active' | 'idle' | 'busy'
  personality: string
}

interface Message {
  id: string
  senderId: string
  senderName: string
  senderAvatar: string
  content: string
  timestamp: string
  isUser: boolean
}

const mockAgents: Agent[] = [
  {
    id: 'agent-001',
    name: '小明',
    avatar: 'M',
    status: 'active',
    personality: '外向、热情、喜欢分享',
  },
  {
    id: 'agent-002',
    name: '小红',
    avatar: 'F',
    status: 'idle',
    personality: '内向、思考型、善于分析',
  },
  {
    id: 'agent-003',
    name: '小刚',
    avatar: 'M',
    status: 'busy',
    personality: '直率、行动派、喜欢挑战',
  },
]

const mockMessages: Message[] = [
  {
    id: 'msg-001',
    senderId: 'agent-001',
    senderName: '小明',
    senderAvatar: 'M',
    content: '你好！很高兴见到你。今天想聊些什么呢？',
    timestamp: '10:30',
    isUser: false,
  },
  {
    id: 'msg-002',
    senderId: 'user',
    senderName: '你',
    senderAvatar: 'U',
    content: '你好，小明！我想知道你对最近 AI 发展的看法？',
    timestamp: '10:31',
    isUser: true,
  },
  {
    id: 'msg-003',
    senderId: 'agent-001',
    senderName: '小明',
    senderAvatar: 'M',
    content: '哇，AI 真的是太酷了！我觉得它会彻底改变我们的生活方式。特别是在创意领域，AI 可以帮助人类做很多以前做不到的事情。不过我也担心就业问题，你觉得呢？',
    timestamp: '10:32',
    isUser: false,
  },
]

export function SimulationDialogue() {
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(mockAgents[0])
  const [messages, setMessages] = useState<Message[]>(mockMessages)
  const [inputMessage, setInputMessage] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSendMessage = () => {
    if (!inputMessage.trim() || !selectedAgent) return

    const newUserMessage: Message = {
      id: `msg-${Date.now()}`,
      senderId: 'user',
      senderName: '你',
      senderAvatar: 'U',
      content: inputMessage,
      timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
      isUser: true,
    }

    setMessages([...messages, newUserMessage])
    setInputMessage('')
    setIsTyping(true)

    // 模拟 Agent 回复
    setTimeout(() => {
      const agentResponse: Message = {
        id: `msg-${Date.now() + 1}`,
        senderId: selectedAgent.id,
        senderName: selectedAgent.name,
        senderAvatar: selectedAgent.avatar,
        content: `这是一个模拟回复。我 (${selectedAgent.name}) 收到了你的消息："${inputMessage}"。根据我的人设"${selectedAgent.personality}"，我会这样回应...`,
        timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
        isUser: false,
      }
      setMessages(prev => [...prev, agentResponse])
      setIsTyping(false)
    }, 1500)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const getStatusColor = (status: Agent['status']) => {
    switch (status) {
      case 'active': return 'bg-success'
      case 'idle': return 'bg-warning'
      case 'busy': return 'bg-error'
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">深度对话</h1>
          <p className="text-muted-foreground mt-1">与模拟世界中的 Agent 进行自然对话</p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-4">
        {/* Agent 列表 */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              选择 Agent
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {mockAgents.map((agent) => (
                <button
                  key={agent.id}
                  onClick={() => setSelectedAgent(agent)}
                  className={cn(
                    'flex w-full items-center gap-3 rounded-lg p-3 text-left transition-colors',
                    selectedAgent?.id === agent.id
                      ? 'bg-primary text-primary-foreground'
                      : 'hover:bg-secondary'
                  )}
                >
                  <div className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/20">
                    {agent.avatar}
                    <div
                      className={cn(
                        'absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-background',
                        getStatusColor(agent.status)
                      )}
                    />
                  </div>
                  <div className="flex-1 overflow-hidden">
                    <p className="truncate text-sm font-medium">{agent.name}</p>
                    <p className={cn(
                      'truncate text-xs',
                      selectedAgent?.id === agent.id ? 'text-primary-foreground/70' : 'text-muted-foreground'
                    )}>
                      {agent.personality.slice(0, 10)}...
                    </p>
                  </div>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* 聊天窗口 */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {selectedAgent && (
                  <>
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/20">
                      {selectedAgent.avatar}
                    </div>
                    <div>
                      <CardTitle>{selectedAgent.name}</CardTitle>
                      <p className="text-sm text-muted-foreground">{selectedAgent.personality}</p>
                    </div>
                  </>
                )}
              </div>
              <div className="flex gap-2">
                <Badge variant={selectedAgent?.status === 'active' ? 'success' : 'secondary'}>
                  {selectedAgent?.status === 'active' ? '在线' : selectedAgent?.status === 'idle' ? '空闲' : '忙碌'}
                </Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent className="flex flex-col h-[500px]">
            <ScrollArea className="flex-1 pr-4">
              <div className="space-y-4">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={cn(
                      'flex items-start gap-3',
                      message.isUser ? 'flex-row-reverse' : ''
                    )}
                  >
                    <div
                      className={cn(
                        'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
                        message.isUser ? 'bg-primary text-primary-foreground' : 'bg-secondary text-secondary-foreground'
                      )}
                    >
                      {message.senderAvatar}
                    </div>
                    <div
                      className={cn(
                        'max-w-[70%] rounded-lg p-3',
                        message.isUser ? 'bg-primary text-primary-foreground' : 'bg-secondary'
                      )}
                    >
                      <p className="text-sm">{message.content}</p>
                      <p className={cn(
                        'mt-1 text-xs',
                        message.isUser ? 'text-primary-foreground/70' : 'text-muted-foreground'
                      )}>
                        {message.timestamp}
                      </p>
                    </div>
                  </div>
                ))}
                {isTyping && (
                  <div className="flex items-start gap-3">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary">
                      <Bot className="h-4 w-4" />
                    </div>
                    <div className="rounded-lg bg-secondary p-3">
                      <div className="flex gap-1">
                        <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground" />
                        <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:0.2s]" />
                        <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:0.4s]" />
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            </ScrollArea>

            <div className="mt-4 flex gap-2">
              <Input
                placeholder="输入消息..."
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                disabled={!selectedAgent}
              />
              <Button
                size="icon"
                onClick={handleSendMessage}
                disabled={!selectedAgent || !inputMessage.trim()}
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
