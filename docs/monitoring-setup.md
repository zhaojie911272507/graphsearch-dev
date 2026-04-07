# 监控和可观测性设置指南

## 快速启动

```bash
# 启动完整栈（应用 + 监控）
docker-compose up -d

# 查看监控服务状态
docker-compose ps

# 查看应用日志
docker-compose logs -f app
```

## 访问仪表板

| 服务 | URL | 凭据 |
|------|-----|------|
| Grafana | http://localhost:3000 | admin/admin |
| Prometheus | http://localhost:9090 | - |
| Tempo | http://localhost:3200 | - |
| Alertmanager | http://localhost:9093 | - |

## 验证步骤

### 1. 验证 Prometheus 指标

```bash
# 检查 /metrics 端点
curl http://localhost:8000/metrics | head -20

# 预期输出包含:
# http_requests_total
# http_request_duration_seconds
# rag_embedding_latency_seconds
# ...
```

### 2. 验证 Prometheus 抓取

访问 http://localhost:9090/targets

- 确认 `graphrag-api` 状态为 UP

### 3. 验证追踪

1. 发送几个请求到 API:
```bash
curl http://localhost:8000/api/v1/query -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "测试查询"}'
```

2. 访问 Grafana Tempo 数据源查看 traces

### 4. 验证仪表板

1. 登录 Grafana: http://localhost:3000
2. 浏览 "Graph RAG" 文件夹
3. 确认 System Overview 和 RAG Pipeline 仪表板显示数据

### 5. 验证告警

1. 访问 Prometheus Alerts: http://localhost:9090/alerts
2. 确认所有告警规则已加载
3. 触发告警条件（如停止 app 服务）
4. 确认告警状态变为 PENDING → FIRING

## 配置自定义

### 修改采样率

在 `.env` 中:
```bash
OTEL_TRACES_SAMPLER_ARG=0.01  # 1% 采样
```

### 添加告警通知

编辑 `monitoring/alertmanager/alertmanager.yml`:

```yaml
receivers:
  - name: 'slack-receiver'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
        channel: '#alerts'
```

## 故障排查

### Prometheus 无法抓取指标

1. 检查应用日志：`docker-compose logs app`
2. 验证 /metrics 端点：`curl http://localhost:8000/metrics`
3. 检查 Prometheus 配置：`cat monitoring/prometheus/prometheus.yml`

### Tempo 未收到 traces

1. 检查 OTEL 配置：`docker-compose exec app env | grep OTEL`
2. 验证 Tempo 可访问性：`docker-compose exec app curl http://tempo:4318`
3. 检查应用日志中的 tracing 初始化信息

### Grafana 仪表板无数据

1. 确认数据源配置正确
2. 检查 Prometheus 是否有数据：`up{job="graphrag-api"}`
3. 验证时间范围选择正确

## 生产环境建议

1. **持久化**: 配置卷备份
2. **高可用**: 部署多副本 Prometheus
3. **安全**: 启用认证和 HTTPS
4. **告警**: 集成 PagerDuty/Slack
5. **保留策略**: 调整数据保留时间
