# 消息发送方式对比

## 📊 三个版本的发送逻辑

---

### 1. quantclaw_webhook.py（纯 HTTP API）

**发送方式**：Clawdbot CLI（`subprocess.run`）

```python
cmd = [
    'clawdbot', 'agent',
    '--to', f'qc-{agent_id}',  # ← 虚拟用户
    '--message', full_message,
    '--json'
]

result = subprocess.run(
    cmd,
    capture_output=True,  # ← 等待完整输出
    text=True,
    timeout=300
)

# 解析响应
response = json.loads(result.stdout)
reply_text = extract_text(response)

# 返回给客户端
return web.json_response({'reply': reply_text})
```

**特点**：
- ❌ **不是流式**（等待完整输出）
- ❌ 用户需要等待整个响应生成
- ✅ 实现简单
- ✅ 适合 HTTP API（一次性请求）

---

### 2. app.py / app_integrated.py（WebSocket + Gateway）

**发送方式**：Gateway RPC（`chat.send`）

```python
# 发送到 Gateway
rpc_msg = {
    'type': 'req',
    'id': 'msg_1',
    'method': 'chat.send',  # ← Gateway RPC
    'params': {
        'sessionKey': session_key,  # ← agent:qc-xxx:main
        'message': text,
    }
}
await gateway_ws.send_json(rpc_msg)

# 监听流式响应
async for msg in gateway_ws:
    if msg.data.event == 'agent':
        stream = msg.payload.stream
        
        if stream == 'assistant':
            # 流式片段
            delta = msg.payload.data.delta
            text = msg.payload.data.text
            
            # 转发到客户端
            await ws_client.send_json({
                'type': 'stream',
                'delta': delta,
                'text': text
            })
```

**特点**：
- ✅ **流式输出**（实时显示）
- ✅ 用户立即看到响应
- ✅ 最佳体验
- ❌ 依赖 Gateway WebSocket

---

### 3. app_v3_hybrid.py（尝试的混合方案）

**发送方式**：Clawdbot CLI（`subprocess.Popen`）+ Gateway 监听

```python
# 异步发送（不等待）
subprocess.Popen(
    ['clawdbot', 'agent', '--to', f'qc-{agent_id}', '--message', text],
    stdout=subprocess.DEVNULL,  # ← 不读取输出
    stderr=subprocess.DEVNULL
)

# 监听 Gateway 广播
async for msg in gateway_ws:
    if msg.sessionKey == f'agent:{agent_id}:main':
        # 过滤出当前用户的流式响应
        await ws_client.send_json({'type': 'stream', 'delta': delta})
```

**特点**：
- ✅ 理论上可以流式
- ❌ 握手失败（client.id 问题已修复）
- ⚠️ 需要验证是否真的能工作

---

## 🆚 详细对比

| 项目 | quantclaw_webhook | app_integrated | app_v3_hybrid |
|------|------------------|----------------|---------------|
| **发送方式** | Clawdbot CLI | Gateway RPC | Clawdbot CLI |
| **等待响应** | ✅ 等待 | ❌ 立即返回 | ❌ 不等待 |
| **读取输出** | ✅ subprocess.run | ❌ Gateway 事件 | ❌ DEVNULL |
| **流式** | ❌ 否 | ✅ 是 | ✅ 理论上 |
| **实现** | 简单 | 标准 | 复杂 |
| **依赖** | Clawdbot CLI | Gateway WS | 两者都依赖 |

---

## 🔑 关键差异

### quantclaw_webhook.py

**问题场景**：
```
用户发送: "写一篇1000字的文章"
    ↓
调用 Clawdbot CLI
    ↓
等待 30 秒...（subprocess.run 阻塞）
    ↓
获得完整文章
    ↓
一次性返回给客户端
```

**用户体验**：
- ❌ 等待 30 秒无反馈
- ❌ 不知道是否在处理
- ❌ 可能超时

---

### app_integrated.py（推荐）

**使用场景**：
```
用户发送: "写一篇1000字的文章"
    ↓
发送到 Gateway（立即返回）
    ↓
Gateway 流式事件：
  - "正" (100ms)
  - "在" (200ms)
  - "写" (300ms)
  - "作" (400ms)
  ...
    ↓
实时转发到客户端
```

**用户体验**：
- ✅ 立即看到响应
- ✅ 逐字显示
- ✅ 类似 ChatGPT 体验

---

### app_v3_hybrid.py（实验）

**理论场景**：
```
用户发送: "写一篇文章"
    ↓
异步调用 Clawdbot CLI（不等待）
    ↓
Clawdbot 执行 → Gateway 接收
    ↓
Gateway 广播流式事件
    ↓
app_v3 监听 Gateway → 过滤 sessionKey
    ↓
转发到客户端
```

**问题**：
- ⚠️ Gateway 握手失败（已修复）
- ⚠️ 需要验证是否真的能工作

---

## 🎯 推荐方案

### 最佳实践：app_integrated.py

**优势**：
- ✅ 使用标准的 Gateway RPC（`chat.send`）
- ✅ 原生流式输出
- ✅ 稳定可靠
- ✅ 保留所有原版功能
- ✅ 添加 Token 认证

**发送逻辑**：
```python
# 统一使用 Gateway RPC
await gateway_ws.send_json({
    'method': 'chat.send',
    'params': {
        'sessionKey': session_key,  # token 或 sessionKey 都转为这个
        'message': text
    }
})
```

**兼容性**：
- ✅ Token 认证 → 自动转为 sessionKey
- ✅ SessionKey 直接使用
- ✅ 消息发送逻辑完全相同

---

## 📋 总结

| 服务 | 发送方式 | 流式 | 认证 | 推荐 |
|------|---------|------|------|------|
| **app_integrated.py** | Gateway RPC | ✅ | ✅ | ⭐⭐⭐ |
| app.py | Gateway RPC | ✅ | ❌ | ⭐⭐ |
| quantclaw_webhook.py | Clawdbot CLI | ❌ | ✅ | ⭐ |
| app_v3_hybrid.py | CLI + Gateway | ⚠️ | ✅ | ❓ (实验) |

---

## 💡 答案

**quantclaw_webhook.py 使用的是 Clawdbot CLI（subprocess.run）**：
- ❌ 不是流式
- ❌ 等待完整输出
- ✅ 适合纯 HTTP API

**app_integrated.py 使用的是 Gateway RPC（chat.send）**：
- ✅ 流式输出
- ✅ 实时响应
- ✅ 最佳体验

**两种发送方式不同，但认证逻辑相同！**

---

*文档时间：2026-05-21*
