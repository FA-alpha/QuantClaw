# 聊天记录格式对比

## 📊 格式差异

### app.py（原版）

**文件格式**：`{user_id}.json`（JSON 数组）

**路径**：`/home/ubuntu/work/QuantClaw/server/data/chats/u_1801b7ff6f34.json`

**内容格式**：
```json
[
  {
    "role": "user",
    "content": "查询回测6087",
    "timestamp": "2026-05-20T06:20:30.110640"
  },
  {
    "role": "assistant",
    "content": "回测6087结果：...",
    "timestamp": "2026-05-20T06:22:04.213083"
  }
]
```

**字段**：
- ✅ `role`: "user" | "assistant"
- ✅ `content`: 消息内容
- ✅ `timestamp`: ISO 时间字符串

---

### app_v3（混合方案）

**文件格式**：`{agent_id}.jsonl`（每行一个 JSON）

**路径**：`/home/ubuntu/work/QuantClaw/data/quantclaw_chats/qc-1801b7ff6f34.jsonl`

**内容格式**：
```json
{"ts": 1779347782.972519, "time": "2026-05-21 07:16:22", "role": "user", "name": "用户", "text": "你好，测试一下"}
{"ts": 1779347787.924478, "time": "2026-05-21 07:16:27", "role": "assistant", "name": "QuantClaw", "text": "回复内容..."}
```

**字段**：
- ❌ `text` 而非 `content`
- ❌ `time` 字符串 + `ts` 时间戳（双重）
- ❌ `name` 字段（"用户" / "QuantClaw"）
- ❌ 缺少 ISO `timestamp`

---

## 🔧 兼容性问题

### 前端期望的格式

```javascript
// 前端代码可能这样读取
messages.forEach(msg => {
  const role = msg.role;
  const content = msg.content;  // ← 期望 content
  const timestamp = msg.timestamp;  // ← 期望 ISO 格式
});
```

### V3 当前返回的格式

```javascript
// V3 返回
{
  role: "user",
  text: "...",  // ← 前端会读不到（找 content）
  time: "2026-05-21 07:16:22",  // ← 不是 ISO 格式
  ts: 1779347782.972519,
  name: "用户"
}
```

**结果**：前端无法正确显示消息内容 ❌

---

## ✅ 修复方案

### 方案 A：修改 V3 保存格式（推荐）

**目标**：使用与 app.py 相同的格式

```python
class AgentMemoryManager:
    def save_message(self, agent_id: str, role: str, name: str, text: str):
        """保存消息（兼容 app.py 格式）"""
        record = {
            'role': role,
            'content': text,  # ← 改为 content
            'timestamp': datetime.now().isoformat(),  # ← ISO 格式
        }
        
        # 可选：保留额外字段（向后兼容）
        # record['name'] = name
        # record['ts'] = datetime.now().timestamp()
        
        with open(self.get_chat_file(agent_id), 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    def load_history(self, agent_id: str) -> list:
        """加载历史（返回数组格式）"""
        chat_file = self.get_chat_file(agent_id)
        if not chat_file.exists():
            return []
        
        messages = []
        with open(chat_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    msg = json.loads(line.strip())
                    # 只返回必要字段（兼容前端）
                    messages.append({
                        'role': msg['role'],
                        'content': msg['content'],
                        'timestamp': msg['timestamp']
                    })
                except:
                    pass
        
        return messages[-100:]
```

**优点**：
- ✅ 完全兼容现有前端
- ✅ 无需修改前端代码
- ✅ 格式统一

---

### 方案 B：修改前端读取逻辑

**目标**：让前端适配 V3 格式

```javascript
// 兼容两种格式
messages.forEach(msg => {
  const role = msg.role;
  const content = msg.content || msg.text;  // ← 兼容 text
  const timestamp = msg.timestamp || msg.time;  // ← 兼容 time
});
```

**缺点**：
- ❌ 需要修改前端
- ❌ 维护两套格式

---

## 🔧 立即修复

### 修改 app_v3_hybrid.py

```python
# 找到 AgentMemoryManager 类中的 save_message 方法
# 第 185 行左右
```

**修改前**：
```python
record = {
    'ts': datetime.now().timestamp(),
    'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'role': role,
    'name': name,
    'text': text
}
```

**修改后**：
```python
record = {
    'role': role,
    'content': text,  # ← 改为 content
    'timestamp': datetime.now().isoformat(),  # ← ISO 格式
}
```

同时修改 `load_history` 方法返回格式。

---

## 📝 完整对比表

| 字段 | app.py | V3 当前 | V3 修复后 | 前端期望 |
|------|--------|---------|----------|---------|
| `role` | ✅ | ✅ | ✅ | ✅ |
| `content` | ✅ | ❌ (text) | ✅ | ✅ |
| `timestamp` | ✅ (ISO) | ❌ (time) | ✅ (ISO) | ✅ |
| `text` | ❌ | ✅ | ❌ | ❌ |
| `time` | ❌ | ✅ | ❌ | ❌ |
| `ts` | ❌ | ✅ | ❌ | ❌ |
| `name` | ❌ | ✅ | ❌ | ❌ |

**结论**：需要修改 V3，使用 `content` + `timestamp`

---

*分析时间：2026-05-21*
