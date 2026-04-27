#!/usr/bin/env python3
"""
QuantClaw Server - 量化交易助手服务端
提供 HTTP API + WebSocket 代理 + 独立聊天记录存储
"""

import os
import json
import asyncio
import logging
import uuid
import aiohttp
from aiohttp import web, WSMsgType
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# 配置
GATEWAY_URL = os.getenv('GATEWAY_URL', 'http://127.0.0.1:18789')
GATEWAY_WS = os.getenv('GATEWAY_WS', 'ws://127.0.0.1:18789')
GATEWAY_TOKEN = os.getenv('GATEWAY_TOKEN', 'b27f3270bf6c56c09b97327123066079ee9ecbc6cad55400')
WEBHOOK_PATH = '/webhook/quantclaw'
STATIC_DIR = Path(__file__).parent / 'static'
DATA_DIR = Path(__file__).parent / 'data'

# 确保数据目录存在
DATA_DIR.mkdir(exist_ok=True)
CHAT_DIR = DATA_DIR / 'chats'
CHAT_DIR.mkdir(exist_ok=True, parents=True)


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
        """添加一条消息"""
        messages = self.load(user_id)
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


chat_store = ChatStore(CHAT_DIR)


# ============ 认证辅助函数 ============

async def check_auth_token(token: str, session_id: str = 'main') -> dict:
    """
    调用 Gateway Webhook 验证 token
    
    Returns:
        dict: {'success': bool, 'error'?: str, 'needLogin'?: bool, 'userId'?: str, 'agentId'?: str, ...}
    """
    webhook_data = {'token': token, 'message': '__auth_check__', 'sessionId': session_id}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{GATEWAY_URL}{WEBHOOK_PATH}',
                json=webhook_data,
                headers={'Content-Type': 'application/json'}
            ) as resp:
                result = await resp.json()
        
        if not result.get('success'):
            error = result.get('error', '认证失败')
            # 检查是否需要重新登录
            need_login = 'nologin' in str(error).lower()
            return {
                'success': False,
                'error': error,
                'needLogin': need_login
            }
        
        return result
    
    except Exception as e:
        return {'success': False, 'error': str(e)}


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

        # 调用 Gateway Webhook 进行认证
        webhook_data = {'token': token, 'message': message, 'sessionId': session_id}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{GATEWAY_URL}{WEBHOOK_PATH}',
                json=webhook_data,
                headers={'Content-Type': 'application/json'}
            ) as resp:
                auth_result = await resp.json()

        if not auth_result.get('success'):
            return web.json_response(auth_result, status=401 if 'token' in str(auth_result.get('error', '')) else 400)

        user_id = auth_result.get('userId')
        
        # 保存用户消息到本地
        chat_store.append(user_id, 'user', message)

        return web.json_response({
            'success': True,
            'token': auth_result.get('token'),
            'userId': user_id,
            'agentId': auth_result.get('agentId'),
            'sessionKey': auth_result.get('sessionKey'),
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

        webhook_data = {'token': token, 'message': '__auth_check__', 'sessionId': session_id}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{GATEWAY_URL}{WEBHOOK_PATH}',
                json=webhook_data,
                headers={'Content-Type': 'application/json'}
            ) as resp:
                auth_result = await resp.json()

        if not auth_result.get('success'):
            return web.json_response(auth_result, status=401)

        return web.json_response({
            'success': True,
            'userId': auth_result.get('userId'),
            'agentId': auth_result.get('agentId'),
            'sessionKey': f"agent:{auth_result.get('agentId')}:{session_id}",
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
        webhook_data = {'token': token, 'message': '__auth_check__'}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{GATEWAY_URL}{WEBHOOK_PATH}',
                json=webhook_data,
                headers={'Content-Type': 'application/json'}
            ) as resp:
                auth_result = await resp.json()

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

        webhook_data = {'token': token, 'message': '__auth_check__'}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{GATEWAY_URL}{WEBHOOK_PATH}',
                json=webhook_data,
                headers={'Content-Type': 'application/json'}
            ) as resp:
                auth_result = await resp.json()

        if not auth_result.get('success'):
            return web.json_response(auth_result, status=401)

        user_id = auth_result.get('userId')
        chat_store.clear(user_id)

        return web.json_response({'success': True, 'cleared': True})

    except Exception as e:
        logger.error(f'Clear history error: {e}')
        return web.json_response({'success': False, 'error': str(e)}, status=500)


# ============ WebSocket 处理器 ============

async def handle_websocket(request):
    """WebSocket 代理到 Gateway"""
    ws_client = web.WebSocketResponse()
    await ws_client.prepare(request)

    session_key = request.query.get('sessionKey')
    user_id = request.query.get('userId')
    
    if not session_key:
        await ws_client.send_json({'type': 'error', 'error': 'Missing sessionKey'})
        await ws_client.close()
        return ws_client

    logger.info(f'WS connect: {session_key} (user: {user_id})')

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
                                        'minProtocol': 3,
                                        'maxProtocol': 3,
                                        'client': {
                                            'id': 'gateway-client',
                                            'version': '1.0.0',
                                            'platform': 'linux',
                                            'mode': 'backend'
                                        },
                                        'role': 'operator',
                                        'scopes': ['operator.read', 'operator.write'],
                                        'caps': [],
                                        'commands': [],
                                        'permissions': {},
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
                current_response = ['']  # 当前响应文本
                
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
                                    # 心跳响应
                                    await ws_client.send_json({'type': 'pong'})
                                    continue
                                elif msg_type == 'history':
                                    # 从本地存储获取历史
                                    if user_id:
                                        messages = chat_store.load(user_id)
                                        await ws_client.send_json({
                                            'type': 'history',
                                            'messages': messages,
                                        })
                                        logger.info(f'Sent local history: {len(messages)} messages')
                                else:
                                    # 发送消息
                                    text = data.get('text') or data.get('message', '')
                                    if text:
                                        current_response[0] = ''  # 重置
                                        rpc_msg = {
                                            'type': 'req',
                                            'id': next_id(),
                                            'method': 'chat.send',
                                            'params': {
                                                'sessionKey': session_key,
                                                'message': text,
                                                'idempotencyKey': str(uuid.uuid4()),
                                            }
                                        }
                                        await gateway_ws.send_json(rpc_msg)
                                        logger.info(f'Sent to gateway: {text[:50]}...')
                            except json.JSONDecodeError:
                                pass
                        elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
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
                                
                                # RPC 响应
                                if msg_type == 'res':
                                    if data.get('error'):
                                        error_msg = data.get('error')
                                        logger.error(f'RPC error: {error_msg}')
                                        await ws_client.send_json({
                                            'type': 'error',
                                            'error': error_msg,
                                        })
                                        # 同时作为消息显示给用户
                                        await ws_client.send_json({
                                            'type': 'message',
                                            'role': 'system',
                                            'content': f'⚠️ 错误: {error_msg}',
                                        })
                                    continue
                                
                                # Event 消息：过滤只属于当前 session 的
                                if msg_type == 'event':
                                    msg_session_key = payload.get('sessionKey', '')
                                    if msg_session_key and msg_session_key != session_key:
                                        continue
                                    
                                    # 处理 agent 流式响应
                                    if event_type == 'agent':
                                        stream = payload.get('stream')
                                        stream_data = payload.get('data', {})
                                        
                                        if stream == 'assistant':
                                            text = stream_data.get('text', '')
                                            delta = stream_data.get('delta', '')
                                            current_response[0] = text
                                            await ws_client.send_json({
                                                'type': 'stream',
                                                'text': text,
                                                'delta': delta,
                                            })
                                        elif stream == 'lifecycle':
                                            phase = stream_data.get('phase')
                                            error = stream_data.get('error')
                                            if error:
                                                # Agent 执行出错
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
                                                # 保存完整回复到本地
                                                if user_id and current_response[0]:
                                                    chat_store.append(user_id, 'assistant', current_response[0])
                                                    logger.info(f'Saved response for {user_id}')
                                                await ws_client.send_json({
                                                    'type': 'done',
                                                })
                                    
                                    # chat 事件可以忽略，我们用 agent 事件
                                    
                            except json.JSONDecodeError:
                                pass
                        elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                            break

                await asyncio.gather(
                    handle_client_messages(),
                    handle_gateway_messages(),
                    return_exceptions=True
                )

    except aiohttp.ClientError as e:
        logger.error(f'Gateway connection error: {e}')
        await ws_client.send_json({'type': 'error', 'error': f'Gateway connection failed: {e}'})
    except Exception as e:
        logger.error(f'WS error: {e}')
        await ws_client.send_json({'type': 'error', 'error': str(e)})

    logger.info(f'WS disconnect: {session_key}')
    return ws_client


async def handle_health(request):
    return web.json_response({'status': 'ok', 'service': 'quantclaw'})


async def handle_index(request):
    index_file = STATIC_DIR / 'index.html'
    if index_file.exists():
        return web.FileResponse(index_file)
    return web.Response(text='QuantClaw Server', content_type='text/plain')


def create_app():
    app = web.Application()
    
    app.router.add_get('/', handle_index)
    app.router.add_get('/health', handle_health)
    app.router.add_post('/api/auth', handle_auth)
    app.router.add_post('/api/chat', handle_chat)
    app.router.add_post('/api/history', handle_history)
    app.router.add_post('/api/clear-history', handle_clear_history)
    app.router.add_get('/ws', handle_websocket)
    
    if STATIC_DIR.exists():
        app.router.add_static('/static/', STATIC_DIR, name='static')
    
    return app


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    logger.info(f'Starting QuantClaw Server on port {port}')
    logger.info(f'Gateway: {GATEWAY_URL}')
    logger.info(f'Data dir: {DATA_DIR}')
    web.run_app(create_app(), host='0.0.0.0', port=port)
