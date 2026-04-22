# QuantClaw Server

Python 服务端，支持：
- REST API 发送/接收消息
- WebSocket 实时双向通信
- SSE (Server-Sent Events) 消息推送
- 聊天记录本地存储

## 安装

```bash
cd server
pip install -r requirements.txt
```

## 配置

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `QUANTCLAW_WEBHOOK_URL` | `http://localhost:3000/webhook/quantclaw` | Clawdbot Webhook |
| `QUANTCLAW_WEBHOOK_SECRET` | - | Webhook 签名密钥 |
| `QUANTCLAW_GATEWAY_URL` | (自动) | Clawdbot Gateway RPC 地址 |
| `QUANTCLAW_DATA_DIR` | `./data` | 数据存储目录 |
| `QUANTCLAW_HOST` | `0.0.0.0` | 监听地址 |
| `QUANTCLAW_PORT` | `5000` | 监听端口 |

## 运行

```bash
# 开发模式
python app.py

# 生产模式 (支持 WebSocket)
gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 -b 0.0.0.0:5000 app:app
```

## API 接口

### REST API

| 接口 | 方法 | 说明 |
|------|------|------|
| `/chat` | POST | 发送消息 |
| `/history` | GET | 获取历史记录 |
| `/sessions` | GET | 列出会话 |
| `/sessions/{id}` | DELETE | 删除会话 |
| `/sessions/{id}/clear` | POST | 清空会话 |
| `/export` | GET | 导出聊天记录 |
| `/health` | GET | 健康检查 |

### WebSocket

连接地址: `ws://localhost:5000/ws`

**消息格式：**

```javascript
// 1. 认证 (连接后首先发送)
{"type": "auth", "api_key": "qc_xxx", "session_id": "my-session"}

// 2. 发送聊天消息
{"type": "chat", "message": "查询 BTC 价格"}

// 3. 获取历史
{"type": "get_history", "limit": 50}

// 4. 清空会话
{"type": "clear"}

// 5. 心跳
{"type": "ping"}
```

**接收消息：**

```javascript
// 认证成功 (包含用户信息)
{"type": "auth_success", "session_id": "xxx", "client_id": "xxx", "user_id": "alice", "agent_id": "qc-alice"}

// 认证失败
{"type": "auth_failed", "error": "Invalid API key"}

// 历史消息
{"type": "history", "messages": [...]}

// 新消息
{"type": "message", "role": "user|assistant", "content": "...", "message_id": "...", "timestamp": "..."}

// 消息被拒绝
{"type": "rejected", "error": "该问题与量化交易无关..."}

// 状态
{"type": "status", "status": "typing|idle"}

// 错误
{"type": "error", "error": "..."}

// 心跳响应
{"type": "pong", "timestamp": "..."}
```

### SSE (Server-Sent Events)

连接: `GET /sse?api_key=xxx&session_id=xxx`

**事件类型：**
- `connected` - 连接成功
- `history` - 历史消息
- `message` - 新消息
- `rejected` - 消息被拒绝
- `cleared` - 会话已清空
- `ping` - 心跳

## 使用示例

### cURL (REST)

```bash
# 发送消息
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"api_key":"qc_xxx","message":"查询 BTC 价格","session_id":"test"}'

# 获取历史
curl "http://localhost:5000/history?api_key=qc_xxx&session_id=test&limit=20"

# 列出会话
curl "http://localhost:5000/sessions?api_key=qc_xxx"
```

### JavaScript (WebSocket)

```javascript
const ws = new WebSocket('ws://localhost:5000/ws');

ws.onopen = () => {
  // 认证
  ws.send(JSON.stringify({
    type: 'auth',
    api_key: 'qc_xxx',
    session_id: 'my-session'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch (data.type) {
    case 'auth_success':
      console.log('认证成功:', data.session_id);
      break;
    case 'history':
      console.log('历史消息:', data.messages);
      break;
    case 'message':
      console.log(`${data.role}: ${data.content}`);
      break;
    case 'status':
      console.log('状态:', data.status);
      break;
    case 'rejected':
      console.log('被拒绝:', data.error);
      break;
    case 'error':
      console.error('错误:', data.error);
      break;
  }
};

// 发送消息
function sendMessage(message) {
  ws.send(JSON.stringify({
    type: 'chat',
    message: message
  }));
}

sendMessage('查询 BTC 价格');
```

### JavaScript (SSE)

```javascript
const eventSource = new EventSource(
  'http://localhost:5000/sse?api_key=qc_xxx&session_id=my-session'
);

eventSource.addEventListener('connected', (e) => {
  console.log('连接成功:', JSON.parse(e.data));
});

eventSource.addEventListener('history', (e) => {
  console.log('历史消息:', JSON.parse(e.data));
});

eventSource.addEventListener('message', (e) => {
  const msg = JSON.parse(e.data);
  console.log(`${msg.role}: ${msg.content}`);
});

eventSource.addEventListener('ping', (e) => {
  console.log('心跳:', JSON.parse(e.data));
});

eventSource.onerror = (e) => {
  console.error('SSE 错误');
};

// SSE 只能接收，发送需要用 REST API
fetch('http://localhost:5000/chat', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    api_key: 'qc_xxx',
    message: '查询 BTC 价格',
    session_id: 'my-session'
  })
});
```

### Python

```python
import websocket
import json
import threading

API_KEY = "qc_xxx"
SESSION_ID = "my-session"

def on_message(ws, message):
    data = json.loads(message)
    print(f"Received: {data}")

def on_open(ws):
    # 认证
    ws.send(json.dumps({
        "type": "auth",
        "api_key": API_KEY,
        "session_id": SESSION_ID
    }))

ws = websocket.WebSocketApp(
    "ws://localhost:5000/ws",
    on_open=on_open,
    on_message=on_message
)

# 在后台运行
thread = threading.Thread(target=ws.run_forever)
thread.start()

# 发送消息
ws.send(json.dumps({
    "type": "chat",
    "message": "查询 BTC 价格"
}))
```

## 数据存储

```
data/
└── chats/
    └── {api_key_hash}/
        ├── default.json
        ├── session-1.json
        └── session-2.json
```

消息格式：
```json
{
  "role": "user|assistant|system",
  "content": "消息内容",
  "timestamp": "2024-01-15T10:30:00",
  "message_id": "abc123",
  "metadata": {}
}
```

## Docker

```bash
docker build -t quantclaw-server .
docker run -p 5000:5000 -v ./data:/app/data quantclaw-server
```
