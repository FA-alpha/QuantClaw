#!/usr/bin/env python3
"""
QuantClaw Webhook Server
Token 验证 + 自动注册 + Workspace 管理

功能：
1. Token 验证（调用外部 API）
2. 自动注册新用户（生成唯一 agent_id）
3. Workspace 创建（模板复制 + skills 软链接）

运行：python3 quantclaw_webhook.py
端口：8080
"""

import json
import hashlib
import os
import shutil
import subprocess
import asyncio
import logging
import base64
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
import aiohttp
from aiohttp import web

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


# ============ Token 验证器 ============

class TokenValidator:
    """Token 验证器 - 调用外部 API 验证 token 真实性"""
    
    def __init__(self, api_url: str, timeout: int = 5):
        self.api_url = api_url
        self.timeout = timeout
        logger.info(f'TokenValidator initialized: {api_url}')
    
    async def validate(self, token: str) -> Dict:
        """
        验证 token
        
        调用外部 API：
        POST https://www.fourieralpha.com/Mobile/Account/usage_info
        Body: {
            'show_type': '2',
            'usertoken': token,
            'app_v': '2.0.0',
            'lang': '1'
        }
        
        Returns:
            {
                'valid': bool,
                'status': int,
                'user_id': str,
                'message': str
            }
        """
        try:
            # 构建请求参数（与 TypeScript 版本一致）
            data = {
                'show_type': '2',
                'usertoken': token,  # 注意：参数名是 usertoken 不是 token
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
            
            # 检查返回值（与 TypeScript 版本逻辑一致）
            if result.get('status') == 1:
                info = result.get('info')
                if isinstance(info, dict):
                    user_type = info.get('user_type', '').strip()
                    if user_type:
                        logger.info(f'✅ Token validated: user_type={user_type}')
                        return {
                            'valid': True,
                            'status': result['status'],
                            'user_id': info.get('user_id') or info.get('email'),
                            'message': 'Token validated'
                        }
            
            # 验证失败
            message = 'Token not logged in' if result.get('info') == 'nologin' \
                      else result.get('message', 'Invalid token')
            
            logger.warning(f'❌ Token validation failed: {message}')
            return {
                'valid': False,
                'status': result.get('status', 0),
                'message': message
            }
            
        except asyncio.TimeoutError:
            logger.error(f'⏰ Token validation timeout')
            return {
                'valid': False,
                'message': 'Validation timeout'
            }
        except Exception as e:
            logger.error(f'❌ Token validation error: {e}')
            return {
                'valid': False,
                'message': f'Validation error: {str(e)}'
            }


# ============ 用户管理器 ============

class UserManager:
    """用户管理器 - Token 映射 + 自动注册 + Workspace 创建"""
    
    def __init__(self, config: Dict, validator: TokenValidator):
        self.config = config
        self.validator = validator
        self.users = {}  # user_key (platform_user_id:account_type:parent_user_id) -> user_record
        self.token_index = {}  # token -> user_key
        self.agent_index = {}  # agent_id -> user_key
        
        # 展开路径
        self.data_path = Path(config['dataPath']).expanduser()
        self.workspace_base = Path(config['workspaceBase']).expanduser()
        self.template_path = Path(config['templatePath']).expanduser()
        self.skills_path = Path(config['skillsPath']).expanduser()
        
        self.load_users()
    
    @staticmethod
    def make_user_key(platform_user_id: str, account_type: str, parent_user_id: str) -> str:
        """
        生成用户唯一键
        
        格式: platform_user_id:account_type:parent_user_id
        例如:
        - 主账号: "18:1:0"
        - 子账号: "4:2:18"
        """
        return f"{platform_user_id}:{account_type}:{parent_user_id}"
    
    @staticmethod
    def decode_token(token: str) -> Optional[Dict]:
        """
        解码 token 提取用户信息
        
        Token 格式（Base64 编码）:
        18##laihui@fourieralpha.com##1779792069##plant_v2##0##1##user
        
        字段说明:
        [0] platform_user_id - 平台用户ID（唯一且不变）
        [1] email - 邮箱
        [2] timestamp - 时间戳
        [3] version - 系统版本
        [4] parent_user_id - 如果是子账号，则为主账号ID；主账号则为0
        [5] account_type - 账号类型：1=主账号，2=子账号
        [6] role - 角色（通常为 'user'）
        
        Returns:
            {
                'platform_user_id': '18',  # 平台用户ID（唯一且不变）
                'email': 'laihui@fourieralpha.com',
                'timestamp': 1779792069,
                'version': 'plant_v2',
                'parent_user_id': '0',  # 主账号ID（0表示是主账号）
                'account_type': '1',  # 1=主账号, 2=子账号
                'role': 'user'
            }
        """
        try:
            decoded = base64.b64decode(token).decode('utf-8')
            parts = decoded.split('##')
            
            if len(parts) >= 7:
                return {
                    'platform_user_id': parts[0],  # 使用平台用户ID作为唯一标识
                    'email': parts[1],
                    'timestamp': int(parts[2]),
                    'version': parts[3],
                    'parent_user_id': parts[4],  # 主账号ID（子账号时有值）
                    'account_type': parts[5],  # 1=主账号, 2=子账号
                    'role': parts[6]
                }
            else:
                logger.warning(f'⚠️ Token format invalid: {len(parts)} parts')
                return None
                
        except Exception as e:
            logger.error(f'❌ Failed to decode token: {e}')
            return None
    
    def load_users(self):
        """从 JSON 文件加载用户"""
        if self.data_path.exists():
            try:
                data = json.loads(self.data_path.read_text())
                for user in data.get('users', []):
                    platform_user_id = user.get('platformUserId')
                    account_type = user.get('accountType', '1')  # 默认主账号
                    parent_user_id = user.get('parentUserId', '0')  # 默认0
                    
                    if platform_user_id:
                        user_key = self.make_user_key(platform_user_id, account_type, parent_user_id)
                        self.users[user_key] = user
                        self.token_index[user['token']] = user_key
                        self.agent_index[user['agentId']] = user_key
                logger.info(f'✅ Loaded {len(self.users)} users from {self.data_path}')
            except Exception as e:
                logger.warning(f'⚠️ Failed to load users: {e}')
    
    def save_users(self):
        """保存用户到 JSON 文件"""
        try:
            self.data_path.parent.mkdir(parents=True, exist_ok=True)
            data = {'users': list(self.users.values())}
            self.data_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            logger.info(f'💾 Saved {len(self.users)} users')
        except Exception as e:
            logger.error(f'❌ Failed to save users: {e}')
    
    def find_by_token(self, token: str) -> Optional[Dict]:
        """根据 token 查找用户（通过解码提取完整用户标识）"""
        # 先尝试从 token_index 查找
        user_key = self.token_index.get(token)
        if user_key:
            return self.users.get(user_key)
        
        # 如果找不到，尝试解码 token 获取完整标识
        token_info = self.decode_token(token)
        if token_info:
            user_key = self.make_user_key(
                token_info['platform_user_id'],
                token_info['account_type'],
                token_info['parent_user_id']
            )
            if user_key in self.users:
                # 更新 token_index 缓存
                self.token_index[token] = user_key
                return self.users[user_key]
        
        return None
    
    def find_by_platform_user_id(self, platform_user_id: str, account_type: str = '1', parent_user_id: str = '0') -> Optional[Dict]:
        """根据平台用户ID查找用户（需要完整标识）"""
        user_key = self.make_user_key(platform_user_id, account_type, parent_user_id)
        return self.users.get(user_key)
    
    def find_by_agent_id(self, agent_id: str) -> Optional[Dict]:
        """根据 agent_id 查找用户"""
        user_key = self.agent_index.get(agent_id)
        return self.users.get(user_key) if user_key else None
    
    async def auto_register(self, token: str) -> Dict:
        """
        自动注册新用户
        
        流程：
        1. 解码 token 提取完整用户信息（platform_user_id + account_type + parent_user_id）
        2. 检查用户是否已注册（用完整标识判断，如果是则更新 token）
        3. 调用外部 API 验证 token 真实性
        4. 生成唯一 agent_id (qc-{user_key_hash})
        5. 创建 workspace
        6. 保存用户记录
        
        Returns:
            {
                'platformUserId': '18',
                'accountType': '1',  # 1=主账号, 2=子账号
                'parentUserId': '0',  # 主账号ID（主账号为0）
                'userId': 'u_4ec9599fc203',
                'email': 'laihui@fourieralpha.com',
                'token': 'client_token_abc123',
                'agentId': 'qc-4ec9599fc203',
                'workspace': '/home/ubuntu/clawd-qc-4ec9599fc203',
                'createdAt': '2026-05-21T13:00:00.000Z',
                'updatedAt': '2026-05-26T11:21:00.000Z',
                'enabled': True
            }
        """
        # 1. 解码 token 提取完整用户信息
        token_info = self.decode_token(token)
        if not token_info:
            raise ValueError('Failed to decode token')
        
        platform_user_id = token_info['platform_user_id']
        account_type = token_info['account_type']
        parent_user_id = token_info['parent_user_id']
        email = token_info['email']
        
        # 生成用户唯一键
        user_key = self.make_user_key(platform_user_id, account_type, parent_user_id)
        
        account_type_label = "主账号" if account_type == "1" else "子账号"
        logger.info(f'👤 Extracted user: {user_key} ({account_type_label}), email: {email}')
        
        # 2. 检查用户是否已注册（使用完整标识）
        existing_user = self.users.get(user_key)
        if existing_user:
            # 用户已存在，更新 token、邮箱和时间戳
            logger.info(f'✅ User exists, updating token: {existing_user["agentId"]}')
            existing_user['token'] = token
            existing_user['email'] = email  # 邮箱可能变化，需要更新
            existing_user['updatedAt'] = datetime.now().isoformat()
            self.token_index[token] = user_key
            self.save_users()
            return existing_user
        
        # 3. 验证 token（调用外部 API）
        validation = await self.validator.validate(token)
        if not validation['valid']:
            raise ValueError(validation['message'])
        
        logger.info(f'✅ Token validated successfully')
        
        # 4. 生成唯一 agent_id（基于完整用户标识，保证主账号和子账号有不同的 ID）
        hash_part = hashlib.sha256(user_key.encode()).hexdigest()[:12]
        user_id = f'u_{hash_part}'
        agent_id = f'qc-{hash_part}'
        workspace = self.workspace_base / f'clawd-{agent_id}'
        
        # 5. 创建 workspace
        self.create_workspace(workspace, agent_id)
        
        # 6. 保存用户记录
        user = {
            'platformUserId': platform_user_id,  # 平台用户ID
            'accountType': account_type,  # 1=主账号, 2=子账号
            'parentUserId': parent_user_id,  # 主账号ID（主账号为0）
            'userId': user_id,  # 内部用户ID
            'email': email,  # 邮箱（可能变化）
            'token': token,
            'agentId': agent_id,
            'workspace': str(workspace),
            'createdAt': datetime.now().isoformat(),
            'updatedAt': datetime.now().isoformat(),
            'enabled': True
        }
        
        self.users[user_key] = user
        self.token_index[token] = user_key
        self.agent_index[agent_id] = user_key
        self.save_users()
        
        logger.info(f'🎉 Registered new user: {user_id} (agent: {agent_id}, user_key: {user_key})')
        return user
    
    def create_workspace(self, workspace: Path, agent_id: str):
        """
        创建用户 workspace
        
        步骤：
        1. 创建目录
        2. 复制模板文件（AGENTS.md, SOUL.md, IDENTITY.md 等）
        3. 创建 skills 软链接
        4. 创建 memory 目录
        5. 更新 openclaw.json 添加 agent 配置
        """
        logger.info(f'📁 Creating workspace: {workspace}')
        workspace.mkdir(parents=True, exist_ok=True)
        
        # 1. 复制模板文件
        if self.template_path.exists():
            md_files = list(self.template_path.glob('*.md'))
            logger.info(f'📄 Found {len(md_files)} template files')
            
            for file in md_files:
                dest = workspace / file.name
                if not dest.exists():
                    shutil.copy2(file, dest)
                    logger.info(f'  ✓ Copied: {file.name}')
        else:
            logger.warning(f'⚠️ Template path not found: {self.template_path}')
        
        # 2. 创建 skills 软链接
        skills_link = workspace / 'skills'
        if not skills_link.exists():
            try:
                skills_link.symlink_to(self.skills_path, target_is_directory=True)
                logger.info(f'🔗 Created skills symlink → {self.skills_path}')
            except Exception as e:
                logger.error(f'❌ Failed to create skills symlink: {e}')
        
        # 3. 创建 memory 目录
        memory_dir = workspace / 'memory'
        memory_dir.mkdir(exist_ok=True)
        logger.info(f'📂 Created memory directory')
        
        # 4. 更新 openclaw.json 添加 agent 配置
        self.add_agent_to_config(agent_id, workspace)
        
        logger.info(f'✅ Workspace created successfully')
    
    def add_agent_to_config(self, agent_id: str, workspace: Path):
        """
        更新 openclaw.json,添加新 agent 配置
        
        配置格式：
        {
          "agents": {
            "list": [
              {
                "id": "qc-169a9a518fa7",
                "name": "QuantClaw User qc-169a9a518fa7",
                "workspace": "/home/node/quantclaw-users/clawd-qc-169a9a518fa7",
                "model": {
                  "primary": "openrouter/anthropic/claude-sonnet-4.5"
                }
              }
            ]
          }
        }
        """
        # 获取 openclaw.json 路径（容器内路径）
        config_path = Path(os.getenv('OPENCLAW_CONFIG_PATH', '/home/node/.openclaw/openclaw.json'))
        
        try:
            # 读取现有配置
            if config_path.exists():
                config_data = json.loads(config_path.read_text())
            else:
                config_data = {}
            
            # 确保 agents.list 数组存在
            if 'agents' not in config_data:
                config_data['agents'] = {}
            if 'list' not in config_data['agents']:
                config_data['agents']['list'] = []
            
            # 检查 agent 是否已存在
            agent_list = config_data['agents']['list']
            exists = any(agent.get('id') == agent_id for agent in agent_list)
            
            if not exists:
                # 添加新 agent
                new_agent = {
                    'id': agent_id,
                    'name': f'QuantClaw User {agent_id}',
                    'workspace': str(workspace)
                }
                agent_list.append(new_agent)
                
                # 保存配置
                config_path.parent.mkdir(parents=True, exist_ok=True)
                config_path.write_text(json.dumps(config_data, indent=2, ensure_ascii=False))
                
                logger.info(f'✅ Added agent to openclaw.json: {agent_id}')
            else:
                logger.info(f'ℹ️ Agent already exists in openclaw.json: {agent_id}')
                
        except Exception as e:
            logger.error(f'❌ Failed to update openclaw.json: {e}')


# ============ HTTP 请求处理器 ============


async def handle_register(request: web.Request):
    """
    用户注册/登录接口
    
    POST /api/register
    Body: {
        "token": "client_token_abc123"
    }
    
    Response (新用户):
    {
        "success": true,
        "isNewUser": true,
        "userId": "u_169a9a518fa7",
        "agentId": "qc-169a9a518fa7",
        "token": "client_token_abc123",
        "workspace": "/home/ubuntu/clawd-qc-169a9a518fa7",
        "createdAt": "2026-05-22T04:00:00.000Z"
    }
    
    Response (已有用户):
    {
        "success": true,
        "isNewUser": false,
        "userId": "u_169a9a518fa7",
        "agentId": "qc-169a9a518fa7",
        "token": "client_token_abc123",
        "createdAt": "2026-05-21T13:00:00.000Z"
    }
    """
    user_manager: UserManager = request.app['user_manager']
    config: Dict = request.app['config']
    
    try:
        body = await request.json()
        token = body.get('token')
        
        if not token:
            return web.json_response({
                'success': False,
                'error': 'Missing token'
            }, status=400)
        
        # 检查是否已注册
        user = user_manager.find_by_token(token)
        is_new_user = False
        
        if not user:
            # 新用户，执行注册
            if not config['autoRegister']:
                return web.json_response({
                    'success': False,
                    'error': 'Auto-registration is disabled'
                }, status=403)
            
            try:
                user = await user_manager.auto_register(token)
                is_new_user = True
                logger.info(f'✅ New user registered: {user["userId"]}')
            except Exception as e:
                logger.error(f'❌ Registration failed: {e}')
                return web.json_response({
                    'success': False,
                    'error': f'Registration failed: {str(e)}'
                }, status=401)
        else:
            # 已有用户
            logger.info(f'✅ Existing user login: {user["userId"]}')
        
        # 检查用户是否被禁用
        if not user.get('enabled', True):
            return web.json_response({
                'success': False,
                'error': 'User is disabled'
            }, status=403)
        
        # 返回注册/登录信息
        return web.json_response({
            'success': True,
            'isNewUser': is_new_user,
            'userId': user['userId'],
            'email': user.get('email'),
            'agentId': user['agentId'],
            'token': user['token'],
            'workspace': user.get('workspace'),
            'createdAt': user.get('createdAt'),
            'updatedAt': user.get('updatedAt'),
            'enabled': user.get('enabled', True)
        })
        
    except Exception as e:
        logger.error(f'❌ Registration error: {e}', exc_info=True)
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)


async def handle_health(request: web.Request):
    """健康检查端点"""
    return web.json_response({
        'status': 'ok',
        'service': 'quantclaw-webhook',
        'timestamp': datetime.now().isoformat()
    })


# ============ 应用初始化 ============

async def init_app():
    """初始化应用"""
    
    # 从环境变量加载配置（带默认值）
    config = {
        'dataPath': os.getenv('QUANTCLAW_DATA_PATH', '~/.quantclaw/users.json'),
        'workspaceBase': os.getenv('QUANTCLAW_WORKSPACE_BASE', '~'),
        'templatePath': os.getenv('QUANTCLAW_TEMPLATE_PATH', '~/work/QuantClaw/templates/agent-workspace'),
        'skillsPath': os.getenv('QUANTCLAW_SKILLS_PATH', '~/work/QuantClaw/skills'),
        'defaultModel': os.getenv('QUANTCLAW_DEFAULT_MODEL', 'openrouter/anthropic/claude-sonnet-4-5'),
        'autoRegister': os.getenv('QUANTCLAW_AUTO_REGISTER', 'true').lower() == 'true',
        'tokenValidation': {
            'apiUrl': os.getenv('QUANTCLAW_TOKEN_API', 'https://www.fourieralpha.com/Mobile/Account/usage_info'),
            'timeoutMs': int(os.getenv('QUANTCLAW_TOKEN_TIMEOUT', '5000'))
        }
    }
    
    logger.info('🚀 Initializing QuantClaw Webhook Server')
    logger.info(f'📁 Data path: {config["dataPath"]}')
    logger.info(f'📂 Workspace base: {config["workspaceBase"]}')
    logger.info(f'🔧 Auto-register: {config["autoRegister"]}')
    
    # 初始化组件
    validator = TokenValidator(
        api_url=config['tokenValidation']['apiUrl'],
        timeout=config['tokenValidation']['timeoutMs'] // 1000
    )
    
    user_manager = UserManager(config, validator)
    
    # 创建应用
    app = web.Application()
    app['config'] = config
    app['user_manager'] = user_manager
    
    # 注册路由
    app.router.add_post('/api/register', handle_register)
    app.router.add_get('/health', handle_health)
    
    logger.info('✅ Application initialized')
    
    return app


# ============ 主入口 ============

if __name__ == '__main__':
    import sys
    
    # 检查依赖
    try:
        import aiohttp
    except ImportError:
        print('❌ Error: aiohttp not installed')
        print('Install: pip3 install aiohttp')
        sys.exit(1)
    
    # 运行应用
    port = int(os.environ.get('PORT', 8080))
    
    print('=' * 60)
    print('🚀 QuantClaw Webhook Server')
    print('=' * 60)
    print(f'📊 Port: {port}')
    print(f'🔗 Register: http://0.0.0.0:{port}/api/register')
    print(f'💚 Health: http://0.0.0.0:{port}/health')
    print('=' * 60)
    
    app = asyncio.run(init_app())
    web.run_app(app, host='0.0.0.0', port=port)
