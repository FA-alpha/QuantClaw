# Lark Webhook 实现逻辑分析

## 📋 核心架构

`lark_webhook.py` 是一个 **HTTP Webhook 服务器**，用于接收 Lark（飞书）消息并转发给 Clawdbot。

---

## 🔄 消息流程

```
Lark 群聊 @机器人
    ↓
Lark 服务器发送 Webhook POST 请求
    ↓
lark_webhook.py 接收并处理
    ↓
保存到本地记忆系统（双写）
    ↓
调用 clawdbot CLI（--to lark-{chat_id}）
    ↓
clawdbot 处理并返回响应
    ↓
lark_webhook.py 解析响应
    ↓
发送回复到 Lark 群聊
```

---

## 🧠 记忆系统（双写机制）

### 1. 简单文件记录（向后兼容）
```python
# 保存到 JSONL 文件
/home/ubuntu/clawd/memory/lark_chats/{chat_id}.jsonl
```

格式：
```json
{
  "ts": 1779340055.270,
  "time": "2026-05-21 13:07:35",
  "sender_id": "ou_xxx",
  "sender_name": "张三",
  "text": "消息内容",
  "media": "/path/to/image.jpg"  // 可选
}
```

### 2. 分层记忆系统（语义检索）
```python
if USE_LAYERED_MEMORY:  # 默认 True
    memory = get_memory(chat_id)
    memory.add_message(sender_id, sender_name, text, timestamp, media_path)
```

**特性**：
- **短期记忆**：内存中最近 20 条消息
- **中期记忆**：embedding 向量检索（OpenAI text-embedding-3-small）
- **长期记忆**：每 100 条生成摘要

---

## 🔑 关键点：不使用固定 Session

### 传统方式（QuantClaw 使用）：
```python
# 使用固定 session，历史记录由 clawdbot 管理
clawdbot agent --session-id "quantclaw-main" --message "..."
```

### Lark Webhook 方式：
```python
# 使用虚拟"电话号码"，每个群独立
clawdbot agent --to "lark-{chat_id}" --message "{context}\n{message}"
```

**区别**：

| 方式 | Session 管理 | 上下文来源 | 适用场景 |
|------|-------------|-----------|---------|
| `--session-id` | clawdbot 内部 | JSONL session 文件 | 单用户持续对话 |
| `--to` | 每次新建 | Webhook 自行构建 | 多群并发、独立上下文 |

---

## 📝 上下文构建逻辑

### 第 1 步：构建上下文
```python
if USE_LAYERED_MEMORY:
    # 使用语义检索构建上下文
    memory = get_memory(chat_id)
    context = memory.build_context(query=clean_text)
else:
    # 简单获取最近 50 条消息
    context = get_recent_context(chat_id)
```

### 第 2 步：组装完整消息
```python
# 添加群 ID 标识（用于加载群角色配置）
chat_header = f"[lark_chat_id: {chat_id}]\n"

# 完整消息格式
full_message = f"""
{chat_header}
=== 最近的群聊记录 ===
[2026-05-21 13:05:00] 张三: 前面的讨论...
[2026-05-21 13:06:30] 李四: 回复内容...
=== 群聊记录结束 ===

来自 张三 的消息：当前问题内容
"""
```

### 第 3 步：调用 Clawdbot
```python
cmd = [
    "clawdbot", "agent",
    "--to", f"lark-{chat_id}",  # 虚拟号码，每个群独立
    "--message", full_message,
    "--json"
]

# 如果有图片附件
cmd.extend(["--image", "/path/to/image.jpg"])
```

---

## 🎯 为什么不用 Session？

### 原因 1：多群并发隔离
- 每个群有独立的 `chat_id`
- 使用 `--to lark-{chat_id}` 创建虚拟独立上下文
- 避免不同群的消息互相干扰

### 原因 2：上下文控制
- Webhook 自己管理聊天记录
- 可以实现**语义检索**（不只是最近几条）
- 可以过滤无关消息，只提供相关上下文

### 原因 3：群角色配置
- 通过 `[lark_chat_id: {chat_id}]` 标识
- Clawdbot 可以加载对应的群角色配置
- 文件位置：`/home/ubuntu/clawd/memory/lark_personas/{chat_id}.md`

### 原因 4：性能考虑
- 不需要维护长期 session 文件
- 每次调用都是"新对话"，但带有自定义上下文
- 避免 session 文件过大

---

## 🔍 实际案例

### 用户在群里 @机器人：
```
@慧慧 最近策略表现如何？
```

### Webhook 构建的实际消息：
```
[lark_chat_id: oc_a1b2c3d4e5f6]

=== 最近的群聊记录 ===
[2026-05-21 13:00:00] 张三: 今天行情不错
[2026-05-21 13:02:15] 李四: @慧慧 帮我查询回测6087
[2026-05-21 13:02:20] 慧慧: 回测6087结果：收益率15.2%...
[2026-05-21 13:05:00] 王五: 策略效果确实挺好
=== 群聊记录结束 ===

来自 张三 的消息：最近策略表现如何？
```

### Clawdbot 收到后：
1. 看到 `[lark_chat_id: oc_a1b2c3d4e5f6]`
2. 加载对应群角色配置（如果有）
3. 根据上下文回复
4. **不会保存到 session 文件**（因为用的是 `--to`）

---

## 📊 对比总结

| 特性 | QuantClaw (Session) | Lark Webhook (--to) |
|------|---------------------|---------------------|
| **上下文管理** | Clawdbot 内部 | Webhook 自行构建 |
| **历史记录** | Session JSONL | 自定义 JSONL + embedding |
| **多用户** | 单用户/单 session | 多群并发，独立隔离 |
| **语义检索** | 无 | 有（embedding 向量） |
| **群角色** | 无 | 支持（按 chat_id） |
| **Session 文件** | 会增长 | 不生成 |
| **适用场景** | Web 单用户对话 | 群聊、多对话并发 |

---

## 🚀 优势

1. **上下文灵活**：可以实现语义检索，不只是最近消息
2. **性能更好**：不需要维护大 session 文件
3. **隔离性强**：每个群完全独立
4. **可扩展**：容易添加更多功能（摘要、过滤等）

---

## ⚠️ 注意事项

- `--to` 参数每次创建新"对话"，不会保存到持久 session
- 所有上下文都需要 Webhook 自己提供
- Clawdbot 的回复也需要 Webhook 保存到本地记忆
- 适合需要完全自定义上下文管理的场景

---

*更新时间：2026-05-21*
