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
GATEWAY_TOKEN = os.getenv('GATEWAY_TOKEN', 'a9bde4f80151115b2fef2669fd6f1fbb79f0c69cf1487c5781e342eac070e57e')  # 需要从环境变量获取

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

# ============ 持久会话监听器 ============

class PersistentSessionListener:
    """
    后台持久监听器：独立于客户端 WebSocket
    负责持续监听 Agent 会话并保存消息到本地存储
    """
    
    def __init__(self, gateway_ws: str, gateway_token: str, chat_store):
        self.gateway_ws = gateway_ws
        self.gateway_token = gateway_token
        self.chat_store = chat_store
        self.active_listeners = {}  # {session_key: task}
        self.session_states = {}  # {session_key: {'current_response': '', 'response_saved': bool}}
    
    async def start_listener(self, session_key: str, user_id: str, user_token: str = None):
        """为指定 session 启动持久监听器"""
        if session_key in self.active_listeners:
            logger.info(f'Listener already active: {session_key}')
            return
        
        # 初始化状态
        self.session_states[session_key] = {
            'current_response': '',
            'response_saved': False,
            'user_id': user_id,
            'user_token': user_token,
        }
        
        # 启动后台任务
        task = asyncio.create_task(self._listen_loop(session_key))
        self.active_listeners[session_key] = task
        logger.info(f'🎧 Started persistent listener for {session_key} (user: {user_id})')
    
    async def stop_listener(self, session_key: str):
        """停止指定 session 的监听器"""
        task = self.active_listeners.pop(session_key, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            logger.info(f'🔇 Stopped listener for {session_key}')
        
        # 清理状态
        self.session_states.pop(session_key, None)
    
    async def _listen_loop(self, session_key: str):
        """持久监听循环（独立运行，不受客户端影响）"""
        while True:
            try:
                async with aiohttp.ClientSession() as http_session:
                    gateway_url = f'{self.gateway_ws}?token={self.gateway_token}'
                    
                    async with http_session.ws_connect(gateway_url) as gateway_ws:
                        # 握手
                        if not await self._complete_handshake(gateway_ws):
                            logger.error(f'Handshake failed for {session_key}')
                            await asyncio.sleep(5)
                            continue
                        
                        logger.info(f'🔗 Listener connected to Gateway: {session_key}')
                        
                        # 持续监听消息
                        async for msg in gateway_ws:
                            if msg.type == WSMsgType.TEXT:
                                await self._handle_gateway_message(session_key, msg.data)
                            elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                                logger.warning(f'Gateway connection closed for {session_key}')
                                break
                        
            except asyncio.CancelledError:
                # 被主动取消
                logger.info(f'Listener task cancelled: {session_key}')
                break
            except Exception as e:
                logger.error(f'Listener error for {session_key}: {e}')
            
            # 重连延迟
            await asyncio.sleep(5)
    
    async def _complete_handshake(self, gateway_ws) -> bool:
        """完成 Gateway 握手"""
        connect_id = f'conn_listener_{id(gateway_ws)}'
        
        try:
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
                                'auth': {'token': self.gateway_token},
                                'locale': 'zh-CN',
                                'userAgent': 'quantclaw-listener/1.0.0'
                            }
                        }
                        await gateway_ws.send_json(connect_req)
                    
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
    
    async def _handle_gateway_message(self, session_key: str, msg_data: str):
        """处理来自 Gateway 的消息"""
        try:
            data = json.loads(msg_data)
            
            # 忽略心跳
            event_type = data.get('event', '')
            if event_type in ('health', 'tick'):
                return
            
            msg_type = data.get('type', '')
            payload = data.get('payload', {})
            
            # 只处理 event 消息
            if msg_type != 'event':
                return
            
            # 过滤：只处理当前 session 的消息
            msg_session_key = payload.get('sessionKey', '')
            if msg_session_key and msg_session_key != session_key:
                return
            
            state = self.session_states.get(session_key)
            if not state:
                return
            
            # 处理 agent 事件
            if event_type == 'agent':
                stream = payload.get('stream')
                stream_data = payload.get('data', {})
                
                if stream == 'assistant':
                    # 累积响应文本
                    text = stream_data.get('text', '')
                    state['current_response'] = text
                
                elif stream == 'lifecycle':
                    phase = stream_data.get('phase')
                    
                    if phase == 'end':
                        # 保存完整回复
                        if state['user_id'] and state['current_response'] and not state['response_saved']:
                            response_text = state['current_response']
                            logger.info(f'📝 [Listener] Saving response for {state["user_id"]}: {len(response_text)} chars')
                            self.chat_store.append(state['user_id'], 'assistant', response_text)
                            state['response_saved'] = True
                            logger.info(f'✅ [Listener] Message saved, task completed for {session_key}')
                            
                            # 任务完成，停止监听器（避免占用资源）
                            asyncio.create_task(self.stop_listener(session_key))
                        
                        # 重置状态，准备下一轮（虽然监听器会被停止）
                        state['current_response'] = ''
                        state['response_saved'] = False
        
        except json.JSONDecodeError:
            pass
        except Exception as e:
            logger.error(f'Error handling message in listener: {e}')


# ============ 聊天记录存储 ============

class ChatStore:
    """按用户存储聊天记录"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(exist_ok=True, parents=True)
    
    def _get_file(self, user_id: str) -> Path:
        return self.data_dir / f'{user_id}.json'
    
    def load(self, user_id: str) -> list:
        """加载用户的聊天记录"""
        file = self._get_file(user_id)
        if file.exists():
            try:
                return json.loads(file.read_text())
            except:
                return []
        return []
    
    def save(self, user_id: str, messages: list):
        """保存用户的聊天记录"""
        file = self._get_file(user_id)
        file.write_text(json.dumps(messages, ensure_ascii=False, indent=2))
    
    def append(self, user_id: str, role: str, content: str):
        """添加一条消息（防止重复）"""
        messages = self.load(user_id)
        
        # 检查最后一条消息是否重复（防止同一 role 的连续重复消息）
        if messages and messages[-1]['role'] == role and messages[-1]['content'] == content:
            logger.warning(f'⚠️ Duplicate message detected for {user_id}, skipping')
            return messages
        
        messages.append({
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
        })
        # 只保留最近 100 条
        if len(messages) > 100:
            messages = messages[-100:]
        self.save(user_id, messages)
        return messages
    
    def clear(self, user_id: str):
        """清空用户聊天记录"""
        file = self._get_file(user_id)
        if file.exists():
            file.unlink()


# 创建全局实例
chat_store = ChatStore(CHAT_DIR)
persistent_listener = None  # 延迟初始化（需要 GATEWAY_TOKEN）


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
        session_key = f'agent:{agent_id}:{session_id}'

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
        messages = chat_store.load(user_id)

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
        chat_store.clear(user_id)

        return web.json_response({'success': True, 'cleared': True})

    except Exception as e:
        logger.error(f'Clear history error: {e}')
        return web.json_response({'success': False, 'error': str(e)}, status=500)


async def handle_new_conversation(request):
    """新建对话：通过 /new 命令清除上下文（兼容 Lossless-Claw）"""
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
        session_key = f'agent:{agent_id}:main'
        
        # 步骤2：清除本地聊天记录（ChatStore）
        chat_store.clear(user_id)
        logger.info(f'✅ Cleared ChatStore for user: {user_id}')

        # 步骤3：通过 WebSocket 发送 /new 命令（自动清理 OpenClaw + Lossless-Claw）
        try:
            async with aiohttp.ClientSession() as ws_session:
                gateway_url = f'{GATEWAY_WS}?token={GATEWAY_TOKEN}'
                
                async with ws_session.ws_connect(gateway_url) as gateway_ws:
                    connected = False
                    new_sent = False
                    
                    # 设置超时
                    async def timeout_handler():
                        await asyncio.sleep(10)
                        if not new_sent:
                            logger.warning('WebSocket /new command timeout')
                    
                    timeout_task = asyncio.create_task(timeout_handler())
                    
                    try:
                        async for msg in gateway_ws:
                            if msg.type == WSMsgType.TEXT:
                                ws_data = json.loads(msg.data)
                                
                                # 握手
                                if ws_data.get('event') == 'connect.challenge' and not connected:
                                    connect_req = {
                                        'type': 'req',
                                        'id': 'new_conv_connect',
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
                                
                                # 握手成功，发送 /new
                                elif ws_data.get('type') == 'res' and ws_data.get('id') == 'new_conv_connect':
                                    if ws_data.get('ok'):
                                        connected = True
                                        msg_req = {
                                            'type': 'req',
                                            'id': 'send_new',
                                            'method': 'sessions.create',
                                            'params': {
                                                'key': session_key
                                            }
                                        }
                                        await gateway_ws.send_json(msg_req)
                                        logger.info(f'📤 Sent /new command to {session_key}')
                                    else:
                                        logger.error(f'Handshake failed: {ws_data.get("error")}')
                                        break
                                
                                # /new 命令响应
                                elif ws_data.get('type') == 'res' and ws_data.get('id') == 'send_new':
                                    if ws_data.get('ok'):
                                        logger.info(f'✅ /new command executed for {session_key}')
                                        new_sent = True
                                    else:
                                        logger.error(f'/new command failed: {ws_data.get("error")}')
                                    break
                            
                            elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                                logger.warning('WebSocket closed during /new')
                                break
                    
                    finally:
                        timeout_task.cancel()
                        try:
                            await timeout_task
                        except asyncio.CancelledError:
                            pass
            
            if new_sent:
                logger.info(f'🎉 Session reset via /new for: {user_id}, agent: {agent_id}')
                return web.json_response({
                    'success': True,
                    'cleared': True,
                    'sessionReset': True,
                    'method': 'websocket_new_command',
                    'userId': user_id,
                    'agentId': agent_id,
                    'sessionKey': session_key,
                })
            else:
                logger.error('Failed to send /new command (timeout or error)')
                return web.json_response({
                    'success': False,
                    'error': 'Failed to reset session via /new command'
                }, status=500)
        
        except Exception as ws_error:
            logger.error(f'WebSocket /new error: {ws_error}')
            return web.json_response({
                'success': False,
                'error': f'Failed to send /new command: {str(ws_error)}'
            }, status=500)

    except Exception as e:
        logger.error(f'New conversation error: {e}')
        return web.json_response({'success': False, 'error': str(e)}, status=500)


# ============ WebSocket 处理器 ============

async def handle_websocket(request):
    """WebSocket 代理到 Gateway"""
    ws_client = web.WebSocketResponse()
    await ws_client.prepare(request)

    session_key = request.query.get('sessionKey')
    user_id = request.query.get('userId')
    user_token = request.query.get('token')
    
    if not session_key:
        await ws_client.send_json({'type': 'error', 'error': 'Missing sessionKey'})
        await ws_client.close()
        return ws_client

    logger.info(f'WS connect: {session_key} (user: {user_id})')
    
    # 重连时停止该 session 的旧后备监听器（防止重复保存）
    if persistent_listener and session_key in persistent_listener.active_listeners:
        logger.info(f'🔄 Reconnected: stopping old backup listener for {session_key}')
        await persistent_listener.stop_listener(session_key)

    try:
        async with aiohttp.ClientSession() as http_session:
            gateway_url = f'{GATEWAY_WS}?token={GATEWAY_TOKEN}'
            
            async with http_session.ws_connect(gateway_url) as gateway_ws:
                
                # 握手
                connected = False
                connect_id = 'conn_' + str(id(gateway_ws))
                
                async def complete_handshake():
                    nonlocal connected
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
                                        'userAgent': 'quantclaw-server/1.0.0'
                                    }
                                }
                                await gateway_ws.send_json(connect_req)
                            
                            elif data.get('type') == 'res' and data.get('id') == connect_id:
                                if data.get('ok'):
                                    connected = True
                                    logger.info('Gateway connected!')
                                    return True
                                else:
                                    logger.error(f'Connect failed: {data.get("error")}')
                                    return False
                        elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                            return False
                    return False
                
                if not await asyncio.wait_for(complete_handshake(), timeout=10):
                    await ws_client.send_json({'type': 'error', 'error': 'Gateway handshake failed'})
                    return ws_client
                
                msg_counter = [0]
                current_response = ['']
                response_saved = [False]
                
                def next_id():
                    msg_counter[0] += 1
                    return f'msg_{msg_counter[0]}'
                
                async def handle_client_messages():
                    """处理来自客户端的消息"""
                    async for msg in ws_client:
                        if msg.type == WSMsgType.TEXT:
                            try:
                                data = json.loads(msg.data)
                                msg_type = data.get('type', 'message')
                                
                                if msg_type == 'ping':
                                    await ws_client.send_json({'type': 'pong'})
                                    continue
                                elif msg_type == 'history':
                                    if user_id:
                                        messages = chat_store.load(user_id)
                                        await ws_client.send_json({
                                            'type': 'history',
                                            'messages': messages,
                                        })
                                        logger.info(f'Sent local history: {len(messages)} messages')
                                else:
                                    text = data.get('text') or data.get('message', '')
                                    if text:
                                        current_response[0] = ''
                                        response_saved[0] = False
                                        
                                        rpc_msg = {
                                            'type': 'req',
                                            'id': next_id(),
                                            'method': 'chat.send',
                                            'params': {
                                                'sessionKey': session_key,
                                                'message': text
                                            }
                                        }
                                        await gateway_ws.send_json(rpc_msg)
                                        if user_id:
                                            chat_store.append(user_id, 'user', text)
                                        logger.info(f'Sent to gateway: {text[:50]}...')
                            except json.JSONDecodeError:
                                pass
                        elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                            logger.info(f'🔴 Client WS closed/error for {user_id}: {msg.type}')
                            break

                async def handle_gateway_messages():
                    """处理来自 Gateway 的消息"""
                    async for msg in gateway_ws:
                        if msg.type == WSMsgType.TEXT:
                            try:
                                data = json.loads(msg.data)
                                
                                event_type = data.get('event', '')
                                if event_type in ('health', 'tick'):
                                    continue
                                
                                msg_type = data.get('type', '')
                                payload = data.get('payload', {})
                                
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
                                    continue
                                
                                if msg_type == 'event':
                                    msg_session_key = payload.get('sessionKey', '')
                                    
                                    if msg_session_key != session_key:
                                        continue
                                    
                                    if event_type == 'agent':
                                        stream = payload.get('stream')
                                        stream_data = payload.get('data', {})
                                        
                                        logger.debug(f'🎯 Agent event: stream={stream}, session={msg_session_key}')
                                        
                                        if stream == 'assistant':
                                            text = stream_data.get('text', '')
                                            delta = stream_data.get('delta', '')
                                            current_response[0] = text
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
                                                if user_id and current_response[0] and not response_saved[0]:
                                                    response_text = current_response[0]
                                                    logger.info(f'📝 Saving assistant response for {user_id}: {len(response_text)} chars')
                                                    chat_store.append(user_id, 'assistant', response_text)
                                                    response_saved[0] = True
                                                    logger.info(f'✅ Saved assistant response for {user_id}')
                                                elif response_saved[0]:
                                                    logger.info(f'⚠️ Skipped duplicate save for {user_id}')
                                                
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

                logger.info(f'🔗 Starting message handlers for {session_key}')
                
                await asyncio.gather(
                    handle_client_messages(),
                    handle_gateway_messages(),
                    return_exceptions=True
                )
                
                logger.info(f'🔌 Handlers finished for {session_key}')
                
                # 连接结束时的处理
                if user_id and persistent_listener:
                    has_incomplete_response = current_response[0] and not response_saved[0]
                    
                    if has_incomplete_response:
                        logger.warning(f'🚨 Connection closed before lifecycle.end for {user_id}')
                        logger.info(f'📊 Incomplete stream data: {len(current_response[0])} chars (not saving)')
                        logger.info(f'🎧 Starting backup persistent listener')
                        await persistent_listener.start_listener(session_key, user_id, user_token)

    except aiohttp.ClientError as e:
        logger.error(f'Gateway connection error: {e}')
        try:
            await ws_client.send_json({'type': 'error', 'error': f'Gateway connection failed: {e}'})
        except:
            pass
        if user_id and session_key and user_token and persistent_listener:
            logger.info(f'🎧 Starting backup listener due to connection error')
            await persistent_listener.start_listener(session_key, user_id, user_token)
    except Exception as e:
        logger.error(f'WS error: {e}')
        try:
            await ws_client.send_json({'type': 'error', 'error': str(e)})
        except:
            pass
        if user_id and session_key and user_token and persistent_listener:
            logger.info(f'🎧 Starting backup listener due to error')
            await persistent_listener.start_listener(session_key, user_id, user_token)

    logger.info(f'WS disconnect: {session_key}')
    return ws_client


async def handle_health(request):
    return web.json_response({'status': 'ok', 'service': 'quantclaw-docker'})


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
    global persistent_listener
    
    # 检查必需的环境变量
    if not GATEWAY_TOKEN:
        logger.error('❌ GATEWAY_TOKEN not set!')
        raise ValueError('GATEWAY_TOKEN environment variable is required')
    
    # 初始化持久监听器
    persistent_listener = PersistentSessionListener(GATEWAY_WS, GATEWAY_TOKEN, chat_store)
    
    middlewares = []
    if CORS_ENABLED:
        middlewares.append(cors_middleware)
        logger.info(f'CORS enabled. Allowed origins: {ALLOWED_ORIGINS}')
    
    app = web.Application(middlewares=middlewares)
    
    app.router.add_get('/', handle_index)
    app.router.add_get('/health', handle_health)
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
