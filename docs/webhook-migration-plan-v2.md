# QuantClaw Webhook 设计方案（修正版）

## 🎯 核心设计

### 关键差异：按 agent_id 而非 chat_id 管理

| 系统 | 识别维度 | 使用场景 |
|------|---------|---------|
| **Lark Webhook** | `chat_id` (群ID) | 多个用户共享一个群，按群隔离 |
| **QuantClaw Webhook** | `agent_id` (用户ID) | 每个用户独立，按用户隔离 |

---

## 📁 目录结构

### Lark 方式（参考）
```
/home/ubuntu/clawd/memory/
├── lark_chats/
│   ├── oc_a1b2c3d4.jsonl      # 按群ID
│   └── oc_e5f6g7h8.jsonl
├── lark_memory/
│   ├── oc_a1b2c3d4/
│   └── oc_e5f6g7h8/
└── lark_media/
    ├── oc_a1b2c3d4/
    └── oc_e5f6g7h8/
```

### QuantClaw 方式（新设计）✅
```
/home/ubuntu/work/QuantClaw/data/
├── quantclaw_chats/
│   ├── qc-169a9a518fa7.jsonl      # 按 agent_id
│   └── qc-1801b7ff6f34.jsonl
├── quantclaw_memory/
│   ├── qc-169a9a518fa7/           # 向量记忆
│   │   ├── embeddings.json
│   │   ├── summary.md
│   │   └── meta.json
│   └── qc-1801b7ff6f34/
└── quantclaw_media/
    ├── qc-169a9a518fa7/           # 媒体文件
    │   ├── 20260521_143025_img.jpg
    │   └── 20260521_143130_audio.opus
    └── qc-1801b7ff6f34/
```

---

## 🔄 消息流程

### 1. 客户端请求
```json
POST /api/chat
{
  "token": "user_client_token_abc123",
  "message": "查询回测6087的结果"
}
```

### 2. Token 验证 → 获取 agent_id
```python
# 验证 token（调用外部API）
validation = await validate_token(token)

# 查找或创建用户
user = user_manager.find_by_token(token)
if not user:
    user = await user_manager.auto_register(token)

# 获取用户的 agent_id
agent_id = user['agentId']  # 例如: qc-169a9a518fa7
```

### 3. 保存消息到该 agent 的记忆
```python
# 聊天记录文件路径
chat_file = f"/home/ubuntu/work/QuantClaw/data/quantclaw_chats/{agent_id}.jsonl"

# 保存到 JSONL
save_message(agent_id, "user", user_name, message_text)

# 同时保存到向量记忆（可选）
if USE_LAYERED_MEMORY:
    memory = get_memory(agent_id)  # 注意：这里用 agent_id 而非 chat_id
    memory.add_message("user", user_name, message_text, timestamp)
```

### 4. 构建上下文
```python
# 获取该 agent 的历史记录
context = get_agent_context(agent_id, limit=20)

# 或使用语义检索
if USE_LAYERED_MEMORY:
    memory = get_memory(agent_id)
    context = memory.build_context(query=message_text)
```

### 5. 调用 Clawdbot
```python
# 使用 --to 参数，以 agent_id 作为虚拟"用户"
cmd = [
    'clawdbot', 'agent',
    '--to', f'qc-{agent_id}',  # 虚拟用户标识
    '--message', f'{context}\n\n用户消息：{message_text}',
    '--json'
]
```

### 6. 保存回复到该 agent 的记忆
```python
# 解析 Clawdbot 响应
reply_text = parse_response(response)

# 保存到该 agent 的聊天记录
save_message(agent_id, "assistant", "QuantClaw", reply_text)

# 同时保存到向量记忆
if USE_LAYERED_MEMORY:
    memory = get_memory(agent_id)
    memory.add_message("assistant", "QuantClaw", reply_text, timestamp)

# 返回给客户端
return {'success': True, 'reply': reply_text}
```

---

## 📝 核心文件格式

### 1. 用户数据 (`~/.quantclaw/users.json`)
```json
{
  "users": [
    {
      "userId": "u_169a9a518fa7",
      "token": "client_token_abc123",
      "agentId": "qc-169a9a518fa7",
      "workspace": "/home/ubuntu/clawd-qc-169a9a518fa7",
      "createdAt": "2026-05-21T05:00:00.000Z",
      "enabled": true
    }
  ]
}
```

### 2. 聊天记录 (`quantclaw_chats/{agent_id}.jsonl`)
```json
{"ts": 1779340055.270, "time": "2026-05-21 13:07:35", "role": "user", "name": "用户A", "text": "查询回测6087"}
{"ts": 1779340058.120, "time": "2026-05-21 13:07:38", "role": "assistant", "name": "QuantClaw", "text": "回测6087结果：..."}
```

### 3. 向量记忆元数据 (`quantclaw_memory/{agent_id}/meta.json`)
```json
{
  "agent_id": "qc-169a9a518fa7",
  "total_messages": 156,
  "last_updated": "2026-05-21T13:07:38.000Z",
  "embedding_model": "text-embedding-3-small",
  "summary_count": 2
}
```

---

## 🔧 关键代码结构

### User Manager
```python
class UserManager:
    def find_by_token(self, token: str) -> Optional[UserRecord]:
        """根据 token 查找用户"""
        return self.users.get(token)
    
    async def auto_register(self, token: str) -> UserRecord:
        """自动注册新用户，分配唯一 agent_id"""
        # 1. 验证 token
        validation = await self.validate_token(token)
        if not validation['valid']:
            raise ValueError('Invalid token')
        
        # 2. 生成唯一 agent_id
        hash_part = hashlib.sha256(token.encode()).hexdigest()[:12]
        agent_id = f"qc-{hash_part}"
        user_id = f"u_{hash_part}"
        
        # 3. 创建 workspace
        workspace = f"/home/ubuntu/clawd-{agent_id}"
        await self.create_workspace(workspace, agent_id)
        
        # 4. 保存用户记录
        user = {
            'userId': user_id,
            'token': token,
            'agentId': agent_id,
            'workspace': workspace,
            'createdAt': datetime.now().isoformat(),
            'enabled': True
        }
        self.users[token] = user
        self.save_users()
        return user
```

### Memory Manager
```python
class AgentMemoryManager:
    """按 agent_id 管理记忆（聊天、媒体、向量）"""
    
    def __init__(self, base_dir: str):
        self.chat_dir = Path(base_dir) / "quantclaw_chats"
        self.memory_dir = Path(base_dir) / "quantclaw_memory"
        self.media_dir = Path(base_dir) / "quantclaw_media"
        
        # 确保目录存在
        for d in [self.chat_dir, self.memory_dir, self.media_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    def get_chat_file(self, agent_id: str) -> Path:
        """获取聊天记录文件"""
        return self.chat_dir / f"{agent_id}.jsonl"
    
    def get_memory_dir(self, agent_id: str) -> Path:
        """获取向量记忆目录"""
        mem_dir = self.memory_dir / agent_id
        mem_dir.mkdir(exist_ok=True)
        return mem_dir
    
    def get_media_dir(self, agent_id: str) -> Path:
        """获取媒体文件目录"""
        media_dir = self.media_dir / agent_id
        media_dir.mkdir(exist_ok=True)
        return media_dir
    
    def save_message(self, agent_id: str, role: str, name: str, 
                     text: str, media_path: Optional[str] = None):
        """保存消息到该 agent 的记录"""
        record = {
            'ts': time.time(),
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'role': role,
            'name': name,
            'text': text
        }
        if media_path:
            record['media'] = media_path
        
        # 保存到 JSONL
        chat_file = self.get_chat_file(agent_id)
        with open(chat_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    def get_recent_context(self, agent_id: str, limit: int = 20) -> str:
        """获取该 agent 的最近上下文"""
        chat_file = self.get_chat_file(agent_id)
        if not chat_file.exists():
            return ""
        
        messages = []
        with open(chat_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    messages.append(json.loads(line.strip()))
                except:
                    pass
        
        messages = messages[-limit:]
        
        context_lines = ["=== 您的历史对话记录 ==="]
        for msg in messages:
            context_lines.append(f"[{msg['time']}] {msg['name']}: {msg['text']}")
        context_lines.append("=== 历史记录结束 ===\n")
        
        return '\n'.join(context_lines)
```

### Message Handler
```python
async def handle_message(token: str, message: str, 
                         user_manager: UserManager,
                         memory_manager: AgentMemoryManager):
    """处理客户端消息"""
    
    # 1. 认证 + 获取 agent_id
    user = user_manager.find_by_token(token)
    if not user:
        if config['autoRegister']:
            user = await user_manager.auto_register(token)
        else:
            raise ValueError('Token not registered')
    
    agent_id = user['agentId']
    
    # 2. 保存用户消息（注意：用 agent_id）
    memory_manager.save_message(agent_id, "user", "用户", message)
    
    # 3. 构建上下文（注意：用 agent_id）
    context = memory_manager.get_recent_context(agent_id, limit=20)
    
    # 或使用语义检索
    # if USE_LAYERED_MEMORY:
    #     memory = get_memory(agent_id)  # 传入 agent_id
    #     context = memory.build_context(query=message)
    
    # 4. 调用 Clawdbot（注意：--to 用 agent_id）
    full_message = f"{context}\n\n用户消息：{message}"
    
    cmd = [
        'clawdbot', 'agent',
        '--to', f'qc-{agent_id}',  # 虚拟用户标识
        '--message', full_message,
        '--json'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    # 5. 解析响应
    reply_text = parse_clawdbot_response(result.stdout)
    
    # 6. 保存 AI 回复（注意：用 agent_id）
    memory_manager.save_message(agent_id, "assistant", "QuantClaw", reply_text)
    
    # 7. 返回给客户端
    return {'success': True, 'reply': reply_text}
```

---

## 🆚 关键对比

| 项目 | Lark Webhook | QuantClaw Webhook |
|------|-------------|------------------|
| **识别维度** | `chat_id` (群ID) | `agent_id` (用户ID) |
| **记忆目录** | `lark_chats/` | `quantclaw_chats/` |
| **文件命名** | `{chat_id}.jsonl` | `{agent_id}.jsonl` |
| **调用命令** | `--to lark-{chat_id}` | `--to qc-{agent_id}` |
| **场景** | 多用户共享一个群 | 单用户独立对话 |
| **上下文** | 群内历史消息 | 用户个人历史消息 |

---

## ✅ 实现检查清单

- [ ] User Manager（token 验证 + agent_id 分配）
- [ ] Agent Memory Manager（按 agent_id 管理记忆）
- [ ] 聊天记录保存（`quantclaw_chats/{agent_id}.jsonl`）
- [ ] 媒体文件保存（`quantclaw_media/{agent_id}/`）
- [ ] 向量记忆支持（`quantclaw_memory/{agent_id}/`）
- [ ] 调用 Clawdbot（`--to qc-{agent_id}`）
- [ ] HTTP API 端点（/api/chat）
- [ ] SystemD 服务配置

---

## 🎯 核心改动总结

1. **Lark 方式**：`chat_id` → 群为单位 → 适合多人共享
2. **QuantClaw 方式**：`agent_id` → 用户为单位 → 适合单用户独立

**所有文件路径和命名都要替换**：
- `lark_chats` → `quantclaw_chats`
- `lark_memory` → `quantclaw_memory`
- `lark_media` → `quantclaw_media`
- `{chat_id}` → `{agent_id}`

---

*修正时间：2026-05-21*
