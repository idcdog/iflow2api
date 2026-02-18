# 远程调试指南

当用户报告问题时，可以按照以下步骤收集诊断信息。

## 1. 收集环境信息

请用户提供以下命令的输出：

```bash
# 健康检查（包含完整诊断信息）
curl http://localhost:28000/health

# 或使用 Docker
docker exec <container_name> curl http://localhost:28000/health
```

**预期输出示例：**
```json
{
  "status": "healthy",
  "iflow_logged_in": true,
  "version": "1.2.5",
  "os": "Debian GNU/Linux 13",
  "platform": "Linux",
  "architecture": "x86_64",
  "python": "3.12.12",
  "runtime": "Docker",
  "docker": true,
  "kubernetes": false,
  "wsl": false
}
```

## 2. 收集日志

### Docker 环境

```bash
# 查看完整日志
docker logs <container_name>

# 实时跟踪日志
docker logs -f <container_name>

# 查看最近 100 行日志
docker logs --tail 100 <container_name>
```

### 本地环境

日志会直接输出到标准输出，请复制完整的启动日志和错误发生时的日志。

## 3. 关键日志信息

启动日志应包含：

```
============================================================
  iflow2api v1.2.5
============================================================
  系统: Debian GNU/Linux 13
  平台: Linux x86_64
  Python: 3.12.12 (CPython)
  环境: Docker
  时间: 2026-02-18 11:01:28
============================================================
[iflow2api] 已加载 iFlow 配置
[iflow2api] API Base URL: https://apis.iflow.cn/v1
[iflow2api] API Key: sk-92af795...
[iflow2api] 默认模型: glm-4.7
```

请求日志应包含：

```
[iflow2api] Request: POST /v1/chat/completions (14.2KB)
[iflow2api] Chat请求: model=glm-5, stream=True, messages=104, has_tools=True
[iflow2api] 获取上游流式响应...
[iflow2api] 为模型 glm-5 添加思考参数: chat_template_kwargs, enable_thinking, thinking
[iflow2api] 流式请求 URL: https://apis.iflow.cn/v1/chat/completions
[iflow2api] Response: 200 (1234ms)
```

## 4. 问题排查清单

请用户提供以下信息：

### 必需信息

- [ ] `/health` 端点的完整输出
- [ ] 完整的启动日志
- [ ] 错误发生时的请求日志
- [ ] 使用的客户端名称和版本（如 Cherry Studio、OpenClaw、沉浸式翻译等）
- [ ] 请求的大致规模（消息数量、是否有工具调用）

### 可选信息

- [ ] 请求体（脱敏后）
- [ ] 上游 API 响应状态码
- [ ] 网络环境描述（服务器位置、是否有代理等）

## 5. 常见问题

### 上游流式响应为空 (0 chunks)

**可能原因：**

1. **请求体过大** - 消息数量过多或内容过长
   - 解决方案：减少消息数量，使用更短的对话历史

2. **上下文窗口设置** - 使用了 200k 上下文
   - 解决方案：将上下文设置为 128k

3. **上游 API 临时问题** - iFlow API 服务暂时不可用
   - 解决方案：等待一段时间后重试

4. **会话状态累积** - 长时间运行后会话 ID 可能积累特殊状态
   - 解决方案：重启 Docker 容器以重置会话 ID

### 调试步骤

1. 使用简单请求测试：
   ```bash
   curl -X POST http://localhost:28000/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model": "glm-5", "messages": [{"role": "user", "content": "你好"}]}'
   ```

2. 如果简单请求正常，逐步增加消息数量

3. 检查是否是特定客户端的问题

## 6. Issue 模板

```markdown
## 问题描述
[描述遇到的问题]

## 环境信息

- **版本**: iflow2api v1.2.5
- **系统**: Debian GNU/Linux 13
- **平台**: Linux x86_64
- **Python**: 3.12.12
- **环境**: Docker
- **Docker**: 是

## 客户端信息
- 客户端名称：
- 客户端版本：

## 请求规模
- 消息数量：
- 工具数量：
- 是否流式：

## 日志

```
[粘贴启动日志]
```

```
[粘贴错误发生时的日志]
```

## 其他信息
[任何其他可能有助于解决问题的信息]
```
