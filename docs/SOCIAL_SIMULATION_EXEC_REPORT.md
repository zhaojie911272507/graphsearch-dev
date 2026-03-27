# 社会模拟系统 - 模拟执行与报告生成模块实现文档

## 概述

本文档描述了社会模拟系统的模拟执行和报告生成模块。基于已完成的环境搭建模块，本模块实现了：
1. **模拟执行** - 双平台并行模拟、时序记忆更新、需求预测解析
2. **报告生成** - ReportAgent 及深度交互功能
3. **深度互动** - 与模拟世界中任意 Agent 对话

## 新增功能

### 1. 领域模型扩展 (`app/domain/social/`)

#### 新增枚举类型 (`enums.py`)

```python
# 交互类型
class InteractionType(StrEnum):
    POST = "POST"              # 发布内容
    COMMENT = "COMMENT"        # 评论
    LIKE = "LIKE"              # 点赞
    SHARE = "SHARE"            # 分享
    MESSAGE = "MESSAGE"        # 私信
    FOLLOW = "FOLLOW"          # 关注
    UNFOLLOW = "UNFOLLOW"      # 取消关注
    # ...

# 报告类型
class ReportType(StrEnum):
    DAILY_SUMMARY = "DAILY_SUMMARY"          # 每日摘要
    WEEKLY_ANALYSIS = "WEEKLY_ANALYSIS"      # 每周分析
    INTERACTION_ANALYSIS = "INTERACTION_ANALYSIS"  # 交互分析
    MEMORY_EVOLUTION = "MEMORY_EVOLUTION"    # 记忆演化
    NETWORK_ANALYSIS = "NETWORK_ANALYSIS"    # 网络分析
    # ...

# 需求类型
class NeedType(StrEnum):
    SOCIAL_CONNECTION = "SOCIAL_CONNECTION"  # 社交需求
    INFORMATION = "INFORMATION"              # 信息需求
    ENTERTAINMENT = "ENTERTAINMENT"          # 娱乐需求
    SELF_EXPRESSION = "SELF_EXPRESSION"      # 自我表达
    RECOGNITION = "RECOGNITION"              # 认可需求
```

#### 新增节点类型 (`nodes.py`)

**InteractionNode** - 交互记录节点
```python
@dataclass
class InteractionNode(BaseNode):
    interaction_type: str      # POST/COMMENT/LIKE 等
    content: str               # 交互内容
    sender_id: UUID            # 发送者 ID
    receiver_id: UUID | None   # 接收者 ID（如果有）
    timestamp: datetime
    interaction_metadata: dict
```

**ReportNode** - 报告节点
```python
@dataclass
class ReportNode(BaseNode):
    report_type: str           # 报告类型
    session_id: UUID           # 关联的会话 ID
    content: dict              # 报告内容数据
    summary: str               # 自然语言摘要
    time_range_start: datetime
    time_range_end: datetime
```

### 2. 模拟执行服务 (`app/services/simulation_execution.py`)

#### SimulationEngine - 模拟执行引擎

核心执行引擎，负责：
- 启动/暂停/停止模拟会话
- 执行单步模拟
- 协调各组件工作

```python
class SimulationEngine:
    async def start_simulation(session_id: UUID) -> bool
    async def pause_simulation(session_id: UUID) -> bool
    async def stop_simulation(session_id: UUID) -> bool
    async def run_simulation_step(...) -> SimulationStepResult
```

#### DualPlatformScheduler - 双平台调度器

实现双平台并行执行：

```python
class DualPlatformScheduler:
    async def execute_platform_step(
        platform: PlatformType,
        agents: list[AgentNode],
        world_state: WorldStateNode,
        config: PlatformConfig
    ) -> PlatformStepResult
```

**并行执行流程**:
```
1. 为每个平台创建执行任务
2. 使用 asyncio.gather 并行执行
3. 收集各平台结果
4. 应用记忆衰减
5. 返回综合结果
```

#### InteractionEngine - 交互引擎

生成和执行 Agent 交互：

```python
class InteractionEngine:
    async def generate_interactions(
        agent: AgentNode,
        candidates: list[AgentNode],
        platform: PlatformType,
        config: PlatformConfig
    ) -> list[Interaction]

    async def execute_interaction(
        interaction: Interaction,
        world_state: WorldStateNode
    ) -> InteractionResult
```

**交互生成策略**:
- 基于人格特质决定交互倾向
- 使用 LLM 生成自然的交互内容
- 考虑平台特性（微信 vs 小红书）

#### MemoryManager - 记忆管理器

管理时序记忆：

```python
class MemoryManager:
    async def add_memory(
        agent_id: UUID,
        content: str,
        memory_type: MemoryType,
        emotion_tags: list[EmotionType],
        importance: float
    ) -> MemoryNode

    async def decay_memories(
        agent_id: UUID,
        decay_rate: float
    ) -> list[MemoryNode]

    async def retrieve_relevant_memories(
        agent_id: UUID,
        context: str,
        top_k: int
    ) -> list[MemoryNode]
```

**记忆衰减模型**:
```
新记忆重要性 = 基础重要性
每次查询后：重要性 *= (1 - decay_rate)
重要性 < 阈值：记忆被"遗忘"
```

#### DemandPredictor - 需求预测器

分析 Agent 需求和预测趋势：

```python
class DemandPredictor:
    async def analyze_agent_needs(
        agent: AgentNode,
        recent_interactions: list
    ) -> list[AgentNeed]

    async def predict_trending_topics(
        platform: PlatformType,
        interactions: list[Interaction],
        time_window: timedelta
    ) -> list[TrendingTopic]
```

**需求分析逻辑**:
- 外向性高 → 强社交需求
- 开放性高 → 信息需求强
- 基于近期交互调整需求强度

### 3. 报告生成服务 (`app/services/report_generation.py`)

#### ReportAgent - 报告生成 Agent

生成各类分析报告：

```python
class ReportAgent:
    async def generate_simulation_report(
        session_id: UUID,
        report_type: ReportType,
        time_range: tuple[datetime, datetime]
    ) -> SimulationReport

    async def generate_agent_analysis(
        agent_id: UUID
    ) -> AgentAnalysisReport

    async def generate_world_state_report(
        world_id: UUID
    ) -> dict

    async def generate_network_analysis(
        session_id: UUID
    ) -> NetworkMetrics
```

**报告数据结构**:
```python
@dataclass
class SimulationReport:
    session_id: UUID
    report_type: ReportType
    generated_at: datetime
    time_range: tuple[datetime, datetime]

    # 统计数据
    total_agents: int
    total_interactions: int
    total_memories: int
    platform_stats: dict[PlatformType, PlatformStatistics]

    # 分析结果
    key_events: list[KeyEvent]
    trending_topics: list[TrendingTopic]
    network_metrics: NetworkMetrics
    memory_evolution: MemoryEvolutionStats

    # 自然语言摘要
    executive_summary: str
    detailed_analysis: str
    recommendations: list[str]
```

### 4. 深度交互服务 (`app/services/interactive_dialogue.py`)

#### DialogueManager - 对话管理器

管理用户与 Agent 的对话：

```python
class DialogueManager:
    async def start_conversation(
        user_id: str,
        agent_id: UUID
    ) -> ConversationSession

    async def process_user_message(
        conversation_id: str,
        message: str
    ) -> AgentResponse

    async def get_conversation_history(
        conversation_id: str
    ) -> list[Message]
```

#### AgentChat - Agent 聊天引擎

基于 LLM 的 Agent 响应生成：

```python
class AgentChat:
    def get_agent_voice(self, agent: AgentNode) -> AgentVoiceProfile

    async def generate_response(
        agent: AgentNode,
        user_message: str,
        conversation_history: list[Message],
        retrieved_memories: list[MemoryNode]
    ) -> AgentResponse
```

**Agent 声音特征**:
```python
@dataclass
class AgentVoiceProfile:
    tone: str           # friendly/formal/casual/enthusiastic
    formality: float    # 0.0-1.0
    verbosity: float    # 0.0-1.0
    emoji_usage: bool
    catchphrases: list[str]
```

**响应生成流程**:
1. 根据人格提取声音特征
2. 构建系统提示（角色设定）
3. 添加对话历史和相关记忆
4. 调用 LLM 生成响应
5. 检测情绪和建议动作

### 5. API 路由

#### 模拟执行 API (`/api/v1/simulation/`)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/sessions/{id}/start` | POST | 启动模拟 |
| `/sessions/{id}/pause` | POST | 暂停模拟 |
| `/sessions/{id}/stop` | POST | 停止模拟 |
| `/sessions/{id}/step` | POST | 执行单步 |
| `/sessions/{id}/status` | GET | 获取状态 |
| `/sessions/{id}/metrics` | GET | 获取指标 |
| `/sessions/{id}/agents` | GET | 获取 Agent 列表 |
| `/sessions/{id}/memory/decay` | POST | 应用记忆衰减 |

#### 报告生成 API (`/api/v1/simulation/reports/`)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/generate` | POST | 生成报告 |
| `/{report_id}` | GET | 获取报告 |
| `/session/{session_id}` | GET | 获取会话报告列表 |
| `/agents/{agent_id}/analysis` | GET | Agent 分析 |
| `/world/{world_id}/state` | GET | 世界状态 |
| `/session/{session_id}/network` | GET | 网络分析 |

#### 深度交互 API (`/api/v1/simulation/dialogue/`)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/start` | POST | 开始对话 |
| `/message` | POST | 发送消息 |
| `/{conversation_id}/history` | GET | 获取历史 |
| `/user/{user_id}/sessions` | GET | 用户会话列表 |
| `/agents/{agent_id}/chat` | POST | 直接聊天 |

## 使用示例

### 1. 启动模拟并执行步骤

```python
from app.services.simulation_execution import SimulationEngine
from app.config import get_settings

settings = get_settings()
engine = SimulationEngine(settings.openai, graph_store)

# 启动模拟
await engine.start_simulation(session_id)

# 执行 10 步
for i in range(10):
    result = await engine.run_simulation_step(
        session_id=session_id,
        agents=agents,
        worlds=worlds,
        platform_configs=configs,
    )
    print(f"Step {i+1}: {result.total_interactions} interactions")
```

### 2. 生成模拟报告

```python
from app.services.report_generation import ReportAgent
from app.domain.social.enums import ReportType

report_agent = ReportAgent(settings.openai, graph_store)

# 生成每日摘要
report = await report_agent.generate_simulation_report(
    session_id=session_id,
    report_type=ReportType.DAILY_SUMMARY,
    time_range=(start_time, end_time),
)

print(report.executive_summary)
```

### 3. 与 Agent 对话

```python
from app.services.interactive_dialogue import DialogueManager

dialogue = DialogueManager(settings.openai, graph_store)

# 开始对话
session = await dialogue.start_conversation(
    user_id="user_123",
    agent_id=agent_id,
)

# 发送消息
response = await dialogue.process_user_message(
    conversation_id=session.id,
    message="你好，今天过得怎么样？",
)

print(f"Agent: {response.message}")
print(f"Emotion: {response.emotion}")
```

### 4. API 调用示例

```bash
# 启动模拟
curl -X POST http://localhost:8000/api/v1/simulation/sessions/{id}/start

# 执行单步
curl -X POST http://localhost:8000/api/v1/simulation/sessions/{id}/step?step_count=1

# 生成报告
curl -X POST "http://localhost:8000/api/v1/simulation/reports/generate?session_id={id}&report_type=DAILY_SUMMARY"

# 与 Agent 对话
curl -X POST "http://localhost:8000/api/v1/simulation/dialogue/agents/{agent_id}/chat?user_id=user1" \
  -H "Content-Type: application/json" \
  -d '{"message": "你好！"}'
```

## 测试

### 运行测试

```bash
# 运行所有模拟相关测试
pytest tests/test_simulation_setup.py tests/test_simulation_exec_report.py -v

# 运行执行和报告测试
pytest tests/test_simulation_exec_report.py -v
```

### 测试结果

```
tests/test_simulation_exec_report.py::TestInteraction::test_interaction_creation PASSED
tests/test_simulation_exec_report.py::TestInteractionEngine::test_engine_initialization PASSED
tests/test_simulation_exec_report.py::TestMemoryManager::test_memory_manager_initialization PASSED
tests/test_simulation_exec_report.py::TestDemandPredictor::test_predictor_initialization PASSED
tests/test_simulation_exec_report.py::TestReportAgent::test_report_agent_initialization PASSED
tests/test_simulation_exec_report.py::TestReportAgent::test_simulation_report_creation PASSED
tests/test_simulation_exec_report.py::TestAgentChat::test_agent_chat_initialization PASSED
tests/test_simulation_exec_report.py::TestAgentChat::test_get_agent_voice PASSED
tests/test_simulation_exec_report.py::TestConversationSession::test_conversation_session_creation PASSED
tests/test_simulation_exec_report.py::TestConversationSession::test_add_message PASSED
tests/test_simulation_exec_report.py::TestConversationSession::test_get_recent_messages PASSED
tests/test_simulation_exec_report.py::TestDialogueManager::test_dialogue_manager_initialization PASSED
tests/test_simulation_exec_report.py::TestInteractionNode::test_interaction_node_creation PASSED
tests/test_simulation_exec_report.py::TestInteractionNode::test_interaction_node_serialization PASSED
tests/test_simulation_exec_report.py::TestReportNode::test_report_node_creation PASSED
tests/test_simulation_exec_report.py::TestReportNode::test_report_node_serialization PASSED
tests/test_simulation_exec_report.py::TestSimulationEngine::test_simulation_engine_initialization PASSED

============================== 17 passed
```

## 文件结构

```
app/
├── domain/social/
│   ├── enums.py                  # 新增：InteractionType, ReportType, NeedType
│   ├── nodes.py                  # 新增：InteractionNode, ReportNode
│   └── __init__.py               # 更新导出
├── services/
│   ├── simulation_execution.py   # 模拟执行核心服务
│   ├── report_generation.py      # 报告生成服务
│   └── interactive_dialogue.py   # 深度交互服务
├── api/
│   ├── routes/
│   │   ├── simulation_exec.py    # 模拟执行 API
│   │   ├── simulation_report.py  # 报告生成 API
│   │   ├── simulation_dialogue.py # 深度交互 API
│   │   └── __init__.py           # 更新导入
│   └── schemas/
│       └── simulation.py         # 更新：导入 ReportType
├── main.py                       # 注册新路由
└── config.py                     # (已有 SimulationSettings)

tests/
└── test_simulation_exec_report.py  # 新增测试

docs/
└── SOCIAL_SIMULATION_EXEC_REPORT.md  # 本文档
```

## 架构概览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        模拟执行模块                                      │
├─────────────────────────────────────────────────────────────────────────┤
│  SimulationEngine                                                       │
│  ├── DualPlatformScheduler (双平台并行)                                 │
│  │   ├── Platform WECHAT: execute_platform_step()                       │
│  │   └── Platform XIAOHONGSHU: execute_platform_step()                  │
│  ├── InteractionEngine (交互生成与执行)                                 │
│  │   ├── generate_interactions() - LLM 驱动                             │
│  │   └── execute_interaction() - 创建节点/记忆                          │
│  ├── MemoryManager (时序记忆管理)                                       │
│  │   ├── add_memory()                                                   │
│  │   ├── decay_memories() - 指数衰减模型                               │
│  │   └── retrieve_relevant_memories()                                   │
│  └── DemandPredictor (需求预测)                                         │
│      ├── analyze_agent_needs() - 基于人格                              │
│      └── predict_trending_topics() - 词频分析                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                        报告生成模块                                      │
├─────────────────────────────────────────────────────────────────────────┤
│  ReportAgent                                                            │
│  ├── generate_simulation_report()                                       │
│  │   ├── 收集统计数据 (agents/interactions/memories)                    │
│  │   ├── 平台分析 (WECHAT/XIAOHONGSHU)                                  │
│  │   ├── 网络分析 (度分布/聚类系数/中心性)                              │
│  │   └── LLM 生成自然语言摘要                                            │
│  ├── generate_agent_analysis()                                          │
│  │   ├── 活动统计                                                       │
│  │   └── 行为模式分析                                                   │
│  └── generate_network_analysis()                                        │
│      └── 图算法计算网络指标                                             │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                        深度交互模块                                      │
├─────────────────────────────────────────────────────────────────────────┤
│  DialogueManager                                                        │
│  ├── 会话管理 (start/process/history)                                   │
│  └── 上下文维护                                                         │
│                                                                         │
│  AgentChat                                                              │
│  ├── get_agent_voice() - 从人格提取声音特征                            │
│  ├── generate_response() - LLM 生成响应                                 │
│  │   ├── 系统提示：角色设定 + 人格                                      │
│  │   ├── 对话历史                                                       │
│  │   ├── 相关记忆                                                       │
│  │   └── 情绪检测 + 建议动作                                            │
│  └── AgentVoiceProfile (tone/formality/verbosity)                      │
└─────────────────────────────────────────────────────────────────────────┘
```

## 下一步扩展

1. **持久化完善**: 将交互、报告、对话数据完整持久化到 Neo4j
2. **向量检索**: 实现记忆的向量相似度检索
3. **图算法**: 实现完整的网络分析算法
4. **定时任务**: 添加定时执行模拟和生成报告的功能
5. **前端集成**: 在可视化界面中展示模拟进度和报告
