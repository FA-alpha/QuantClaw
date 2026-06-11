#!/usr/bin/env python3
"""
QuantClaw Server - Docker 版本
提供 HTTP API + WebSocket 代理 + 独立聊天记录存储

与原版 app.py 的区别：
1. 认证调用独立的 quantclaw_webhook.py 服务（端口 8081）
2. Gateway 地址使用容器内地址
"""

import os
import json
import asyncio
import logging
import uuid
import time
import aiohttp
import subprocess
import threading
import re
from aiohttp import web, WSMsgType
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# CORS 配置
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '*').split(',')
CORS_ENABLED = os.getenv('CORS_ENABLED', 'true').lower() == 'true'

# 配置 (Docker 容器内地址)
GATEWAY_URL = os.getenv('GATEWAY_URL', 'http://127.0.0.1:18789')
GATEWAY_WS = os.getenv('GATEWAY_WS', 'ws://127.0.0.1:18789')
GATEWAY_TOKEN = os.getenv('GATEWAY_TOKEN', '94dfe6383735dccc9b4d800c42b653787d550bc13b7fe3a4')  # 需要从环境变量获取

# 认证服务地址（quantclaw_webhook.py 服务）
AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', 'http://127.0.0.1:8081')

STATIC_DIR = Path(__file__).parent / 'static'

# Docker 环境使用独立的数据目录
# 宿主机: /home/ubuntu/work/QuantClaw/server/data
# Docker:  /home/ubuntu/work/QuantClaw/server/data-docker (或容器内独立路径)
DATA_DIR = Path(os.getenv('QUANTCLAW_DATA_DIR', '/home/node/quantclaw/server/data-docker'))

# 确保数据目录存在
DATA_DIR.mkdir(exist_ok=True, parents=True)
CHAT_DIR = DATA_DIR / 'chats'
CHAT_DIR.mkdir(exist_ok=True, parents=True)

logger.info(f'📁 Using data directory: {DATA_DIR}')

# ============ 全局消息监听器 ============

class GlobalMessageListener:
    """
    全局消息监听器（重构版）
    
    设计思路：
    - 服务启动时启动，一直运行
    - 监听所有 Gateway 消息
    - 判断是否是活跃用户（有消息记录文件）
    - 自动保存消息到文件
    
    优势：
    - 简单：不需要动态启停
    - 可靠：不会遗漏消息
    - 高效：一个连接监听所有消息
    """
    
    def __init__(self, gateway_ws: str, chat_store):
        self.gateway_ws = gateway_ws
        self.chat_store = chat_store
        self.running = False
        self.task = None
        
        # 消息缓存：{session_key: current_response}
        self.response_cache = {}
        # 已注册用户：{agent_id: user_id}（handle_auth 时注册）
        self._agent_user = {}
        
        # 连接监控
        self.connection_count = 0  # 总连接次数
        self.reconnect_count = 0    # 重连次数
        self.last_connect_time = None
    
    async def start(self):
        """启动全局监听器"""
        if self.running:
            logger.warning('GlobalListener already running')
            return
        
        self.running = True
        self.task = asyncio.create_task(self._listen_loop())
        logger.info(f'🌍 GlobalMessageListener started (token: {GATEWAY_TOKEN[:20]}...)')
    
    async def stop(self):
        """停止监听器"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info('🌍 GlobalMessageListener stopped')
    
    def register_user(self, agent_id: str, user_id: str):
        """注册用户：auth 时调用，agent_id -> user_id 映射"""
        self._agent_user[agent_id] = user_id
        logger.info(f'📋 Registered user: {agent_id} -> {user_id}')
    
    async def _listen_loop(self):
        """持久监听循环"""
        
        while self.running:
            ws = None
            session = None
            
            try:
                self.connection_count += 1
                self.reconnect_count += 1
                logger.info(f'🔌 GlobalListener connecting... (attempt #{self.reconnect_count}, total: {self.connection_count})')
                
                session = aiohttp.ClientSession()
                gateway_url = f'{self.gateway_ws}?token={GATEWAY_TOKEN}'
                
                ws = await session.ws_connect(
                    gateway_url,
                    autoping=True,
                    heartbeat=30
                )
                
                # 完成握手
                if not await self._complete_handshake(ws):
                    logger.error('❌ GlobalListener handshake failed')
                    await ws.close()
                    await session.close()
                    await asyncio.sleep(5)
                    continue
                
                self.last_connect_time = time.time()
                logger.info(f'✅ GlobalListener connected to Gateway (reconnect #{self.reconnect_count}, total: {self.connection_count})')
                
                # 持续监听
                async for msg in ws:
                    if msg.type == WSMsgType.TEXT:
                        await self._handle_message(msg.data)
                    elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                        logger.warning(f'🔴 GlobalListener connection closed: {msg.type}')
                        break
                
                logger.info('🔌 GlobalListener connection ended normally')
                        
            except asyncio.CancelledError:
                logger.info('🛑 GlobalListener task cancelled')
                break
            except Exception as e:
                logger.error(f'❌ GlobalListener error: {e}')
            finally:
                # 确保清理资源
                if ws and not ws.closed:
                    try:
                        await ws.close()
                        logger.debug('🧹 GlobalListener ws closed')
                    except Exception as e:
                        logger.error(f'Error closing ws: {e}')
                
                if session and not session.closed:
                    try:
                        await session.close()
                        logger.debug('🧹 GlobalListener session closed')
                    except Exception as e:
                        logger.error(f'Error closing session: {e}')
                
                if self.running:
                    logger.info('⏳ GlobalListener reconnecting in 5s...')
                    await asyncio.sleep(5)
    
    async def _complete_handshake(self, ws) -> bool:
        """完成 Gateway 握手（使用成功的方法）"""
        connect_id = f'conn_{id(ws)}'
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    
                    if data.get('event') == 'connect.challenge':
                        connect_req = {
                            'type': 'req',
                            'id': connect_id,
                            'method': 'connect',
                            'params': {
                                'minProtocol': 4,
                                'maxProtocol': 4,
                                'client': {
                                    'id': 'gateway-client',
                                    'version': '1.0.0',
                                    'platform': 'linux',
                                    'mode': 'backend'
                                },
                                'role': 'operator',
                                'scopes': ['operator.read', 'operator.write'],
                                'caps': [],
                                'auth': {'token': GATEWAY_TOKEN},
                                'locale': 'zh-CN',
                                'userAgent': 'quantclaw-listener/1.0.0'
                            }
                        }
                        await ws.send_json(connect_req)
                    
                    elif data.get('type') == 'res' and data.get('id') == connect_id:
                        if data.get('ok'):
                            return True
                        else:
                            logger.error(f'Handshake failed: {data.get("error")}')
                            return False
                elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                    return False
            
            return False
        except asyncio.TimeoutError:
            return False
    
    async def _handle_message(self, data: str):
        """处理 Gateway 消息"""
        try:
            message = json.loads(data)
            
            # 只处理 agent 事件
            if message.get('event') != 'agent':
                return
            
            payload = message.get('payload', {})
            session_key = payload.get('sessionKey', '')
            
            if not session_key:
                return
            
            # 从 session_key 提取 agent_id，查 agent->user 映射
            # session_key 格式: agent:qc-xxx:main
            agent_id = session_key.split(':')[1] if ':' in session_key else ''
            user_id = self._agent_user.get(agent_id)
            if not user_id:
                # 不是已注册的 QuantClaw 用户 → 忽略
                return
            
            # 处理消息
            stream = payload.get('stream')
            stream_data = payload.get('data', {})
            
            if stream == 'assistant':
                # 累积回复文本
                text = stream_data.get('text', '')
                if text:
                    self.response_cache[session_key] = text
            
            elif stream == 'lifecycle':
                phase = stream_data.get('phase')
                
                if phase == 'end':
                    # 回复完成，保存消息
                    response_text = self.response_cache.get(session_key, '')
                    if response_text:
                        logger.info(f'📝 [GlobalListener] Saving response for {user_id}: {len(response_text)} chars')
                        self.chat_store.append(user_id, session_key, 'assistant', response_text)
                        logger.info(f'✅ [GlobalListener] Saved for {user_id}')
                    
                    # 清理缓存
                    self.response_cache.pop(session_key, None)
        
        except json.JSONDecodeError:
            pass
        except Exception as e:
            logger.error(f'[GlobalListener] Handle message error: {e}')


# ============ 聊天记录存储 ============

class ChatStore:
    """按用户+session存储聊天记录（用户目录 → session 文件）"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(exist_ok=True, parents=True)
    
    def _safe_key(self, session_key: str) -> str:
        """agent:qc-xxx:dashboard:uuid -> agent_qc-xxx_dashboard_uuid"""
        return session_key.replace(':', '_').replace('-', '_')
    
    def _user_dir(self, user_id: str) -> Path:
        dir = self.data_dir / user_id
        dir.mkdir(exist_ok=True, parents=True)
        return dir
    
    def _get_file(self, user_id: str, session_key: str) -> Path:
        safe = self._safe_key(session_key)
        return self._user_dir(user_id) / f'{safe}.json'
    
    def _find_latest(self, user_id: str):
        """找用户最新的 session 聊天文件"""
        user_dir = self.data_dir / user_id
        if not user_dir.exists():
            return None
        files = sorted(
            user_dir.glob('*.json'),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        return files[0] if files else None
    

    def load(self, user_id: str, session_key=None) -> list:
        if session_key:
            file = self._get_file(user_id, session_key)
        else:
            file = self._find_latest(user_id)
        if file and file.exists():
            try:
                return json.loads(file.read_text())
            except:
                return []
        return []
    
    def save(self, user_id: str, session_key: str, messages: list):
        file = self._get_file(user_id, session_key)
        file.write_text(json.dumps(messages, ensure_ascii=False, indent=2))
    
    def append(self, user_id: str, session_key: str, role: str, content: str):
        """添加消息（防止同一 role 连续重复）"""
        messages = self.load(user_id, session_key)
        if messages and messages[-1]['role'] == role and messages[-1]['content'] == content:
            logger.warning(f'⚠️ Duplicate message for {user_id}, skipping')
            return messages
        messages.append({
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
        })
        if len(messages) > 100:
            messages = messages[-100:]
        self.save(user_id, session_key, messages)
        return messages
    
    def new_conversation(self, user_id: str, session_key: str):
        """创建新会话文件。同名存在则 rename 旧文件"""
        user_dir = self._user_dir(user_id)
        file = self._get_file(user_id, session_key)
        if file.exists():
            ts = int(time.time())
            backup = user_dir / f'{file.stem}_{ts}.json.bak'
            file.rename(backup)
            logger.info(f'📦 Backup existing chat -> {backup.name}')
        file.write_text('[]')
        logger.info(f'📝 New chat file: {user_id}/{file.name}')
    
    def clear(self, user_id: str, session_key=None):
        """清空指定 session 的聊天记录（兼容旧接口）"""
        if session_key:
            file = self._get_file(user_id, session_key)
        else:
            file = self._find_latest(user_id)
        if file and file.exists():
            file.unlink()

# 创建全局实例
chat_store = ChatStore(CHAT_DIR)
global_listener = None  # 延迟初始化（需要 GATEWAY_TOKEN）


# ============ 认证辅助函数 (调用 quantclaw_webhook.py 服务) ============

async def call_auth_service(token: str) -> dict:
    """
    调用认证服务验证 token
    
    Args:
        token: 用户 token
    
    Returns:
        dict: {
            'success': bool,
            'userId': str,
            'agentId': str,
            'token': str,
            'workspace': str,
            'isNewUser': bool,
            'error'?: str
        }
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{AUTH_SERVICE_URL}/api/register',
                json={'token': token},
                headers={'Content-Type': 'application/json'},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                result = await resp.json()
                
                if not result.get('success'):
                    logger.warning(f'Auth failed: {result.get("error")}')
                    return result
                
                # 成功
                logger.info(f'Auth success: userId={result.get("userId")}, agentId={result.get("agentId")}')
                return result
                
    except asyncio.TimeoutError:
        logger.error('Auth service timeout')
        return {'success': False, 'error': 'Authentication service timeout'}
    except Exception as e:
        logger.error(f'Auth service error: {e}')
        return {'success': False, 'error': f'Authentication failed: {str(e)}'}


async def sync_session_to_webhook(user_id: str, agent_id: str, session_key: str) -> bool:
    """
    同步 sessionKey 到 quantclaw_webhook 用户配置
    
    POST /api/sync-session
    Body: {userId, agentId, sessionKey}
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{AUTH_SERVICE_URL}/api/sync-session',
                json={
                    'userId': user_id,
                    'agentId': agent_id,
                    'sessionKey': session_key,
                },
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                result = await resp.json()
                if result.get('success'):
                    logger.info(f'📡 Synced session to webhook: {user_id} -> {session_key}')
                    return True
                else:
                    logger.warning(f'Sync session failed: {result.get("error")}')
                    return False
    except Exception as e:
        logger.error(f'Sync session error: {e}')
        return False


# ============ HTTP 处理器 ============

async def handle_chat(request):
    """处理聊天请求 - 认证"""
    try:
        data = await request.json()
        message = data.get('message', '').strip()
        token = data.get('token')
        session_id = data.get('sessionId', 'main')

        if not token:
            return web.json_response({'success': False, 'error': 'Missing token'}, status=400)
        if not message:
            return web.json_response({'success': False, 'error': 'Missing message'}, status=400)

        # 调用认证服务
        auth_result = await call_auth_service(token)

        if not auth_result.get('success'):
            error_msg = auth_result.get('error', 'Authentication failed')
            return web.json_response({
                'success': False,
                'error': error_msg
            }, status=401)

        user_id = auth_result.get('userId')
        agent_id = auth_result.get('agentId')
        
        # 生成 sessionKey
        session_key = f'agent:{agent_id}:{session_id}'
        
        # 注意：消息将在WebSocket中保存，这里不重复保存

        return web.json_response({
            'success': True,
            'token': token,
            'userId': user_id,
            'agentId': agent_id,
            'sessionKey': session_key,
            'isNewUser': auth_result.get('isNewUser', False),
            'message': message,
        })

    except json.JSONDecodeError:
        return web.json_response({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f'Chat error: {e}')
        return web.json_response({'success': False, 'error': str(e)}, status=500)


async def handle_auth(request):
    """仅认证，不发消息"""
    try:
        data = await request.json()
        token = data.get('token')
        session_id = data.get('sessionId', 'main')

        if not token:
            return web.json_response({'success': False, 'error': 'Missing token'}, status=400)

        # 调用认证服务
        auth_result = await call_auth_service(token)

        if not auth_result.get('success'):
            return web.json_response(auth_result, status=401)

        agent_id = auth_result.get('agentId')
        user_id = auth_result.get('userId')
        # 从 webhook 拿 sessionKey，不再本地拼接
        session_key = auth_result.get('sessionKey') or f'agent:{agent_id}:{session_id}'

        # 注册用户到 GlobalListener（agent_id -> user_id 映射）
        if global_listener and agent_id and user_id:
            global_listener.register_user(agent_id, user_id)

        return web.json_response({
            'success': True,
            'userId': auth_result.get('userId'),
            'agentId': agent_id,
            'sessionKey': session_key,
            'isNewUser': auth_result.get('isNewUser', False),
        })

    except Exception as e:
        logger.error(f'Auth error: {e}')
        return web.json_response({'success': False, 'error': str(e)}, status=500)


async def handle_history(request):
    """获取聊天历史（从本地存储）"""
    try:
        data = await request.json()
        token = data.get('token')

        if not token:
            return web.json_response({'success': False, 'error': 'Missing token'}, status=400)

        # 先认证获取 userId
        auth_result = await call_auth_service(token)

        if not auth_result.get('success'):
            return web.json_response(auth_result, status=401)

        user_id = auth_result.get('userId')
        agent_id = auth_result.get('agentId')
        session_id = data.get('sessionId', 'main')
        session_key = auth_result.get('sessionKey') or f'agent:{agent_id}:{session_id}'
        messages = chat_store.load(user_id, session_key)

        return web.json_response({
            'success': True,
            'userId': user_id,
            'messages': messages,
        })

    except Exception as e:
        logger.error(f'History error: {e}')
        return web.json_response({'success': False, 'error': str(e)}, status=500)


async def handle_clear_history(request):
    """清空聊天历史"""
    try:
        data = await request.json()
        token = data.get('token')

        if not token:
            return web.json_response({'success': False, 'error': 'Missing token'}, status=400)

        auth_result = await call_auth_service(token)

        if not auth_result.get('success'):
            return web.json_response(auth_result, status=401)

        user_id = auth_result.get('userId')
        agent_id = auth_result.get('agentId')
        session_id = data.get('sessionId', 'main')
        session_key = auth_result.get('sessionKey') or f'agent:{agent_id}:{session_id}'
        chat_store.clear(user_id, session_key)

        return web.json_response({'success': True, 'cleared': True})

    except Exception as e:
        logger.error(f'Clear history error: {e}')
        return web.json_response({'success': False, 'error': str(e)}, status=500)


async def handle_new_conversation(request):
    """新建对话：通过 sessions.create 创建新会话（官方 API，无消息残留）"""
    try:
        data = await request.json()
        token = data.get('token')

        if not token:
            return web.json_response({'success': False, 'error': 'Missing token'}, status=400)

        # 步骤1：认证获取用户信息
        auth_result = await call_auth_service(token)

        if not auth_result.get('success'):
            return web.json_response(auth_result, status=401)

        user_id = auth_result.get('userId')
        agent_id = auth_result.get('agentId')
        main_session_key = f'agent:{agent_id}:main'
        
        # 步骤2：通过 sessions.create 创建新会话
        try:
            async with aiohttp.ClientSession() as ws_session:
                gateway_url = f'{GATEWAY_WS}?token={GATEWAY_TOKEN}'
                
                async with ws_session.ws_connect(
                    gateway_url,
                    autoping=True,
                    heartbeat=30
                ) as gateway_ws:
                    connected = False
                    session_created = False
                    new_session_key = None
                    
                    ws_req_id = str(uuid.uuid4())
                    
                    async def timeout_handler():
                        await asyncio.sleep(10)
                        if not session_created:
                            logger.warning('WebSocket sessions.create timeout')
                    
                    timeout_task = asyncio.create_task(timeout_handler())
                    
                    try:
                        async for msg in gateway_ws:
                            if msg.type == WSMsgType.TEXT:
                                ws_data = json.loads(msg.data)
                                
                                # 握手
                                if ws_data.get('event') == 'connect.challenge' and not connected:
                                    connect_req = {
                                        'type': 'req',
                                        'id': ws_req_id,
                                        'method': 'connect',
                                        'params': {
                                            'minProtocol': 4,
                                            'maxProtocol': 4,
                                            'client': {
                                                'id': 'gateway-client',
                                                'version': '1.0.0',
                                                'platform': 'linux',
                                                'mode': 'backend'
                                            },
                                            'role': 'operator',
                                            'scopes': ['operator.admin'],
                                            'caps': [],
                                            'auth': {'token': GATEWAY_TOKEN},
                                            'locale': 'zh-CN',
                                            'userAgent': 'quantclaw-new-conversation'
                                        }
                                    }
                                    await gateway_ws.send_json(connect_req)
                                
                                # 握手成功，调用 sessions.create
                                elif ws_data.get('type') == 'res' and ws_data.get('id') == ws_req_id:
                                    if ws_data.get('ok'):
                                        connected = True
                                        create_id = str(uuid.uuid4())
                                        create_req = {
                                            'type': 'req',
                                            'id': create_id,
                                            'method': 'sessions.create',
                                            'params': {
                                                'agentId': agent_id,
                                                'parentSessionKey': main_session_key,
                                                'emitCommandHooks': True
                                            }
                                        }
                                        await gateway_ws.send_json(create_req)
                                        logger.info(f'📤 Sent sessions.create for agent:{agent_id}')
                                        ws_req_id = create_id
                                    else:
                                        logger.error(f'Handshake failed: {ws_data.get("error")}')
                                        break
                                
                                # sessions.create 响应（payload 包裹）
                                elif ws_data.get('type') == 'res' and ws_data.get('id') == ws_req_id:
                                    if ws_data.get('ok'):
                                        payload = ws_data.get('payload', {})
                                        new_session_key = payload.get('key', '')
                                        new_session_id = payload.get('sessionId', '')
                                        logger.info(f'✅ Session created: {new_session_key} (sessionId={new_session_id})')
                                        session_created = True
                                    else:
                                        logger.error(f'sessions.create failed: {ws_data.get("error")}')
                                    break
                            
                            elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                                logger.warning('WebSocket closed during sessions.create')
                                break
                    
                    finally:
                        timeout_task.cancel()
                        try:
                            await timeout_task
                        except asyncio.CancelledError:
                            pass
            
            if session_created:
                # 为新 session 创建聊天文件（同名冲突则备份旧文件）
                chat_store.new_conversation(user_id, new_session_key)
                # 同步 sessionKey 到 webhook 用户配置
                await sync_session_to_webhook(user_id, agent_id, new_session_key)
                
                logger.info(f'🎉 New session for user:{user_id}, agent:{agent_id} -> {new_session_key}')
                return web.json_response({
                    'success': True,
                    'sessionReset': True,
                    'method': 'sessions.create',
                    'userId': user_id,
                    'agentId': agent_id,
                    'newSessionKey': new_session_key,
                })
            else:
                logger.error('Failed to create session (timeout or error)')
                return web.json_response({
                    'success': False,
                    'error': 'Failed to create new session'
                }, status=500)
        
        except Exception as ws_error:
            logger.error(f'WebSocket sessions.create error: {ws_error}')
            return web.json_response({
                'success': False,
                'error': f'Failed to create session: {str(ws_error)}'
            }, status=500)

    except Exception as e:
        logger.error(f'New conversation error: {e}')
        return web.json_response({'success': False, 'error': str(e)}, status=500)


# ============ WebSocket 处理器 ============



# ============ WebSocket 处理器（简化版） ============

async def handle_websocket(request):
    """
    WebSocket 代理 - 简化版
    
    职责：
    1. 转发用户消息到 Gateway
    2. 保存用户消息到文件 ✅
    3. 转发 Gateway 回复到客户端（不保存，由 GlobalListener 保存）
    """
    # 消息 ID 计数器
    msg_counter = [0]
    
    def next_id():
        msg_counter[0] += 1
        return f'msg_{msg_counter[0]}'
    
    ws_client = web.WebSocketResponse()
    await ws_client.prepare(request)

    _session_key = request.query.get('sessionKey')
    user_id = request.query.get('userId')
    user_token = request.query.get('token')
    
    if not _session_key or not user_id:
        await ws_client.send_json({'type': 'error', 'error': 'Missing parameters'})
        await ws_client.close()
        return ws_client

    # 可变容器，支持 switch_session 动态切换
    session_key = [_session_key]
    # 追踪 chat.abort 请求 ID，以便 Gateway 响应时通知前端
    pending_abort_id = [None]
    
    logger.info(f'WS connect: {_session_key} (user: {user_id})')
    
    try:
        async with aiohttp.ClientSession() as http_session:
            gateway_url = f'{GATEWAY_WS}?token={GATEWAY_TOKEN}'
            
            async with http_session.ws_connect(
                gateway_url,
                autoping=True,
                heartbeat=30
            ) as gateway_ws:
                
                # 完成握手
                connect_id = f'conn_{session_key[0]}'
                connected = False
                
                # 握手逻辑
                async for msg in gateway_ws:
                    if msg.type == WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        
                        if data.get('event') == 'connect.challenge':
                            connect_req = {
                                'type': 'req',
                                'id': connect_id,
                                'method': 'connect',
                                'params': {
                                    'minProtocol': 4,
                                    'maxProtocol': 4,
                                    'client': {
                                        'id': 'gateway-client',
                                        'version': '1.0.0',
                                        'platform': 'linux',
                                        'mode': 'backend'
                                    },
                                    'role': 'operator',
                                    'scopes': ['operator.read', 'operator.write'],
                                    'caps': [],
                                    'auth': {'token': GATEWAY_TOKEN},
                                    'locale': 'zh-CN',
                                    'userAgent': 'quantclaw-websocket/1.0.0'
                                }
                            }
                            await gateway_ws.send_json(connect_req)
                        
                        elif data.get('type') == 'res' and data.get('id') == connect_id:
                            connected = data.get('ok', False)
                            if connected:
                                logger.info('Gateway connected!')
                            break
                
                if not connected:
                    await ws_client.send_json({'type': 'error', 'error': 'Gateway connection failed'})
                    return ws_client
                
                # 双向转发
                async def forward_client_to_gateway():
                    """客户端 → Gateway"""
                    try:
                        async for msg in ws_client:
                            if msg.type == WSMsgType.TEXT:
                                data = json.loads(msg.data)
                                
                                # 心跳
                                if data.get('type') == 'ping':
                                    await ws_client.send_json({'type': 'pong'})
                                    continue
                                
                                # 历史记录请求
                                if data.get('type') == 'history':
                                    messages = chat_store.load(user_id, session_key[0])
                                    await ws_client.send_json({
                                        'type': 'history',
                                        'messages': messages
                                    })
                                    continue
                                
                                # 切换 session（新建对话后前端发来新 key）
                                if data.get('type') == 'switch_session':
                                    new_key = data.get('sessionKey', '').strip()
                                    if new_key:
                                        old_key = session_key[0]
                                        session_key[0] = new_key
                                        # 同步 sessionKey 到 webhook
                                        await sync_session_to_webhook(user_id, '', new_key)
                                        logger.info(f'🔄 Session switched: {old_key} -> {new_key}')
                                        await ws_client.send_json({
                                            'type': 'session_switched',
                                            'sessionKey': new_key
                                        })
                                    continue
                                
                                # 停止输出（chat.abort）
                                if data.get('method') == 'chat.abort':
                                    abort_id = next_id()
                                    pending_abort_id[0] = abort_id
                                    abort_req = {
                                        'type': 'req',
                                        'id': abort_id,
                                        'method': 'chat.abort',
                                        'params': {
                                            'sessionKey': session_key[0]
                                        }
                                    }
                                    await gateway_ws.send_json(abort_req)
                                    logger.info(f'🛑 Sent chat.abort for {session_key[0]} (id={abort_id})')
                                    continue
                                
                                # 🔑 处理用户消息
                                if data.get('type') == 'message':
                                    message_text = data.get('text', '').strip()
                                    if message_text:
                                        logger.info(f'💬 User message from {user_id}: {len(message_text)} chars')
                                        chat_store.append(user_id, session_key[0], 'user', message_text)
                                        
                                        rpc_msg = {
                                            'type': 'req',
                                            'id': next_id(),
                                            'method': 'chat.send',
                                            'params': {
                                                'sessionKey': session_key[0],
                                                'message': message_text,
                                                'idempotencyKey': str(uuid.uuid4()),
                                            }
                                        }
                                        await gateway_ws.send_json(rpc_msg)
                                    continue
                                
                                # 其他消息直接转发
                                await gateway_ws.send_json(data)
                                
                            elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                                break
                    except Exception as e:
                        logger.error(f'Forward client->gateway error: {e}')
                
                async def forward_gateway_to_client():
                    """Gateway → 客户端（处理格式后转发，不保存）"""
                    current_response = ['']
                    
                    try:
                        async for msg in gateway_ws:
                            if msg.type == WSMsgType.TEXT:
                                try:
                                    data = json.loads(msg.data)
                                    
                                    event_type = data.get('event', '')
                                    if event_type in ('health', 'tick'):
                                        continue
                                    
                                    msg_type = data.get('type', '')
                                    payload = data.get('payload', {})
                                    
                                    # RPC 响应
                                    if msg_type == 'res':
                                        if data.get('error'):
                                            error_msg = data.get('error')
                                            logger.error(f'RPC error: {error_msg}')
                                            await ws_client.send_json({
                                                'type': 'error',
                                                'error': error_msg,
                                            })
                                            await ws_client.send_json({
                                                'type': 'message',
                                                'role': 'system',
                                                'content': f'⚠️ 错误: {error_msg}',
                                            })
                                        # chat.abort 响应：通知前端已收到并处理
                                        if data.get('id') == pending_abort_id[0] and data.get('ok'):
                                            pending_abort_id[0] = None
                                            logger.info('✅ chat.abort acknowledged by Gateway')
                                            await ws_client.send_json({
                                                'type': 'aborted',
                                                'sessionKey': session_key[0],
                                            })
                                        continue
                                    
                                    # Event 消息
                                    if msg_type == 'event':
                                        msg_session_key = payload.get('sessionKey', '')
                                        
                                        if session_key[0] != msg_session_key:
                                            continue
                                        # 不过滤 sessionKey，接收所有消息
                                        
                                        # 处理 agent 流式响应
                                        if event_type == 'agent':
                                            stream = payload.get('stream')
                                            stream_data = payload.get('data', {})
                                            
                                            logger.debug(f'🎯 Agent event: stream={stream}, session={msg_session_key}')
                                            
                                            if stream == 'assistant':
                                                text = stream_data.get('text', '')
                                                delta = stream_data.get('delta', '')
                                                current_response[0] = text
                                                # 发送流式数据到客户端
                                                await ws_client.send_json({
                                                    'type': 'stream',
                                                    'text': text,
                                                    'delta': delta,
                                                })
                                                if len(text) < 100:
                                                    logger.debug(f'🌊 Streaming to {user_id}: {len(text)} chars')
                                            elif stream == 'lifecycle':
                                                phase = stream_data.get('phase')
                                                error = stream_data.get('error')
                                                if error:
                                                    logger.error(f'Agent error: {error}')
                                                    await ws_client.send_json({
                                                        'type': 'error',
                                                        'error': error,
                                                    })
                                                    await ws_client.send_json({
                                                        'type': 'message',
                                                        'role': 'system',
                                                        'content': f'⚠️ Agent 错误: {error}',
                                                    })
                                                if phase == 'end':
                                                    # 发送完成信号（不保存，GlobalListener 负责）
                                                    await ws_client.send_json({
                                                        'type': 'done',
                                                    })
                                        
                                        elif event_type == 'chat':
                                            logger.debug(f'Ignoring chat event: {payload}')
                                            continue
                                    
                                except json.JSONDecodeError:
                                    pass
                            elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                                logger.info(f'🔴 Gateway WS closed/error for {user_id}: {msg.type}')
                                break
                    except Exception as e:
                        logger.error(f'Forward gateway->client error: {e}')
                
                # 并发执行双向转发
                await asyncio.gather(
                    forward_client_to_gateway(),
                    forward_gateway_to_client(),
                    return_exceptions=True
                )
    
    except Exception as e:
        logger.error(f'WS error: {e}')
    
    logger.info(f'WS disconnect: {session_key}')
    return ws_client

async def handle_health(request):
    return web.json_response({'status': 'ok', 'service': 'quantclaw-docker'})


async def handle_connections_status(request):
    """返回连接状态"""
    if global_listener:
        return web.json_response({
            'globalListener': {
                'running': global_listener.running,
                'totalConnections': global_listener.connection_count,
                'reconnectCount': global_listener.reconnect_count,
                'lastConnectTime': global_listener.last_connect_time,
                'responseCacheSize': len(global_listener.response_cache)
            }
        })
    else:
        return web.json_response({'error': 'GlobalListener not initialized'}, status=500)


async def handle_index(request):
    index_file = STATIC_DIR / 'index.html'
    if index_file.exists():
        return web.FileResponse(index_file)
    return web.Response(text='QuantClaw Server (Docker)', content_type='text/plain')


# ============ CORS 中间件 ============

@web.middleware
async def cors_middleware(request, handler):
    """处理 CORS 跨域请求"""
    if not CORS_ENABLED:
        return await handler(request)
    
    if request.method == 'OPTIONS':
        origin = request.headers.get('Origin', '*')
        
        allowed = False
        if '*' in ALLOWED_ORIGINS:
            allowed = True
        elif origin in ALLOWED_ORIGINS:
            allowed = True
        
        if allowed:
            response = web.Response()
            response.headers['Access-Control-Allow-Origin'] = origin if origin != '*' else '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Max-Age'] = '86400'
            return response
        else:
            return web.Response(status=403, text='CORS origin not allowed')
    
    response = await handler(request)
    
    origin = request.headers.get('Origin', '*')
    
    allowed = False
    if '*' in ALLOWED_ORIGINS:
        allowed = True
        origin = '*'
    elif origin in ALLOWED_ORIGINS:
        allowed = True
    
    if allowed:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
    
    return response


def create_app():
    global global_listener
    
    # 检查必需的环境变量
    if not GATEWAY_TOKEN:
        logger.error('❌ GATEWAY_TOKEN not set!')
        raise ValueError('GATEWAY_TOKEN environment variable is required')
    
    # 🌍 初始化 GlobalMessageListener
    global_listener = GlobalMessageListener(GATEWAY_WS, chat_store)
    
    middlewares = []
    if CORS_ENABLED:
        middlewares.append(cors_middleware)
        logger.info(f'CORS enabled. Allowed origins: {ALLOWED_ORIGINS}')
    
    app = web.Application(middlewares=middlewares)
    
    # 🚀 应用启动时启动 GlobalListener
    async def on_startup(app):
        """应用启动回调"""
        if global_listener:
            await global_listener.start()
        logger.info('✅ Application started with GlobalMessageListener')
    
    # 🧹 应用关闭时停止 GlobalListener
    async def on_cleanup(app):
        """应用关闭回调"""
        logger.info('🧹 Cleaning up...')
        if global_listener:
            await global_listener.stop()
        await cleanup_auth_session()
        logger.info('✅ Cleanup complete')
    
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    
    app.router.add_get('/', handle_index)
    app.router.add_get('/health', handle_health)
    app.router.add_get('/api/connections', handle_connections_status)
    app.router.add_post('/api/auth', handle_auth)
    app.router.add_post('/api/chat', handle_chat)
    app.router.add_post('/api/history', handle_history)
    app.router.add_post('/api/clear-history', handle_clear_history)
    app.router.add_post('/api/new-conversation', handle_new_conversation)
    app.router.add_get('/ws', handle_websocket)
    
    if STATIC_DIR.exists():
        app.router.add_static('/static/', STATIC_DIR, name='static')
    
    return app


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))  # 默认8080，与8081的认证服务区分
    logger.info(f'Starting QuantClaw Server (Docker) on port {port}')
    logger.info(f'Gateway: {GATEWAY_URL}')
    logger.info(f'Auth Service: {AUTH_SERVICE_URL}')
    logger.info(f'Data dir: {DATA_DIR}')
    web.run_app(create_app(), host='0.0.0.0', port=port)
