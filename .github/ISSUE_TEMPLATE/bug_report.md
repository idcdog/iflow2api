---
name: Bug 报告
about: 报告 iflow2api 的问题
title: '[Bug] '
labels: bug
assignees: ''
---

## 问题描述

[描述遇到的问题]

## 环境信息

请运行以下命令并提供输出：

```bash
curl http://localhost:28000/health
```

**或（Docker 环境）：**

```bash
docker exec <container_name> curl http://localhost:28000/health
```

<details>
<summary>健康检查输出</summary>

```json
{
  // 粘贴 /health 端点的输出
}
```

</details>

## 客户端信息

- 客户端名称：[例如：Cherry Studio、OpenClaw、沉浸式翻译]
- 客户端版本：

## 请求规模

- 消息数量：
- 工具数量：
- 是否流式：
- 上下文窗口设置：

## 日志

<details>
<summary>启动日志</summary>

```
============================================================
  iflow2api v1.2.5
============================================================
// 粘贴启动日志
```

</details>

<details>
<summary>错误发生时的日志</summary>

```
// 粘贴错误发生时的请求日志
```

</details>

## 复现步骤

1. 
2. 
3. 

## 其他信息

[任何其他可能有助于解决问题的信息]
