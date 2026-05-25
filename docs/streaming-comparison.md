# 流式输出对比和实现方案

## 📊 当前状态

### quantclaw-webhook.py（纯 HTTP）

**实现方式**：
```python
result = subprocess.run(
    cmd,
    capture_output=True,  # 等待完整输出
    text=True,
    timeout=300
)

# 解析完整响应
response = json.loads(result.stdout)
reply_text = ...

# 一次性返回
return web.json_response({
    'success': True,
    'reply': reply_text  # 完整文本
})
```

**特点**：
- ❌ **不是流式**：等待 Clawdbot 完全执行完
- ❌ 用户体验差：长时间无反馈
- ✅ 实现简单
- ✅ 适合短响应

---

### app_v2.py（WebSocket）

**实现方式**：
```python
result = subprocess.run(
    cmd,
    capture_output=True,  # 同样等待完整输出
    text=True,
    timeout=300
)

# 解析后发送
await ws_client.send_json({
    'type': 'message',
    'role': 'assistant',
    'content': reply_text  # 完整文本
})
```

**特点**：
- ❌ **不是流式**：等待完整输出
- ✅ 有"正在输入"状态提示
- ✅ WebSocket 连接保持
- ❌ 实际响应时长没有改善

---

## 🎯 流式输出方案

### 方案 A：使用 subprocess.Popen（推荐）

**原理**：逐行读取 Clawdbot 的标准输出

```python
import asyncio
import subprocess

async def stream_clawdbot(agent_id: str, message: str):
    """流式调用 Clawdbot"""
    cmd = [
        'clawdbot', 'agent',
        '--to', f'qc-{agent_id}',
        '--message', message,
    ]
    
    # 使用 Popen 而不是 run
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, 'HOME': str(Path.home())}
    )
    
    # 逐行读取输出
    full_response = []
    
    # 非阻塞读取
    while True:
        line = await asyncio.get_event_loop().run_in_executor(
            None, process.stdout.readline
        )
        
        if not line:
            break
        
        # 发送每一行（或累积的部分）
        full_response.append(line)
        yield line.strip()
    
    # 等待进程结束
    await asyncio.get_event_loop().run_in_executor(
        None, process.wait
    )
    
    return ''.join(full_response)
```

**WebSocket 集成**：
```python
# 在 handle_websocket 中
async for chunk in stream_clawdbot(agent_id, text):
    # 发送流式片段
    await ws_client.send_json({
        'type': 'stream',
        'delta': chunk  # 增量文本
    })

# 最后发送完成标志
await ws_client.send_json({
    'type': 'done'
})
```

**优点**：
- ✅ 真正的流式输出
- ✅ 用户立即看到响应
- ✅ 体验接近 ChatGPT

**缺点**：
- ❌ 实现复杂
- ❌ 需要处理并发读取
- ❌ Clawdbot 本身是否支持流式输出？

---

### 方案 B：假流式（分段发送）

**原理**：等待完整响应后，分段发送

```python
async def fake_stream_response(ws_client, reply_text: str, chunk_size: int = 50):
    """假流式：分段发送完整响应"""
    words = reply_text.split()
    
    for i in range(0, len(words), chunk_size):
        chunk = ' '.join(words[i:i + chunk_size])
        
        await ws_client.send_json({
            'type': 'stream',
            'delta': chunk
        })
        
        # 模拟打字延迟
        await asyncio.sleep(0.05)
    
    # 发送完成标志
    await ws_client.send_json({
        'type': 'done'
    })
```

**使用**：
```python
# 获取完整响应
result = subprocess.run(cmd, ...)
reply_text = parse_response(result.stdout)

# 假流式发送
await fake_stream_response(ws_client, reply_text)
```

**优点**：
- ✅ 实现简单
- ✅ 提升用户体验
- ✅ 不依赖 Clawdbot 支持

**缺点**：
- ❌ 不是真正的流式
- ❌ 总时长没有改善
- ❌ 用户仍需等待生成完成

---

### 方案 C：Gateway Event Stream（真流式）

**原理**：直接监听 Gateway 的 agent 事件流

```python
async def listen_gateway_stream(session_key: str):
    """监听 Gateway 的 agent 流式事件"""
    async with aiohttp.ClientSession() as session:
        gateway_url = f'{GATEWAY_WS}?token={GATEWAY_TOKEN}'
        
        async with session.ws_connect(gateway_url) as ws:
            # 握手
            await complete_handshake(ws)
            
            # 发送消息
            await ws.send_json({
                'type': 'req',
                'id': 'msg_1',
                'method': 'chat.send',
                'params': {
                    'sessionKey': session_key,
                    'message': message
                }
            })
            
            # 监听流式响应
            async for msg in ws:
                data = json.loads(msg.data)
                
                if data.get('event') == 'agent':
                    stream = data['payload'].get('stream')
                    
                    if stream == 'assistant':
                        # 流式文本片段
                        delta = data['payload']['data'].get('delta', '')
                        text = data['payload']['data'].get('text', '')
                        
                        yield {
                            'delta': delta,  # 增量
                            'text': text     # 累积
                        }
                    
                    elif stream == 'lifecycle':
                        phase = data['payload']['data'].get('phase')
                        if phase == 'end':
                            break
```

**WebSocket 转发**：
```python
async for chunk in listen_gateway_stream(session_key):
    await ws_client.send_json({
        'type': 'stream',
        'delta': chunk['delta'],
        'text': chunk['text']
    })
```

**优点**：
- ✅ 真正的流式输出
- ✅ 实时显示
- ✅ 利用 Gateway 现有能力

**缺点**：
- ❌ 依赖 Gateway
- ❌ 需要维护 session
- ❌ 与当前 `--to` 方案不兼容

---

## 🆚 方案对比

| 方案 | 真流式 | 实现难度 | 用户体验 | 依赖 |
|------|--------|---------|---------|------|
| **当前方案** | ❌ | ⭐ | ⭐ | Clawdbot CLI |
| **方案 A: Popen** | ✅ | ⭐⭐⭐ | ⭐⭐⭐ | Clawdbot 支持 |
| **方案 B: 假流式** | ❌ | ⭐⭐ | ⭐⭐ | 无 |
| **方案 C: Gateway** | ✅ | ⭐⭐⭐⭐ | ⭐⭐⭐ | Gateway + session |

---

## 💡 推荐方案

### 短期（快速改善）：方案 B - 假流式

**实现成本**：低  
**改善效果**：中  
**适用场景**：快速优化用户体验

```python
# 只需修改发送逻辑
async def send_response_with_fake_streaming(ws, reply_text):
    words = reply_text.split()
    chunk_size = 10  # 每次10个词
    
    for i in range(0, len(words), chunk_size):
        chunk = ' '.join(words[i:i + chunk_size])
        await ws.send_json({
            'type': 'stream',
            'delta': chunk
        })
        await asyncio.sleep(0.03)  # 30ms 延迟
    
    await ws.send_json({'type': 'done'})
```

---

### 长期（真正流式）：方案 A - Popen

**前提条件**：需要验证 Clawdbot 是否支持流式输出

**测试方法**：
```bash
# 测试 Clawdbot 是否流式输出
clawdbot agent --to test --message "写一个长故事" 2>&1 | while IFS= read -r line; do
  echo "[$line]"
  sleep 0.1
done
```

如果 Clawdbot 本身是流式的，就可以用 Popen 逐行读取。

---

### 企业级（最强）：方案 C - Gateway Stream

**适用场景**：需要完整的 Gateway 功能（工具调用、多轮对话等）

**权衡**：
- 放弃 `--to` 的简单性
- 回到 session 管理
- 但获得完整的流式能力

---

## 🔧 实现示例（方案 B：假流式）

### 修改 app_v2.py

```python
async def send_streaming_response(ws, reply_text: str):
    """假流式发送响应"""
    # 按字符分割（更流畅）
    chunk_size = 5  # 每次5个字符
    
    for i in range(0, len(reply_text), chunk_size):
        chunk = reply_text[i:i + chunk_size]
        
        await ws.send_json({
            'type': 'stream',
            'delta': chunk
        })
        
        # 短暂延迟
        await asyncio.sleep(0.02)
    
    # 完成标志
    await ws.send_json({
        'type': 'done'
    })

# 在 handle_websocket 中使用
result = subprocess.run(cmd, ...)
reply_text = parse_response(result.stdout)

# 使用假流式发送
await send_streaming_response(ws_client, reply_text)

# 保存完整响应
memory_manager.save_message(agent_id, 'assistant', 'QuantClaw', reply_text)
```

---

### 前端接收

```javascript
let fullResponse = '';

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'stream':
            // 累积流式片段
            fullResponse += data.delta;
            // 实时显示
            updateMessage(fullResponse);
            break;
        
        case 'done':
            // 流式结束
            console.log('Streaming complete');
            break;
    }
};
```

---

## 📋 总结

### 当前状态

- ❌ **quantclaw-webhook.py**：不是流式（HTTP 一次性返回）
- ❌ **app_v2.py**：不是流式（等待完整响应后发送）

### 改进建议

**立即可做**：方案 B（假流式）
- 修改 20 行代码
- 显著改善体验
- 无需依赖改动

**未来优化**：方案 A（真流式）
- 需要验证 Clawdbot 支持
- 实现 Popen 异步读取
- 真正的实时响应

---

*更新时间：2026-05-21*
