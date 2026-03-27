# 社会模拟系统 - 环境搭建模块实现文档

## 概述

本文档描述了基于 MiroFish 项目灵感实现的社会模拟系统环境搭建模块。该模块负责从现实种子提取、人设生成、到环境配置的全过程。

## 实现的功能

### 1. 领域模型扩展 (`app/domain/social/`)

#### 枚举类型 (`enums.py`)
- **MemoryType**: 记忆类型（个体/集体/情景/语义/程序）
- **PlatformType**: 社交平台类型（微信/小红书）
- **SimulationStatus**: 模拟会话状态
- **AgentState**: Agent 活动状态
- **EmotionType**: 基本情绪类型
- **SeedSourceType**: 种子来源类型

#### 节点模型 (`nodes.py`)
- **AgentNode**: 模拟个体角色
  - 详细画像 (AgentProfile): 姓名、职业、兴趣、价值观等
  - 人格特质 (PersonalityTraits): 大五人格模型
  - 背景故事、目标、状态
- **MemoryNode**: 个体/群体记忆
  - 记忆内容、类型、重要性
  - 情绪标签、关联 Agent
- **WorldStateNode**: 仿真世界状态
  - 平台类型、状态数据、活跃 Agent
- **SimulationSessionNode**: 模拟会话
  - 会话参数、指标、关联世界和 Agent
- **SeedNode**: 现实种子
  - 来源 URL、原始内容、可信度评分

#### 关系类型 (`relationships.py`)
- Agent-Memory: HAS_MEMORY, MEMORY_ORIGIN, SHARED_MEMORY
- Agent-Agent: KNOWS, FRIENDS_WITH, FOLLOWS, TRUSTS, FAMILY_OF, COLLEAGUE_OF
- Agent-World: EXISTS_IN, INTERACTS_IN, OWNS
- Seed-Extraction: EXTRACTED_FROM, GENERATED_BY, SOURCED_FROM
- Session-Management: PART_OF_SESSION, SESSION_CONTAINS, WORLD_OF_SESSION

### 2. Agent 服务层 (`app/services/`)

#### SeedExtractorAgent (`seed_extractor.py`)
**职责**: 从现实种子中提取实体和关系

```python
# 使用示例
extractor = SeedExtractorAgent(openai_settings)
result = await extractor.extract_seed(
    source_type="TEXT",
    raw_content="在一些内容中提到了张三和李四...",
)
# 返回：SeedExtractionResult(
#   seed_node, entities, concepts, relationships, potential_agents
# )
```

**核心功能**:
- 支持多种来源 (URL/文档/文本)
- LLM 驱动的实体和关系提取
- 识别潜在 Agent 候选人
- 自动计算内容哈希

#### ProfileGeneratorAgent (`profile_generator.py`)
**职责**: 生成详细的 Agent 人设

```python
# 使用示例
generator = ProfileGeneratorAgent(openai_settings)
result = await generator.generate_profiles(
    seed_data={"title": "...", "raw_content": "..."},
    profile_count=10,
    platform=PlatformType.WECHAT,
)
# 返回：ProfileGenerationResult(agents, memories, relationships)
```

**核心功能**:
- 基于种子内容生成多样化角色
- 完整的人格特质生成 (大五人格)
- 背景故事自动生成
- 初始记忆创建
- Agent 间关系构建

#### EnvironmentConfigAgent (`environment_config.py`)
**职责**: 配置仿真环境参数

```python
# 使用示例
config_agent = EnvironmentConfigAgent(openai_settings)

# 配置世界
world_result = config_agent.configure_world(
    world_key="wechat_world",
    name="WeChat Simulation",
    platform=PlatformType.WECHAT,
)

# 设置平台参数
platform_config = config_agent.setup_platform_config(
    "WECHAT",
    custom_config={"interaction_probability": 0.5}
)
```

**核心功能**:
- 世界状态初始化
- 平台特定配置 (微信/小红书默认配置)
- 交互规则定义
- 模拟参数注入

#### SimulationOrchestrator (`simulation_orchestrator.py`)
**职责**: 编排完整的 bootstrap 流程

```python
# 使用示例
orchestrator = SimulationOrchestrator(openai_settings, graph_store)
config = SimulationBootstrapConfig(
    name="My Simulation",
    seed_sources=[{"source_type": "TEXT", "content": "..."}],
    agent_count=20,
    platforms=["WECHAT", "XIAOHONGSHU"],
)
result = await orchestrator.bootstrap(config)
```

**核心功能**:
- 串联所有 Agent 服务
- 进度跟踪
- 图数据库持久化
- 错误处理和恢复

### 3. API 路由 (`app/api/routes/simulation.py`)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/simulation/bootstrap` | POST | 初始化完整模拟环境 |
| `/api/v1/simulation/seeds/extract` | POST | 提取现实种子 |
| `/api/v1/simulation/agents/generate` | POST | 生成 Agent 人设 |
| `/api/v1/simulation/world/configure` | POST | 配置模拟世界 |
| `/api/v1/simulation/sessions/{id}` | GET | 查询会话状态 |
| `/api/v1/simulation/sessions/{id}/start` | POST | 启动模拟 |
| `/api/v1/simulation/query` | POST | 查询模拟状态 |

### 4. API Schemas (`app/api/schemas/simulation.py`)

- **SeedExtractRequest/Response**: 种子提取请求/响应
- **AgentGenerateRequest/Response**: Agent 生成请求/响应
- **WorldConfigRequest/Response**: 世界配置请求/响应
- **SimulationBootstrapRequest/Response**: Bootstrap 请求/响应
- **SimulationParamsSchema**: 模拟参数
- **MemorySchema**: 记忆信息

### 5. 配置扩展 (`app/config.py`)

```python
class SimulationSettings(BaseSettings):
    max_agents: int = 50
    memory_decay_rate: float = 0.1
    interaction_probability: float = 0.3
    platform_sync_interval: int = 60
    simulation_speed: float = 1.0
    enable_emotion: bool = True
    enable_memory_formation: bool = True
    enable_relationship_evolution: bool = True
```

## 使用示例

### 1. 通过 API Bootstrap 模拟

```bash
curl -X POST http://localhost:8000/api/v1/simulation/bootstrap \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Tech Company Simulation",
    "description": "Simulating social dynamics in a tech company",
    "seed_sources": [
      {
        "source_type": "TEXT",
        "content": "在北京的一家科技公司，有一个由张伟领导的团队..."
      }
    ],
    "agent_count": 10,
    "platforms": ["WECHAT", "XIAOHONGSHU"],
    "parameters": {
      "max_agents": 20,
      "interaction_probability": 0.3
    }
  }'
```

### 2. 在代码中使用

```python
from app.services.simulation_orchestrator import SimulationOrchestrator
from app.config import get_settings

settings = get_settings()
orchestrator = SimulationOrchestrator(
    openai_settings=settings.openai,
    graph_store=graph_store,
)

config = SimulationBootstrapConfig(
    name="Test Simulation",
    agent_count=5,
    platforms=["WECHAT"],
    seed_sources=[{
        "source_type": "TEXT",
        "content": "一些描述社会场景的内容..."
    }]
)

result = await orchestrator.bootstrap(config)
print(f"Created {len(result.agents)} agents")
```

## 平台默认配置

### 微信 (WECHAT)
- 发帖频率：0.5-3.0 篇/天
- 互动概率：0.4
- 内容主题：daily_life, work, family, news, hobbies
- 活跃时段：8,9,12,13,20,21,22 点
- 字符限制：1500

### 小红书 (XIAOHONGSHU)
- 发帖频率：0.3-2.0 篇/天
- 互动概率：0.5
- 内容主题：lifestyle, beauty, fashion, travel, food, shopping
- 活跃时段：9,10,11,20,21,22,23 点
- 字符限制：1000

## 测试

### 单元测试
```bash
pytest tests/test_simulation_setup.py -v
```

### API 测试
```bash
# 启动服务器
uvicorn app.main:app --reload

# 运行测试脚本
python scripts/test_simulation_api.py
```

## 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                     Simulation Bootstrap                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. SeedExtractorAgent                                          │
│     Input: 种子来源 (URL/文本/文档)                              │
│     Output: SeedNode + 提取的实体/关系/潜在 Agent                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. ProfileGeneratorAgent                                       │
│     Input: Seed 数据                                             │
│     Output: AgentNode[] + MemoryNode[] + Relationships          │
│     - 生成画像 (AgentProfile)                                   │
│     - 生成人格 (PersonalityTraits)                              │
│     - 生成背景故事                                              │
│     - 生成初始记忆                                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. EnvironmentConfigAgent                                      │
│     Input: 配置参数                                              │
│     Output: WorldStateNode[] + PlatformConfig[] + Rules         │
│     - 配置世界状态                                              │
│     - 设置平台参数                                              │
│     - 定义交互规则                                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. GraphStore Persistence                                      │
│     - 持久化所有节点到 Neo4j                                    │
│     - 创建关系连接                                              │
│     - 初始化模拟会话                                            │
└─────────────────────────────────────────────────────────────────┘
```

## 下一步

环境搭建模块已完成，后续可以实现：

1. **模拟执行模块** (`Task #1`)
   - 双平台并行模拟
   - 时序记忆动态更新
   - 需求预测解析

2. **报告生成模块** (`Task #2`)
   - ReportAgent 实现
   - 丰富工具集
   - 深度交互对话

3. **深度互动功能**
   - 与任意 Agent 对话
   - 记忆查询和修改
   - 世界状态观察

## 文件结构

```
app/
├── domain/social/
│   ├── __init__.py              # 包导出
│   ├── enums.py                 # 枚举类型
│   ├── nodes.py                 # 节点模型
│   └── relationships.py         # 关系类型
├── services/
│   ├── __init__.py              # 包导出
│   ├── seed_extractor.py        # SeedExtractorAgent
│   ├── profile_generator.py     # ProfileGeneratorAgent
│   ├── environment_config.py    # EnvironmentConfigAgent
│   └── simulation_orchestrator.py # SimulationOrchestrator
├── api/
│   ├── routes/
│   │   ├── simulation.py        # 模拟 API 路由
│   │   └── __init__.py          # (已更新)
│   └── schemas/
│       └── simulation.py        # 模拟 API schemas
├── config.py                    # (已扩展 SimulationSettings)
└── main.py                      # (已注册 simulation 路由)

tests/
└── test_simulation_setup.py     # 单元测试

scripts/
└── test_simulation_api.py       # API 集成测试

.env.example                     # (已添加模拟配置)
```
