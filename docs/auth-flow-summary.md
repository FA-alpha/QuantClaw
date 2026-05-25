# QuantClaw 鉴权流程总结

## ✅ 现有实现（TypeScript Extension）

### 完整的鉴权流程

```
客户端发送 token
    ↓
1. 检查 token 是否已注册
   - 已注册 → 直接返回用户信息
   - 未注册 → 进入步骤 2
    ↓
2. 调用外部 API 验证 token 真实性
   POST https://www.fourieralpha.com/Mobile/Account/usage_info
   Body: {
     show_type: 2,
     usertoken: "client_token_abc123",
     app_v: "2.0.0",
     lang: "1"
   }
    ↓
3. 检查验证结果
   - status === 1 && info.user_type 有效 → 通过
   - 否则 → 拒绝
    ↓
4. 生成唯一 agent_id
   hash = SHA256(token)[:12]
   agent_id = "qc-{hash}"
   user_id = "u_{hash}"
    ↓
5. 创建 workspace
   路径: ~/clawd-{agent_id}
   - 复制模板文件（AGENTS.md, SOUL.md 等）
   - 创建 skills 软链接
   - 创建 memory 目录
    ↓
6. 保存用户记录
   ~/.quantclaw/users.json
    ↓
7. 返回用户信息
   { userId, agentId, token, workspace }
```

---

## 📝 关键代码位置

### Token 验证器（token-validator.ts）

```typescript
async validate(token: string): Promise<TokenValidationResult> {
  // 调用外部 API
  const result = await this.callApi(token);
  
  // 检查返回值
  if (result.status === 1) {
    if (typeof result.info === 'object' && result.info !== null) {
      const userType = result.info.user_type || '';
      if (userType && userType.trim() !== '') {
        return {
          valid: true,
          status: result.status,
          userId: result.info.user_id || result.info.email,
        };
      }
    }
  }
  
  return { valid: false, message: 'Invalid token' };
}
```

### 自动注册（index.ts）

```typescript
async autoRegister(clientToken: string): Promise<UserRecord> {
  // 1. 检查是否已注册
  const existingUser = this.users.get(clientToken);
  if (existingUser) {
    return existingUser;
  }
  
  // 2. 验证 token
  if (this.tokenValidator) {
    const validation = await this.tokenValidator.validate(clientToken);
    if (!validation.valid) {
      throw new Error(validation.message || 'Invalid token');
    }
  }
  
  // 3. 生成 agent_id
  const hash = crypto.createHash('sha256')
    .update(clientToken)
    .digest('hex')
    .substring(0, 12);
  const userId = `u_${hash}`;
  const agentId = `qc-${hash}`;
  const workspace = `~/clawd-${agentId}`;
  
  // 4. 创建 workspace
  await this.createWorkspace(workspace, userId);
  
  // 5. 保存用户记录
  const user = {
    userId,
    token: clientToken,
    agentId,
    workspace,
    createdAt: new Date().toISOString(),
    enabled: true,
  };
  
  this.users.set(clientToken, user);
  this.saveUsers();
  
  return user;
}
```

### Workspace 创建（index.ts）

```typescript
private async createWorkspace(workspace: string, userId: string) {
  // 创建目录
  if (!fs.existsSync(workspace)) {
    fs.mkdirSync(workspace, { recursive: true });
  }
  
  // 1. 复制模板文件
  const templatePath = '~/work/QuantClaw/templates/agent-workspace';
  const templateFiles = fs.readdirSync(templatePath)
    .filter(f => f.endsWith('.md'));
  
  for (const file of templateFiles) {
    const srcPath = path.join(templatePath, file);
    const destPath = path.join(workspace, file);
    if (!fs.existsSync(destPath)) {
      fs.copyFileSync(srcPath, destPath);
    }
  }
  
  // 2. 创建 skills 软链接
  const skillsLink = path.join(workspace, 'skills');
  const skillsTarget = this.expandPath(this.config.skillsPath);
  if (!fs.existsSync(skillsLink)) {
    fs.symlinkSync(skillsTarget, skillsLink, 'dir');
  }
  
  // 3. 创建 memory 目录
  const memoryDir = path.join(workspace, 'memory');
  if (!fs.existsSync(memoryDir)) {
    fs.mkdirSync(memoryDir, { recursive: true });
  }
}
```

---

## 🐍 Python 实现版本

### 完整代码结构

```python
#!/usr/bin/env python3
"""
QuantClaw Webhook Server
完整的 Token 验证 + 自动注册 + Workspace 管理
"""

import json
import hashlib
import os
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
import aiohttp
from aiohttp import web


class TokenValidator:
    """Token 验证器 - 调用外部 API 验证"""
    
    def __init__(self, api_url: str, timeout: int = 5):
        self.api_url = api_url
        self.timeout = timeout
    
    async def validate(self, token: str) -> Dict:
        """
        验证 token
        
        Returns:
            {
                'valid': bool,
                'status': int,
                'user_id': str,
                'message': str
            }
        """
        try:
            # 构建请求参数（与 TS 版本一致）
            data = {
                'show_type': '2',
                'usertoken': token,  # 注意：参数名是 usertoken
                'app_v': '2.0.0',
                'lang': '1',
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    data=data,  # form-urlencoded
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as resp:
                    result = await resp.json()
            
            # 检查返回值（与 TS 版本逻辑一致）
            if result.get('status') == 1:
                info = result.get('info')
                if isinstance(info, dict):
                    user_type = info.get('user_type', '').strip()
                    if user_type:
                        return {
                            'valid': True,
                            'status': result['status'],
                            'user_id': info.get('user_id') or info.get('email'),
                            'message': 'Token validated'
                        }
            
            # 验证失败
            message = 'Token not logged in' if result.get('info') == 'nologin' \
                      else result.get('message', 'Invalid token')
            
            return {
                'valid': False,
                'status': result.get('status', 0),
                'message': message
            }
            
        except Exception as e:
            return {
                'valid': False,
                'message': f'Validation error: {str(e)}'
            }


class UserManager:
    """用户管理器 - Token 映射 + 自动注册"""
    
    def __init__(self, config: Dict, validator: TokenValidator):
        self.config = config
        self.validator = validator
        self.users = {}  # token -> user_record
        self.user_index = {}  # user_id -> token
        
        self.data_path = Path(config['dataPath']).expanduser()
        self.workspace_base = Path(config['workspaceBase']).expanduser()
        self.template_path = Path(config['templatePath']).expanduser()
        self.skills_path = Path(config['skillsPath']).expanduser()
        
        self.load_users()
    
    def load_users(self):
        """从 JSON 文件加载用户"""
        if self.data_path.exists():
            try:
                data = json.loads(self.data_path.read_text())
                for user in data.get('users', []):
                    self.users[user['token']] = user
                    self.user_index[user['userId']] = user['token']
                print(f'✅ Loaded {len(self.users)} users')
            except Exception as e:
                print(f'⚠️ Failed to load users: {e}')
    
    def save_users(self):
        """保存用户到 JSON 文件"""
        try:
            self.data_path.parent.mkdir(parents=True, exist_ok=True)
            data = {'users': list(self.users.values())}
            self.data_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f'❌ Failed to save users: {e}')
    
    def find_by_token(self, token: str) -> Optional[Dict]:
        """根据 token 查找用户"""
        return self.users.get(token)
    
    async def auto_register(self, token: str) -> Dict:
        """
        自动注册新用户
        
        流程：
        1. 检查 token 是否已注册
        2. 调用外部 API 验证 token
        3. 生成唯一 agent_id
        4. 创建 workspace
        5. 保存用户记录
        
        Returns:
            {
                'userId': 'u_169a9a518fa7',
                'token': 'client_token_abc123',
                'agentId': 'qc-169a9a518fa7',
                'workspace': '/home/ubuntu/clawd-qc-169a9a518fa7',
                'createdAt': '2026-05-21T13:00:00.000Z',
                'enabled': True
            }
        """
        # 1. 检查是否已注册
        existing_user = self.users.get(token)
        if existing_user:
            print(f'✅ Token already registered: {existing_user["userId"]}')
            return existing_user
        
        # 2. 验证 token
        validation = await self.validator.validate(token)
        if not validation['valid']:
            raise ValueError(validation['message'])
        
        print(f'✅ Token validated: {validation.get("user_id")}')
        
        # 3. 生成唯一 agent_id（与 TS 版本一致）
        hash_part = hashlib.sha256(token.encode()).hexdigest()[:12]
        user_id = f'u_{hash_part}'
        agent_id = f'qc-{hash_part}'
        workspace = self.workspace_base / f'clawd-{agent_id}'
        
        # 4. 创建 workspace
        self.create_workspace(workspace, agent_id)
        
        # 5. 保存用户记录
        user = {
            'userId': user_id,
            'token': token,
            'agentId': agent_id,
            'workspace': str(workspace),
            'createdAt': datetime.now().isoformat(),
            'enabled': True
        }
        
        self.users[token] = user
        self.user_index[user_id] = token
        self.save_users()
        
        print(f'🎉 Registered new user: {user_id} (agent: {agent_id})')
        return user
    
    def create_workspace(self, workspace: Path, agent_id: str):
        """
        创建用户 workspace
        
        步骤：
        1. 创建目录
        2. 复制模板文件（AGENTS.md, SOUL.md 等）
        3. 创建 skills 软链接
        4. 创建 memory 目录
        """
        workspace.mkdir(parents=True, exist_ok=True)
        
        # 1. 复制模板文件
        if self.template_path.exists():
            for file in self.template_path.glob('*.md'):
                dest = workspace / file.name
                if not dest.exists():
                    shutil.copy2(file, dest)
                    print(f'📄 Copied template: {file.name}')
        
        # 2. 创建 skills 软链接
        skills_link = workspace / 'skills'
        if not skills_link.exists():
            skills_link.symlink_to(self.skills_path, target_is_directory=True)
            print(f'🔗 Created skills symlink')
        
        # 3. 创建 memory 目录
        memory_dir = workspace / 'memory'
        memory_dir.mkdir(exist_ok=True)
        print(f'📁 Created memory directory')


class AgentMemoryManager:
    """Agent 记忆管理器 - 按 agent_id 管理聊天记录"""
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.chat_dir = self.base_dir / 'quantclaw_chats'
        self.memory_dir = self.base_dir / 'quantclaw_memory'
        self.media_dir = self.base_dir / 'quantclaw_media'
        
        # 确保目录存在
        for d in [self.chat_dir, self.memory_dir, self.media_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    def get_chat_file(self, agent_id: str) -> Path:
        """获取聊天记录文件"""
        return self.chat_dir / f'{agent_id}.jsonl'
    
    def save_message(self, agent_id: str, role: str, name: str, text: str):
        """保存消息到该 agent 的记录"""
        record = {
            'ts': datetime.now().timestamp(),
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'role': role,
            'name': name,
            'text': text
        }
        
        chat_file = self.get_chat_file(agent_id)
        with open(chat_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    def get_recent_context(self, agent_id: str, limit: int = 20) -> str:
        """获取该 agent 的最近上下文"""
        chat_file = self.get_chat_file(agent_id)
        if not chat_file.exists():
            return ''
        
        messages = []
        with open(chat_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    messages.append(json.loads(line.strip()))
                except:
                    pass
        
        messages = messages[-limit:]
        
        context_lines = ['=== 您的历史对话记录 ===']
        for msg in messages:
            context_lines.append(f"[{msg['time']}] {msg['name']}: {msg['text']}")
        context_lines.append('=== 历史记录结束 ===\n')
        
        return '\n'.join(context_lines)


async def handle_chat(request: web.Request):
    """处理聊天请求"""
    user_manager = request.app['user_manager']
    memory_manager = request.app['memory_manager']
    
    try:
        body = await request.json()
        token = body.get('token')
        message = body.get('message')
        
        if not token:
            return web.json_response({'success': False, 'error': 'Missing token'}, status=400)
        if not message:
            return web.json_response({'success': False, 'error': 'Missing message'}, status=400)
        
        # 认证检查
        if message == '__auth_check__':
            user = user_manager.find_by_token(token)
            is_new_user = False
            
            if not user:
                if request.app['config']['autoRegister']:
                    try:
                        user = await user_manager.auto_register(token)
                        is_new_user = True
                    except Exception as e:
                        return web.json_response({
                            'success': False,
                            'error': f'Registration failed: {str(e)}'
                        }, status=401)
                else:
                    return web.json_response({
                        'success': False,
                        'error': 'Token not registered'
                    }, status=401)
            
            return web.json_response({
                'success': True,
                'token': user['token'],
                'userId': user['userId'],
                'agentId': user['agentId'],
                'isNewUser': is_new_user
            })
        
        # 查找用户
        user = user_manager.find_by_token(token)
        if not user:
            if request.app['config']['autoRegister']:
                user = await user_manager.auto_register(token)
            else:
                return web.json_response({
                    'success': False,
                    'error': 'Token not registered'
                }, status=401)
        
        if not user['enabled']:
            return web.json_response({
                'success': False,
                'error': 'User disabled'
            }, status=403)
        
        agent_id = user['agentId']
        
        # 保存用户消息
        memory_manager.save_message(agent_id, 'user', '用户', message)
        
        # 构建上下文
        context = memory_manager.get_recent_context(agent_id, limit=20)
        
        # 调用 Clawdbot
        full_message = f'{context}\n\n用户消息：{message}'
        
        cmd = [
            'clawdbot', 'agent',
            '--to', f'qc-{agent_id}',
            '--message', full_message,
            '--json'
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            env={**os.environ, 'HOME': str(Path.home())}
        )
        
        if result.returncode == 0 and result.stdout:
            try:
                response = json.loads(result.stdout)
                reply_text = ''
                
                # 解析响应（与 lark_webhook.py 类似）
                if 'result' in response and isinstance(response['result'], dict):
                    payloads = response['result'].get('payloads', [])
                    if payloads:
                        texts = [p.get('text', '') for p in payloads if p.get('text')]
                        reply_text = '\n\n'.join(texts)
                
                if not reply_text:
                    reply_text = response.get('reply', '') or response.get('text', '')
                
                if reply_text:
                    # 保存回复
                    memory_manager.save_message(agent_id, 'assistant', 'QuantClaw', reply_text)
                    
                    return web.json_response({
                        'success': True,
                        'reply': reply_text,
                        'agentId': agent_id
                    })
                else:
                    return web.json_response({
                        'success': False,
                        'error': 'No reply from agent'
                    }, status=500)
                    
            except json.JSONDecodeError:
                # 尝试纯文本
                reply_text = result.stdout.strip()
                if reply_text:
                    memory_manager.save_message(agent_id, 'assistant', 'QuantClaw', reply_text)
                    return web.json_response({
                        'success': True,
                        'reply': reply_text,
                        'agentId': agent_id
                    })
        
        return web.json_response({
            'success': False,
            'error': f'CLI returned code {result.returncode}'
        }, status=500)
        
    except Exception as e:
        print(f'❌ Error: {e}')
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)


async def init_app():
    """初始化应用"""
    config = {
        'dataPath': '~/.quantclaw/users.json',
        'workspaceBase': '~/clawd-users',
        'templatePath': '~/work/QuantClaw/templates/agent-workspace',
        'skillsPath': '~/work/QuantClaw/skills',
        'defaultModel': 'openrouter/anthropic/claude-sonnet-4-5',
        'autoRegister': True,
        'tokenValidation': {
            'apiUrl': 'https://www.fourieralpha.com/Mobile/Account/usage_info',
            'timeoutMs': 5000
        }
    }
    
    # 初始化组件
    validator = TokenValidator(
        api_url=config['tokenValidation']['apiUrl'],
        timeout=config['tokenValidation']['timeoutMs'] // 1000
    )
    
    user_manager = UserManager(config, validator)
    memory_manager = AgentMemoryManager('/home/ubuntu/work/QuantClaw/data')
    
    # 创建应用
    app = web.Application()
    app['config'] = config
    app['user_manager'] = user_manager
    app['memory_manager'] = memory_manager
    
    # 注册路由
    app.router.add_post('/api/chat', handle_chat)
    
    return app


if __name__ == '__main__':
    import sys
    
    app = asyncio.run(init_app())
    
    port = 8080
    print(f'🚀 QuantClaw Webhook Server starting on port {port}')
    print(f'📊 Endpoint: http://0.0.0.0:{port}/api/chat')
    
    web.run_app(app, host='0.0.0.0', port=port)
```

---

## 🔑 关键流程总结

### 1. Token 验证
```python
POST https://www.fourieralpha.com/Mobile/Account/usage_info
Body: {
  'show_type': '2',
  'usertoken': token,
  'app_v': '2.0.0',
  'lang': '1'
}

# 检查响应
if response['status'] == 1 and response['info']['user_type']:
    # 有效
else:
    # 无效
```

### 2. 自动注册
```python
# 生成 agent_id
hash = SHA256(token)[:12]
agent_id = f'qc-{hash}'

# 创建 workspace
~/clawd-{agent_id}/
├── AGENTS.md        # 从模板复制
├── SOUL.md
├── skills/          # 软链接到 ~/work/QuantClaw/skills
└── memory/          # 空目录
```

### 3. 消息处理
```python
# 保存到 agent 的记录
quantclaw_chats/{agent_id}.jsonl

# 构建上下文
context = get_recent_context(agent_id)

# 调用 Clawdbot
clawdbot agent --to qc-{agent_id} --message "{context}\n{message}"

# 保存回复
save_message(agent_id, "assistant", reply)
```

---

## ✅ 完整功能清单

- [x] Token 验证（调用外部 API）
- [x] 自动注册（首次 token 验证后创建用户）
- [x] agent_id 生成（SHA256 hash）
- [x] Workspace 创建
- [x] 模板文件复制
- [x] Skills 软链接
- [x] Memory 目录初始化
- [x] 按 agent_id 管理聊天记录
- [x] 上下文构建
- [x] Clawdbot 调用（--to）
- [x] 响应解析和保存

---

*总结时间：2026-05-21*
