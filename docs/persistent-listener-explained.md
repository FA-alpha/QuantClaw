# 持久监听器功能说明

## 🎯 问题场景

### 没有持久监听器时

```
用户发送消息 → Gateway 处理（需要30秒）
    ↓ (10秒后)
用户关闭浏览器或网络断开
    ↓
WebSocket 断连
    ↓
❌ Gateway 的响应无处可去
    ↓
❌ 消息丢失，用户看不到回复
```

---

### 有持久监听器时 ✅

```
用户发送消息 → Gateway 处理
    ↓
WebSocket 正常（流式响应中）
    ↓ (10秒后)
用户关闭浏览器
    ↓
检测到断连 → 启动后台监听器
    ↓
✅ 后台监听器继续监听 Gateway
    ↓
✅ 接收完整响应并保存到数据库
    ↓
用户下次连接时可以看到完整回复
```

---

## 🔧 V3 混合版需要的功能

### 当前 V3 的流程

```
1. Token 认证 → 获取 agent_id
2. 连接 Gateway WebSocket
3. 用户发送消息 → subprocess.Popen 异步调用
4. 监听 Gateway 流式事件 → 转发客户端
5. 客户端断连 → ❌ Gateway 监听也断开
```

**问题**：步骤5，客户端断连后没有继续监听

---

### 添加持久监听器后

```
1. Token 认证 → 获取 agent_id
2. 连接 Gateway WebSocket
3. 用户发送消息 → subprocess.Popen 异步调用
4. 监听 Gateway 流式事件 → 转发客户端
5. 客户端断连 → ✅ 启动后台持久监听器
6. ✅ 持久监听器继续监听 Gateway
7. ✅ 保存完整响应到 quantclaw_chats/{agent_id}.jsonl
```

---

## 📝 实现要点

### 1. 复制 PersistentSessionListener 类

从 app.py 复制整个类（约200行）：
- `start_listener()` - 启动后台监听
- `stop_listener()` - 停止监听
- `_listen_loop()` - 持续监听 Gateway
- `_complete_handshake()` - Gateway 握手
- `_handle_gateway_message()` - 处理消息并保存

### 2. 初始化监听器

```python
# 需要 ChatStore（兼容格式）
chat_store = ChatStore(DATA_DIR / 'quantclaw_chats')

# 初始化持久监听器
persistent_listener = PersistentSessionListener(
    GATEWAY_WS,
    GATEWAY_TOKEN,
    chat_store
)
```

### 3. 修改 handle_websocket

在客户端断连时启动后台监听：

```python
async def handle_websocket(request):
    # ... 认证、连接 Gateway ...
    
    try:
        # 处理消息...
        await asyncio.gather(
            handle_client_messages(),
            handle_gateway_messages()
        )
    
    except Exception as e:
        logger.error(f'WebSocket error: {e}')
    
    finally:
        # 关键：客户端断连后，启动后台监听器
        if session_key and user_id:
            await persistent_listener.start_listener(
                session_key,
                user_id,
                token  # 传递 token 用于回测监控
            )
            logger.info(f'🎧 Fallback: started persistent listener for {session_key}')
        
        logger.info(f'🔴 WebSocket disconnected: {agent_id}')
```

### 4. 统一存储格式

**关键**：持久监听器使用 `ChatStore`，需要确保格式统一：

```python
class ChatStore:
    def append(self, user_id: str, role: str, content: str):
        """保存消息（兼容格式）"""
        messages.append({
            'role': role,
            'content': content,  # ← 与前端一致
            'timestamp': datetime.now().isoformat()
        })
```

**存储位置可以统一**：
- 主监听：实时保存到 `quantclaw_chats/{agent_id}.jsonl`
- 后台监听：断连后保存到同一文件
- 用户下次连接加载同一文件

---

## 🔄 完整时序图

### 场景：用户发送长消息后断连

```
T=0s   用户: 发送 "写一篇1000字文章"
       ↓
T=0s   WebSocket: 发送到 Gateway
       subprocess.Popen(['clawdbot', ...])  # 异步
       ↓
T=0.1s Gateway: 开始生成（需要30秒）
       ↓
T=1s   流式响应开始: "标"
       WebSocket 转发 → 客户端显示
       ↓
T=2s   流式: "题：..."
       ↓
T=5s   用户关闭浏览器 ❌
       WebSocket 断连
       ↓
T=5s   检测到断连 → 启动后台监听器 ✅
       persistent_listener.start_listener(session_key, user_id)
       ↓
T=6s   后台监听器: 连接 Gateway ✅
       ↓
T=10s  流式: "第一段..." (后台接收)
       ↓
T=20s  流式: "第二段..." (后台接收)
       ↓
T=30s  完成: phase="end"
       后台监听器: 保存完整文章 ✅
       quantclaw_chats/qc-xxx.jsonl
       ↓
T=60s  用户重新打开网页
       ↓
T=60s  加载历史 → ✅ 看到完整文章！
```

---

## ✅ 优势

### 用户体验

1. **有网时**：实时流式显示 ✅
2. **断网后**：后台继续保存 ✅
3. **重连后**：完整历史加载 ✅

### 技术优势

1. **高可靠性**：消息不会丢失
2. **自动恢复**：断连自动切换到后台模式
3. **资源优化**：响应完成后自动停止监听器

---

## 🔑 关键代码

### 启动后台监听器

```python
# 在 WebSocket finally 块中
finally:
    # 启动后台监听器（断连后继续保存）
    await persistent_listener.start_listener(
        session_key=f"agent:{agent_id}:main",
        user_id=user_id,
        user_token=token
    )
```

### 停止后台监听器

```python
# 用户重新连接时
if session_key in persistent_listener.active_listeners:
    logger.info(f'🔄 Reconnected: stopping old backup listener')
    await persistent_listener.stop_listener(session_key)
```

---

## 📊 与原版对比

| 功能 | app.py | app_v3 (当前) | app_v3 (改进后) |
|------|--------|--------------|----------------|
| Token 认证 | ❌ | ✅ | ✅ |
| 流式输出 | ✅ | ✅ | ✅ |
| 持久监听器 | ✅ | ❌ | ✅ |
| 断连继续保存 | ✅ | ❌ | ✅ |
| 回测监控 | ✅ | ❌ | ✅ (可选) |

---

*等待子任务完成集成...*
