# 混合方案：Webhook 认证 + Gateway 流式

## 🎯 设计思路

结合 quantclaw-webhook 和 Gateway 的优势：

**Webhook 负责**：
- ✅ Token 认证
- ✅ 用户管理（自动注册）
- ✅ agent_id 映射
- ✅ Workspace 创建

**Gateway 负责**：
- ✅ 消息发送（chat.send RPC）
- ✅ 流式响应监听
- ✅ 完整的 Agent 功能

---

## 🔄 完整流程

```
客户端 WebSocket (带 token)
    ↓
1. Token 验证 + 获取 agent_id
   (使用 quantclaw-webhook 逻辑)
    ↓
2. 保存用户消息到 quantclaw_chats/{agent_id}.jsonl
    ↓
3. 连接 Gateway WebSocket
    ↓
4. 发送消息: chat.send RPC
   sessionKey: agent:{agent_id}:main
    ↓
5. 监听 Gateway 流式事件
   event: "agent", stream: "assistant"
    ↓
6. 转发流式片段到客户端 WebSocket
    ↓
7. 保存完整回复到 quantclaw_chats/{agent_id}.jsonl
```

---

## 📝 核心代码实现

### 完整的混合版本

```python
async def handle_websocket_hybrid(request: web.Request):
    """混合方案：Webhook 认证 + Gateway 流式"""
    ws_client = web.WebSocketResponse()
    await ws_client.prepare(request)
    
    user_manager: UserManager = request.app['user_manager']
    memory_manager: AgentMemoryManager = request.app['memory_manager']
    
    # 从查询参数获取 token
    token = request.query.get('token')
    
    if not token:
        await ws_client.send_json({'type': 'error', 'error': 'Missing token'})
        await ws_client.close()
        return ws_client
    
    # 1. Token 认证 + 获取 agent_id
    user = user_manager.find_by_token(token)
    if not user:
        if AUTO_REGISTER:
            try:
                user = await user_manager.auto_register(token)
            except Exception as e:
                await ws_client.send_json({'type': 'error', 'error': str(e)})
                await ws_client.close()
                return ws_client
        else:
            await ws_client.send_json({'type': 'error', 'error': 'Invalid token'})
            await ws_client.close()
            return ws_client
    
    agent_id = user['agentId']
    session_key = f'agent:{agent_id}:main'  # ← 使用 agent_id 构建 sessionKey
    
    logger.info(f'🔗 WebSocket connected: {agent_id}')
    
    # 2. 发送历史记录
    history = memory_manager.load_history(agent_id)
    await ws_client.send_json({
        'type': 'history',
        'messages': history
    })
    
    # 3. 连接到 Gateway
    try:
        async with aiohttp.ClientSession() as http_session:
            gateway_url = f'{GATEWAY_WS}?token={GATEWAY_TOKEN}'
            
            async with http_session.ws_connect(gateway_url) as gateway_ws:
                # 完成 Gateway 握手
                connected = await complete_handshake(gateway_ws)
                if not connected:
                    await ws_client.send_json({'type': 'error', 'error': 'Gateway handshake failed'})
                    return ws_client
                
                logger.info(f'✅ Gateway connected for {agent_id}')
                
                # 状态变量
                current_response = ['']
                response_saved = [False]
                
                # 处理客户端消息
                async def handle_client_messages():
                    async for msg in ws_client:
                        if msg.type == WSMsgType.TEXT:
                            try:
                                data = json.loads(msg.data)
                                msg_type = data.get('type', 'message')
                                
                                if msg_type == 'ping':
                                    await ws_client.send_json({'type': 'pong'})
                                    continue
                                
                                # 处理消息
                                text = data.get('text') or data.get('message', '')
                                if text:
                                    logger.info(f'📨 Message from {agent_id}: {text[:50]}...')
                                    
                                    # 重置状态
                                    current_response[0] = ''
                                    response_saved[0] = False
                                    
                                    # 保存用户消息
                                    memory_manager.save_message(agent_id, 'user', '用户', text)
                                    
                                    # 构建上下文
                                    context = memory_manager.get_recent_context(agent_id, limit=20)
                                    full_message = f'{context}\n\n用户消息：{text}'
                                    
                                    # 发送到 Gateway
                                    rpc_msg = {
                                        'type': 'req',
                                        'id': f'msg_{int(asyncio.get_event_loop().time() * 1000)}',
                                        'method': 'chat.send',
                                        'params': {
                                            'sessionKey': session_key,
                                            'message': full_message
                                        }
                                    }
                                    await gateway_ws.send_json(rpc_msg)
                                    logger.info(f'📤 Sent to Gateway: {session_key}')
                            
                            except json.JSONDecodeError:
                                pass
                        elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                            break
                
                # 处理 Gateway 消息（流式响应）
                async def handle_gateway_messages():
                    async for msg in gateway_ws:
                        if msg.type == WSMsgType.TEXT:
                            try:
                                data = json.loads(msg.data)
                                
                                event_type = data.get('event', '')
                                if event_type in ('health', 'tick'):
                                    continue
                                
                                msg_type = data.get('type', '')
                                payload = data.get('payload', {})
                                
                                # 只处理当前 session 的事件
                                if msg_type == 'event' and event_type == 'agent':
                                    msg_session_key = payload.get('sessionKey', '')
                                    
                                    # 必须匹配 session_key
                                    if msg_session_key != session_key:
                                        continue
                                    
                                    stream = payload.get('stream')
                                    stream_data = payload.get('data', {})
                                    
                                    if stream == 'assistant':
                                        # 流式文本
                                        text = stream_data.get('text', '')
                                        delta = stream_data.get('delta', '')
                                        current_response[0] = text
                                        
                                        # 转发流式数据到客户端
                                        await ws_client.send_json({
                                            'type': 'stream',
                                            'text': text,
                                            'delta': delta
                                        })
                                    
                                    elif stream == 'lifecycle':
                                        phase = stream_data.get('phase')
                                        
                                        if phase == 'end':
                                            # 保存完整回复
                                            if current_response[0] and not response_saved[0]:
                                                reply_text = current_response[0]
                                                memory_manager.save_message(
                                                    agent_id, 'assistant', 'QuantClaw', reply_text
                                                )
                                                response_saved[0] = True
                                                logger.info(f'✅ Saved reply for {agent_id}')
                                            
                                            # 发送完成标志
                                            await ws_client.send_json({'type': 'done'})
                            
                            except json.JSONDecodeError:
                                pass
                        elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                            break
                
                # 并发处理客户端和 Gateway 消息
                await asyncio.gather(
                    handle_client_messages(),
                    handle_gateway_messages()
                )
    
    except Exception as e:
        logger.error(f'❌ WebSocket error: {e}')
    finally:
        logger.info(f'🔴 WebSocket disconnected: {agent_id}')
    
    return ws_client


async def complete_handshake(gateway_ws):
    """完成 Gateway 握手"""
    connect_id = 'conn_' + str(id(gateway_ws))
    
    async for msg in gateway_ws:
        if msg.type == WSMsgType.TEXT:
            data = json.loads(msg.data)
            
            if data.get('event') == 'connect.challenge':
                connect_req = {
                    'type': 'req',
                    'id': connect_id,
                    'method': 'connect',
                    'params': {
                        'minProtocol': 3,
                        'maxProtocol': 3,
                        'client': {
                            'id': 'quantclaw-v2',
                            'version': '2.0.0',
                            'platform': 'linux',
                            'mode': 'backend'
                        },
                        'role': 'operator',
                        'scopes': ['operator.read', 'operator.write'],
                        'caps': [],
                        'commands': [],
                        'permissions': {},
                        'auth': {'token': GATEWAY_TOKEN},
                        'locale': 'zh-CN',
                        'userAgent': 'quantclaw-v2/2.0.0'
                    }
                }
                await gateway_ws.send_json(connect_req)
            
            elif data.get('type') == 'res' and data.get('id') == connect_id:
                if data.get('ok'):
                    logger.info('✅ Gateway handshake complete')
                    return True
                else:
                    logger.error(f'❌ Handshake failed: {data.get("error")}')
                    return False
        
        elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
            return False
    
    return False
```

---

## 🆚 方案对比

| 方案 | 认证 | 记忆管理 | 消息发送 | 响应方式 | 流式 |
|------|------|---------|---------|---------|------|
| **纯 Webhook** | Webhook | agent_id | Clawdbot CLI | subprocess.run | ❌ |
| **纯 Gateway** | Gateway | sessionKey | Gateway RPC | Gateway event | ✅ |
| **混合方案** | Webhook | agent_id | Gateway RPC | Gateway event | ✅ |

---

## ✅ 混合方案优势

1. **完整认证** ✅
   - Token 验证（外部 API）
   - 自动注册
   - Workspace 管理

2. **灵活记忆** ✅
   - 按 agent_id 管理
   - 独立的聊天记录
   - 可自定义上下文

3. **流式输出** ✅
   - Gateway 原生支持
   - 实时显示
   - 最佳用户体验

4. **最佳实践** ✅
   - sessionKey = agent:{agent_id}:main
   - 利用 Gateway 的完整功能
   - 同时保持独立的数据管理

---

## 🔑 关键映射

**核心概念**：
```python
# Token → agent_id（Webhook 管理）
token = "MTgjI2xhaWh1aUBmb3VyaWVyYWxwaGEuY29tIyMxNzY0MDU0NTE5IyNwbGFudF90ZXN0IyMwIyMxIyN1c2Vy"
agent_id = "qc-1801b7ff6f34"  # SHA256(token)[:12]

# agent_id → sessionKey（Gateway 使用）
session_key = f"agent:{agent_id}:main"
# 例如：agent:qc-1801b7ff6f34:main

# 数据存储（Webhook 管理）
chat_file = f"quantclaw_chats/{agent_id}.jsonl"
workspace = f"~/clawd-{agent_id}/"
```

---

## 📊 数据流向

### 发送消息
```
用户消息
    ↓
保存到 quantclaw_chats/{agent_id}.jsonl  ← Webhook 管理
    ↓
构建上下文（最近 20 条）
    ↓
发送到 Gateway: chat.send
sessionKey: agent:{agent_id}:main        ← Gateway 处理
```

### 接收响应
```
Gateway 流式事件
event: "agent"
stream: "assistant"
sessionKey: agent:{agent_id}:main
    ↓
过滤：只处理当前 agent_id 的事件
    ↓
转发到客户端 WebSocket                   ← 流式输出
    ↓
lifecycle phase: "end"
    ↓
保存完整回复到 quantclaw_chats/{agent_id}.jsonl
```

---

## 🔧 兼容性处理

### Gateway Session 自动创建

**问题**：首次使用时 `agent:{agent_id}:main` 的 session 不存在

**解决**：Gateway 会自动创建 session

**验证**：
```bash
# 检查 session 是否创建
ls ~/.clawdbot/agents/{agent_id}/sessions/
```

### Workspace 发现

**问题**：Gateway 如何找到 workspace？

**解决 1**：使用 `clawd-` 前缀（自动发现）
```python
workspace = f"~/clawd-{agent_id}"  # Gateway fallback 机制
```

**解决 2**：配置 agents-config.json
```json
{
  "agents": {
    "list": [
      {
        "id": "qc-1801b7ff6f34",
        "name": "QuantClaw - u_1801b7ff6f34",
        "workspace": "/home/ubuntu/clawd-qc-1801b7ff6f34"
      }
    ]
  }
}
```

---

## 🎨 前端体验

### 流式输出效果

**客户端收到的消息序列**：
```javascript
// 1. 历史记录
{type: 'history', messages: [...]}

// 2. 用户发送消息后
{type: 'status', status: 'typing'}

// 3. 流式响应（逐字显示）
{type: 'stream', delta: '回', text: '回'}
{type: 'stream', delta: '测', text: '回测'}
{type: 'stream', delta: '6', text: '回测6'}
{type: 'stream', delta: '0', text: '回测60'}
{type: 'stream', delta: '8', text: '回测608'}
{type: 'stream', delta: '7', text: '回测6087'}
{type: 'stream', delta: '结', text: '回测6087结'}
...

// 4. 完成
{type: 'done'}
```

---

## 💪 完整优势

| 特性 | 纯 CLI | 纯 Gateway | 混合方案 |
|------|--------|-----------|---------|
| Token 认证 | ❌ | ❌ | ✅ |
| 自动注册 | ❌ | ❌ | ✅ |
| agent_id 管理 | ✅ | ❌ | ✅ |
| Workspace 管理 | ✅ | ❌ | ✅ |
| 流式输出 | ❌ | ✅ | ✅ |
| 独立记忆 | ✅ | ❌ | ✅ |
| 实现复杂度 | 低 | 中 | 高 |

---

## ⚠️ 注意事项

### 1. Session 管理

**混合方案中**：
- Workspace 由 Webhook 创建和管理
- Session 由 Gateway 自动创建
- 两者通过 `agent_id` 关联

### 2. 历史记录

**双重存储**：
- `quantclaw_chats/{agent_id}.jsonl` ← Webhook 管理
- `~/.clawdbot/agents/{agent_id}/sessions/*.jsonl` ← Gateway 管理

**建议**：
- 以 Webhook 的记录为主（用于展示历史）
- Gateway 的 session 作为上下文（Agent 内部使用）

### 3. 上下文构建

**方案 A**：由 Webhook 构建（推荐）
```python
# Webhook 构建上下文
context = memory_manager.get_recent_context(agent_id, limit=20)
full_message = f'{context}\n\n用户消息：{text}'

# 发送完整消息给 Gateway
await gateway_ws.send_json({
    'method': 'chat.send',
    'params': {
        'sessionKey': session_key,
        'message': full_message
    }
})
```

**方案 B**：让 Gateway 管理（自动）
```python
# 不构建上下文，直接发送
await gateway_ws.send_json({
    'method': 'chat.send',
    'params': {
        'sessionKey': session_key,
        'message': text  # 只发送当前消息
    }
})

# Gateway 自动从 session 文件加载历史
```

**推荐**：方案 A（Webhook 管理上下文）
- ✅ 更灵活的上下文控制
- ✅ 可以实现语义检索
- ✅ 数据一致性更好

---

## 🚀 实现步骤

### 1. 修改 app_v2.py

在 `handle_websocket` 函数中：
- 保留 Token 认证部分
- 添加 Gateway WebSocket 连接
- 添加流式事件监听
- 添加消息转发逻辑

### 2. 测试流程

1. Token 认证 → 获取 agent_id ✅
2. WebSocket 连接 → 加载历史 ✅
3. 发送消息 → Gateway RPC ⏳
4. 接收流式响应 → 转发客户端 ⏳
5. 保存完整回复 ⏳

---

## 📋 代码变更清单

- [ ] 添加 `complete_handshake()` 函数
- [ ] 修改 `handle_websocket()` 函数
- [ ] 添加 Gateway WebSocket 连接
- [ ] 添加流式事件监听
- [ ] 添加消息转发逻辑
- [ ] 测试验证

---

*设计时间：2026-05-21*
