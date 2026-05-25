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
        self.users = {}  # token -> user_record
        self.user_index = {}  # user_id -> token
        
        # 展开路径
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
        """根据 token 查找用户"""
        return self.users.get(token)
    
    def find_by_user_id(self, user_id: str) -> Optional[Dict]:
        """根据 user_id 查找用户"""
        token = self.user_index.get(user_id)
        return self.users.get(token) if token else None
    
    async def auto_register(self, token: str) -> Dict:
        """
        自动注册新用户
        
        流程：
        1. 检查 token 是否已注册
        2. 调用外部 API 验证 token 真实性
        3. 生成唯一 agent_id (qc-{hash})
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
            logger.info(f'✅ Token already registered: {existing_user["userId"]}')
            return existing_user
        
        # 2. 验证 token（调用外部 API）
        validation = await self.validator.validate(token)
        if not validation['valid']:
            raise ValueError(validation['message'])
        
        logger.info(f'✅ Token validated successfully')
        
        # 3. 生成唯一 agent_id（与 TypeScript 版本一致）
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
        
        logger.info(f'🎉 Registered new user: {user_id} (agent: {agent_id})')
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
            'agentId': user['agentId'],
            'token': user['token'],
            'workspace': user.get('workspace'),
            'createdAt': user.get('createdAt'),
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
