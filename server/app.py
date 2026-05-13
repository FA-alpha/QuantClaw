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
import subprocess
import threading
import re
from aiohttp import web, WSMsgType
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# CORS 配置
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '*').split(',')
CORS_ENABLED = os.getenv('CORS_ENABLED', 'true').lower() == 'true'

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
                                'minProtocol': 3,
                                'maxProtocol': 3,
                                'client': {
                                    'id': 'quantclaw-listener',
                                    'version': '1.0.0',
                                    'platform': 'linux',
                                    'mode': 'backend'
                                },
                                'role': 'operator',
                                'scopes': ['operator.read'],
                                'caps': [],
                                'commands': [],
                                'permissions': {},
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
                            
                            # 检测回测ID并启动监控
                            if state.get('user_token'):
                                back_ids = monitor_manager.extract_backtest_ids(response_text)
                                if back_ids:
                                    for back_id in back_ids:
                                        if monitor_manager.start_monitor(back_id, state['user_id'], state['user_token']):
                                            logger.info(f"🚀 [Listener] Auto-started backtest {back_id} monitor")
                            
                            # 任务完成，停止监听器（避免占用资源）
                            asyncio.create_task(self.stop_listener(session_key))
                        
                        # 重置状态，准备下一轮（虽然监听器会被停止）
                        state['current_response'] = ''
                        state['response_saved'] = False
        
        except json.JSONDecodeError:
            pass
        except Exception as e:
            logger.error(f'Error handling message in listener: {e}')


# ============ 回测监控管理 ============

class BacktestMonitorManager:
    """回测监控管理器"""
    
    def __init__(self):
        self.active_monitors = {}  # {back_id: process}
        self.skills_dir = Path(__file__).parent.parent / 'skills'
    
    def extract_backtest_ids(self, text: str) -> list:
        """从文本中提取回测ID"""
        # 匹配回测ID模式：数字
        pattern = r'回测.*?ID[：:\s]*(\d+)|回测[：:\s]*#?(\d+)|back_id[：:\s]*(\d+)'
        matches = re.findall(pattern, text, re.IGNORECASE)
        
        # 提取所有非空匹配
        ids = []
        for match in matches:
            for group in match:
                if group and group.isdigit():
                    ids.append(int(group))
        
        return list(set(ids))  # 去重
    
    def start_monitor(self, back_id: int, user_id: str, user_token: str):
        """启动回测监控"""
        if back_id in self.active_monitors:
            logger.info(f"回测 {back_id} 已在监控中")
            return False
        
        try:
            monitor_script = self.skills_dir / 'start-backtest' / 'backtest_monitor.py'
            
            # 构建命令
            cmd = [
                'python3', str(monitor_script),
                '--back-id', str(back_id),
                '--token', user_token,
                '--daemon'
            ]
            
            # 启动后台监控进程
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.skills_dir / 'start-backtest'
            )
            
            self.active_monitors[back_id] = {
                'process': process,
                'user_id': user_id,
                'start_time': datetime.now()
            }
            
            logger.info(f"✅ 启动回测 {back_id} 监控，PID: {process.pid}")
            return True
            
        except Exception as e:
            logger.error(f"启动监控失败: {e}")
            return False
    
    def check_notification_files(self):
        """检查通知文件并发送消息"""
        notification_dir = Path('/tmp')
        pattern = 'quantclaw_notification_*.json'
        
        for file_path in notification_dir.glob(pattern):
            try:
                # 读取通知内容
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                back_id = data.get('back_id')
                user_id = data.get('user_id') 
                message = data.get('message')
                
                if back_id and user_id and message:
                    # 发送通知消息到聊天
                    asyncio.create_task(self.send_notification(user_id, message))
                    logger.info(f"📨 发送回测 {back_id} 完成通知")
                
                # 删除已处理的通知文件
                file_path.unlink()
                
                # 清理监控记录
                if back_id in self.active_monitors:
                    del self.active_monitors[back_id]
                    
            except Exception as e:
                logger.error(f"处理通知文件 {file_path} 失败: {e}")
                # 删除损坏的文件
                try:
                    file_path.unlink()
                except:
                    pass
    
    async def send_notification(self, user_id: str, message: str):
        """发送通知消息到用户聊天"""
        try:
            # 保存系统消息到聊天记录
            chat_store.append(user_id, 'assistant', message)
            logger.info(f"💬 回测完成通知已保存到用户 {user_id} 聊天记录")
            
        except Exception as e:
            logger.error(f"发送通知失败: {e}")

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


# 创建全局管理器
monitor_manager = BacktestMonitorManager()
chat_store = ChatStore(CHAT_DIR)
persistent_listener = PersistentSessionListener(GATEWAY_WS, GATEWAY_TOKEN, chat_store)

# ============ 后台任务 ============

async def notification_checker():
    """定期检查回测完成通知"""
    while True:
        try:
            monitor_manager.check_notification_files()
            await asyncio.sleep(5)  # 每5秒检查一次
        except Exception as e:
            logger.error(f"通知检查器错误: {e}")
            await asyncio.sleep(10)  # 出错后延长间隔


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
        
        # 注意：消息将在WebSocket中保存，这里不重复保存

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


async def handle_new_conversation(request):
    """新建对话：清除聊天记录并删除 session 文件"""
    try:
        data = await request.json()
        token = data.get('token')

        if not token:
            return web.json_response({'success': False, 'error': 'Missing token'}, status=400)

        # 步骤1：认证获取用户信息
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
        agent_id = auth_result.get('agentId')
        
        # 步骤2：清除本地聊天记录
        chat_store.clear(user_id)
        logger.info(f'Cleared chat history for user: {user_id}')

        # 步骤3：删除 Clawdbot session 文件，强制创建新 session
        session_key = f'agent:{agent_id}:main'
        session_dir = Path(f'/home/ubuntu/.clawdbot/agents/{agent_id}/sessions')
        
        if session_dir.exists():
            # 删除当前 session 的 JSONL 文件
            sessions_json = session_dir / 'sessions.json'
            if sessions_json.exists():
                try:
                    import json as _json
                    with open(sessions_json, 'r') as f:
                        sessions_data = _json.load(f)
                    
                    # 获取当前 session 的文件路径
                    session_info = sessions_data.get(session_key, {})
                    session_file = session_info.get('sessionFile')
                    
                    if session_file and Path(session_file).exists():
                        Path(session_file).unlink()
                        logger.info(f'Deleted session file: {session_file}')
                    
                    # 从 sessions.json 中删除这个 session
                    if session_key in sessions_data:
                        del sessions_data[session_key]
                        with open(sessions_json, 'w') as f:
                            _json.dump(sessions_data, f, indent=2)
                        logger.info(f'Removed session key from sessions.json: {session_key}')
                    
                except Exception as e:
                    logger.error(f'Failed to delete session files: {e}')
        
        logger.info(f'Session reset for user: {user_id}, agent: {agent_id}')

        return web.json_response({
            'success': True,
            'cleared': True,
            'sessionReset': True,
            'userId': user_id,
            'agentId': agent_id,
            'sessionKey': session_key,
        })

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
    user_token = request.query.get('token')  # 获取用户token
    
    if not session_key:
        await ws_client.send_json({'type': 'error', 'error': 'Missing sessionKey'})
        await ws_client.close()
        return ws_client

    logger.info(f'WS connect: {session_key} (user: {user_id})')
    
    # 存储用户token供监控使用
    if user_id and user_token:
        monitor_manager.user_tokens = getattr(monitor_manager, 'user_tokens', {})
        monitor_manager.user_tokens[user_id] = user_token
    
    # 重连时停止该 session 的旧后备监听器（防止重复保存）
    if session_key in persistent_listener.active_listeners:
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
                response_saved = [False]  # 防止重复保存标志
                
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
                                        response_saved[0] = False  # 重置保存标志
                                        
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
                                        # 保存用户消息到本地（只在WebSocket中保存一次）
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
                                            # 发送流式数据到客户端
                                            await ws_client.send_json({
                                                'type': 'stream',
                                                'text': text,
                                                'delta': delta,
                                            })
                                            # 调试：记录流式数据发送（仅记录前几次）
                                            if len(text) < 100:
                                                logger.debug(f'🌊 Streaming to {user_id}: {len(text)} chars')
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
                                                # 保存完整回复到本地（防重复保存）
                                                if user_id and current_response[0] and not response_saved[0]:
                                                    response_text = current_response[0]
                                                    logger.info(f'📝 About to save assistant response for {user_id}: {len(response_text)} chars')
                                                    chat_store.append(user_id, 'assistant', response_text)
                                                    response_saved[0] = True  # 标记已保存
                                                    logger.info(f'✅ Saved assistant response for {user_id}')
                                                    
                                                    # 检测回测ID并启动监控（保存后立即检测）
                                                    back_ids = monitor_manager.extract_backtest_ids(response_text)
                                                    if back_ids:
                                                        # 获取用户token
                                                        user_tokens = getattr(monitor_manager, 'user_tokens', {})
                                                        user_token = user_tokens.get(user_id)
                                                        if user_token:
                                                            for back_id in back_ids:
                                                                if monitor_manager.start_monitor(back_id, user_id, user_token):
                                                                    logger.info(f"🚀 自动启动回测 {back_id} 监控")
                                                        else:
                                                            logger.warning(f"无法获取用户 {user_id} 的token，跳过监控")
                                                elif response_saved[0]:
                                                    logger.info(f'⚠️ Skipped duplicate save for {user_id} (already saved)')
                                                
                                                await ws_client.send_json({
                                                    'type': 'done',
                                                })
                                    
                                    # chat 事件可以忽略，我们用 agent 事件
                                    elif event_type == 'chat':
                                        # 明确忽略 chat 事件，避免重复处理
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
                if user_id:
                    # 检查是否有未完成的响应（有流式数据但未收到 lifecycle.end）
                    has_incomplete_response = current_response[0] and not response_saved[0]
                    
                    # 不保存流式数据！只启动后备监听器等待 lifecycle.end
                    if has_incomplete_response:
                        logger.warning(f'🚨 Connection closed before lifecycle.end for {user_id}')
                        logger.info(f'📊 Incomplete stream data: {len(current_response[0])} chars (not saving)')
                        logger.info(f'🎧 Starting backup persistent listener to wait for completion')
                        await persistent_listener.start_listener(session_key, user_id, user_token)

    except aiohttp.ClientError as e:
        logger.error(f'Gateway connection error: {e}')
        try:
            await ws_client.send_json({'type': 'error', 'error': f'Gateway connection failed: {e}'})
        except:
            pass
        # 连接异常时启动后备监听器（任何异常都可能导致消息丢失）
        if user_id and session_key and user_token:
            logger.info(f'🎧 Starting backup listener due to connection error')
            await persistent_listener.start_listener(session_key, user_id, user_token)
    except Exception as e:
        logger.error(f'WS error: {e}')
        try:
            await ws_client.send_json({'type': 'error', 'error': str(e)})
        except:
            pass
        # 其他异常时也启动后备监听器
        if user_id and session_key and user_token:
            logger.info(f'🎧 Starting backup listener due to error')
            await persistent_listener.start_listener(session_key, user_id, user_token)

    logger.info(f'WS disconnect: {session_key}')
    return ws_client


async def handle_health(request):
    return web.json_response({'status': 'ok', 'service': 'quantclaw'})


async def handle_index(request):
    index_file = STATIC_DIR / 'index.html'
    if index_file.exists():
        return web.FileResponse(index_file)
    return web.Response(text='QuantClaw Server', content_type='text/plain')


# ============ CORS 中间件 ============

@web.middleware
async def cors_middleware(request, handler):
    """处理 CORS 跨域请求"""
    if not CORS_ENABLED:
        return await handler(request)
    
    # 处理 OPTIONS 预检请求
    if request.method == 'OPTIONS':
        origin = request.headers.get('Origin', '*')
        
        # 检查是否允许该源
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
    
    # 处理实际请求
    response = await handler(request)
    
    origin = request.headers.get('Origin', '*')
    
    # 检查是否允许该源
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


async def init_background_tasks(app):
    """启动后台任务"""
    app['notification_task'] = asyncio.create_task(notification_checker())
    logger.info("🔍 回测通知检查器已启动")

async def cleanup_background_tasks(app):
    """清理后台任务"""
    app['notification_task'].cancel()
    await app['notification_task']

def create_app():
    # 添加 CORS 中间件
    middlewares = []
    if CORS_ENABLED:
        middlewares.append(cors_middleware)
        logger.info(f'CORS enabled. Allowed origins: {ALLOWED_ORIGINS}')
    
    app = web.Application(middlewares=middlewares)
    
    # 添加启动和清理事件
    app.on_startup.append(init_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)
    
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
    port = int(os.getenv('PORT', 8080))
    logger.info(f'Starting QuantClaw Server on port {port}')
    logger.info(f'Gateway: {GATEWAY_URL}')
    logger.info(f'Data dir: {DATA_DIR}')
    web.run_app(create_app(), host='0.0.0.0', port=port)
