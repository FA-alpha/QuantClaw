#!/usr/bin/env python3
"""
启动回测脚本
用法: python start.py --token <token> [选项]

支持的功能：
1. --list-groups: 查看策略组列表 (Strategy/group_lists)
2. --list-strategies: 查看当前账号下策略列表 (Strategy/lists)
3. --apply: 开始回测 (Backtrack/apply_do)
4. --list-coins: 列出可用币种
"""

import argparse
import json
import sys
import os
import time
from datetime import datetime
import requests

# API 配置
API_BASE = "https://www.fourieralpha.com/Mobile"

# 缓存配置
CACHE_DIR = os.path.expanduser("~/.quantclaw/cache")
COIN_CACHE_FILE = os.path.join(CACHE_DIR, "coins.json")
CACHE_TTL = 86400  # 24 小时


def auto_get_token():
    """
    从当前 Agent workspace 自动获取 token
    
    优先级：
    1. 根据当前 agent_id 从 users.json 匹配用户
    2. 如果找不到匹配用户，直接报错（不再回退到第一个用户）
    
    Returns:
        str: usertoken 或 None
    """
    # 步骤1：查找当前 agent_id
    agent_id = None
    
    def find_agent_id_in_path(start_path):
        """向上遍历路径查找 clawd-* 目录"""
        current = start_path
        
        while current != '/':
            basename = os.path.basename(current)
            
            if basename.startswith('clawd-'):
                return basename.replace('clawd-', '')
            
            current = os.path.dirname(current)
        
        return None
    
    # 从 PWD 环境变量获取（保留软链接路径）
    pwd = os.environ.get('PWD')
    if pwd:
        agent_id = find_agent_id_in_path(pwd)
    
    # 从物理路径查找（回退方案）
    if not agent_id:
        agent_id = find_agent_id_in_path(os.path.abspath(os.getcwd()))
    
    # 步骤2：从 users.json 获取 token
    users_file = os.path.expanduser('~/.quantclaw/users.json')
    if not os.path.exists(users_file):
        return None
    
    try:
        with open(users_file, 'r') as f:
            data = json.load(f)
        users = data.get('users', [])
        
        if not users:
            print("[ERROR] ~/.quantclaw/users.json 中没有用户")
            return None
        
        # 必须根据 agent_id 匹配用户
        if not agent_id:
            print("[ERROR] 无法识别当前 agent_id，请确认在正确的 workspace 中执行")
            return None
        
        for user in users:
            if user.get('agentId') == agent_id:
                return user.get('token')
        
        # 找不到匹配的用户
        print(f"[ERROR] 未找到 agent_id={agent_id} 对应的用户")
        print(f"[DEBUG] 可用的 agent_id: {[u.get('agentId') for u in users]}")
        return None
        
    except Exception as e:
        print(f"[ERROR] 读取用户配置失败: {e}")
        return None


def check_auth(response: dict) -> tuple[bool, str]:
    """
    检查 API 响应状态
    
    Returns:
        tuple: (is_ok, error_message)
    """
    if response.get("status") == 0:
        info = response.get("info", "未知错误")
        return False, str(info)
    return True, ""


def get_coin_list(token: str, force_refresh: bool = False) -> dict:
    """
    获取可用币种列表（带缓存）
    """
    if not force_refresh and os.path.exists(COIN_CACHE_FILE):
        try:
            with open(COIN_CACHE_FILE, "r") as f:
                cache = json.load(f)
            if time.time() - cache.get("timestamp", 0) < CACHE_TTL:
                return cache.get("data", {})
        except:
            pass
    
    url = f"{API_BASE}/Strategy/coin_lists"
    data = {"usertoken": token, "app_v": "2.0.0"}
    
    try:
        resp = requests.post(url, data=data, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        
        ok, msg = check_auth(result)
        if not ok:
            return {"error": msg}
        
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(COIN_CACHE_FILE, "w") as f:
            json.dump({"timestamp": time.time(), "data": result}, f)
        
        return result
    except requests.RequestException as e:
        return {"error": str(e)}


def get_group_lists(token: str, page: int = 1, limit: int = 10) -> dict:
    """
    查看策略组列表
    
    API: POST /Strategy/group_lists
    """
    url = f"{API_BASE}/Strategy/group_lists"
    data = {
        "usertoken": token,
        "page": page,
        "limit": limit,
    }
    
    try:
        resp = requests.post(url, data=data, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        
        ok, msg = check_auth(result)
        if not ok:
            return {"error": msg}
        
        return result
    except requests.RequestException as e:
        return {"error": str(e)}


def get_strategy_lists(
    token: str,
    page: int = 1,
    limit: int = 10,
    search_val: str = None,
    search_coin: str = None,
    search_amt_type: int = None,
    search_status: int = None,
    data_grade: int = 1,
    show_type: int = 1,
    app_v: str = "2.0.0",
    lang: int = 1,
) -> dict:
    """
    查看当前账号下策略列表
    
    API: POST /Strategy/lists
    """
    url = f"{API_BASE}/Strategy/lists"
    data = {
        "usertoken": token,
        "page": page,
        "limit": limit,
        "data_grade": data_grade,
        "show_type": show_type,
        "app_v": app_v,
        "lang": lang,
    }
    
    if search_val:
        data["search_val"] = search_val
    if search_coin:
        data["search_coin"] = search_coin
    if search_amt_type is not None:
        data["search_amt_type"] = search_amt_type
    if search_status is not None:
        data["search_status"] = search_status
    
    try:
        resp = requests.post(url, data=data, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        
        ok, msg = check_auth(result)
        if not ok:
            return {"error": msg}
        
        return result
    except requests.RequestException as e:
        return {"error": str(e)}


def apply_backtest(
    token: str,
    strategy_id: str = None,
    bgn_date: str = None,
    end_date: str = None,
    init_balance: float = None,
    leverage: float = None,
    margin_mode: str = None,
    margin_allocation: str = None,
    data_type: int = 1,
) -> dict:
    """
    开始回测
    
    API: POST /Backtrack/apply_do
    
    参数说明:
    - strategy_id: 策略 ID（单个或多个逗号分隔）
    - margin_mode: 保证金模式（exclusive=独占, shared=共享）
    - margin_allocation: 共享模式分配金额（逗号分隔，来自calc_margin计算结果）
    - data_type: 数据类型（默认1）
    """
    url = f"{API_BASE}/Backtrack/apply_do"
    data = {
        "usertoken": token,
        "data_type": str(data_type),
        "app_v": "2.0.0"
    }

    # 策略参数：使用 strategy_id
    if strategy_id:
        data["strategy_id"] = strategy_id
    
    # 日期参数 - 使用 date_lists 格式
    if bgn_date and end_date:
        import json as json_module
        date_lists = [{"bgn_date": bgn_date, "end_date": end_date}]
        data["date_lists"] = json_module.dumps(date_lists)
    
    # 保证金参数
    if init_balance is not None:
        data["init_balance"] = init_balance
    if leverage is not None:
        data["leverage"] = leverage
    
    # 保证金模式 - 使用正确的参数名 margin_mode_config
    if margin_mode:
        # margin_mode_config 需要传递 JSON 字符串
        import json as json_module
        margin_config = {
            "is_shared_margin": (margin_mode == "shared"),
            "global_margin_limit": 10000 if init_balance is None else init_balance,
        }
        
        # 如果有分配金额（来自calc_margin计算结果），添加到 strategy_margin_limit
        if margin_allocation and margin_mode == "shared":
            # 需要知道策略 ID，从 strategy_ids 中提取
            if strategy_id:
                strategy_ids = strategy_id.split(",")
                allocations = margin_allocation.split(",")
                strategy_margin_limit = {}
                for i, (sid, alloc) in enumerate(zip(strategy_ids, allocations)):
                    try:
                        # 直接使用calc_margin计算出的具体金额（不再是百分比）
                        actual_margin = float(alloc)
                        strategy_margin_limit[sid.strip()] = str(int(actual_margin))
                    except:
                        pass
                margin_config["strategy_margin_limit"] = strategy_margin_limit
        
        # 转换为 JSON 字符串
        data["margin_mode_config"] = json_module.dumps(margin_config)
    
    try:
        resp = requests.post(url, data=data, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        
        ok, msg = check_auth(result)
        if not ok:
            return {"error": msg}
        
        return result
    except requests.RequestException as e:
        return {"error": str(e)}


def get_backtest_detail(token: str, back_id: int) -> dict:
    """
    获取回测详细统计信息
    
    API: POST /Backtrack/stat_info
    
    Args:
        token: 用户登录 token
        back_id: 回测记录 ID
    
    Returns:
        dict: API 响应数据（已清理net_value）
    """
    url = f"{API_BASE}/Backtrack/stat_info"
    data = {
        "usertoken": token,
        "back_id": back_id,
        "app_v": "2.0.0"
    }
    
    try:
        resp = requests.post(url, data=data, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        
        # 检查认证状态
        ok, msg = check_auth(result)
        if not ok:
            return {"error": msg}
        
        # 清理net_value参数，节省上下文窗口
        if isinstance(result.get("info"), dict):
            info = result["info"]
            # 删除total_stat中的net_value
            if "total_stat" in info and isinstance(info["total_stat"], dict):
                info["total_stat"].pop("net_value", None)
            
            # 删除其他可能的大数据字段
            info.pop("daily_stat", None)
            info.pop("trade_details", None)
        
        return result
    except requests.RequestException as e:
        return {"error": str(e)}


def calc_margin_allocation(
    token: str,
    strategy_ids: str,
    allocation_rules: dict = None,
    total_balance: float = 10000,
    leverage: float = 1.5,
    long_pct: int = 90,
    short_pct: int = 20,
    grouped_strategies: dict = None
) -> dict:
    """
    计算保证金分配方案
    
    API: POST /Strategy/calc_margin
    
    Args:
        token: 用户登录 token
        strategy_ids: 策略IDs，逗号分隔
        allocation_rules: 分配规则字典
        total_balance: 总保证金（默认10000）
        leverage: 杠杆倍数（默认1.5）
        long_pct: 做多保证金占比（默认90）
        short_pct: 做空保证金占比（默认20）
    
    Returns:
        dict: 包含每个策略具体保证金分配的响应数据
    """
    url = f"{API_BASE}/Strategy/calc_margin"
    
    # 首先获取策略详细信息
    strategies_info = get_strategies_with_grouping(token, strategy_ids)
    if "error" in strategies_info:
        return strategies_info
    
    strategies = strategies_info.get("strategies", [])
    if not strategies:
        return {"error": "未找到指定的策略"}
    
    # 构建strategys_json参数（正确的接口格式）
    strategys_json = []
    for strategy in strategies:
        # 确保ai_time_id存在且不为空
        ai_time_id = str(strategy.get("ai_time_id", ""))
        if not ai_time_id:
            print(f"[WARNING] 策略 {strategy.get('id')} 缺少ai_time_id，可能导致分配错误")
        
        strategys_json.append({
            "id": str(strategy.get("id", strategy.get("strategy_id", ""))),
            "direction": strategy.get("direction", ""),
            "multiple_num": strategy.get("multiple_num", 1),
            "ai_time_id": ai_time_id,
            "coin": strategy.get("coin", "")
        })
    
    # 基本参数（正确格式）
    data = {
        "strategys_json": json.dumps(strategys_json),
        "leverage": str(leverage),
        "long_pct": str(long_pct),
        "short_pct": str(short_pct),
        "usertoken": token,
        "app_v": "2.0.0",
        "lang": "1"
    }
    
    # 根据前端逻辑构建分配参数（模仿前端calcMargin函数）
    long_coin_pcts = []
    short_coin_pcts = []
    long_ai_time_pcts = []
    short_ai_time_pcts = []
    
    # 构建币种分配映射（模仿show_config_margin_modal逻辑）
    long_coin_map = {}
    short_coin_map = {}
    ai_time_map = {}
    
    for strategy in strategies:
        coin = strategy.get("coin", "")
        direction = strategy.get("direction", "")
        ai_time_id = str(strategy.get("ai_time_id", ""))
        ai_time_name = strategy.get("ai_time_name", "")
        
        # 按方向分组币种
        if direction == 'short':
            if coin not in short_coin_map:
                short_coin_map[coin] = {"coin": coin, "pct": ""}
        else:  # long 或其他默认为做多
            if coin not in long_coin_map:
                long_coin_map[coin] = {"coin": coin, "pct": ""}
        
        # AI时间类型分组
        if ai_time_id:
            if ai_time_id not in ai_time_map:
                ai_time_map[ai_time_id] = {
                    "ai_time_id": ai_time_id, 
                    "name": ai_time_name, 
                    "direction": {}
                }
            if direction not in ai_time_map[ai_time_id]["direction"]:
                ai_time_map[ai_time_id]["direction"][direction] = {"pct": ""}
    
    # 应用用户指定的分配规则
    if allocation_rules:
        # 处理币种做多分配
        if "coin_long_allocation" in allocation_rules:
            for coin, pct in allocation_rules["coin_long_allocation"].items():
                if coin in long_coin_map:
                    long_coin_map[coin]["pct"] = str(pct)
        
        # 处理币种做空分配
        if "coin_short_allocation" in allocation_rules:
            for coin, pct in allocation_rules["coin_short_allocation"].items():
                if coin in short_coin_map:
                    short_coin_map[coin]["pct"] = str(pct)
        
        # 处理AI时间类型分配（按方向分别处理）
        if "ai_time_long_allocation" in allocation_rules:
            for ai_time_id, ai_time_info in ai_time_map.items():
                ai_time_name = ai_time_info["name"]
                if ai_time_name in allocation_rules["ai_time_long_allocation"]:
                    pct = str(allocation_rules["ai_time_long_allocation"][ai_time_name])
                    if "long" in ai_time_info["direction"]:
                        ai_time_info["direction"]["long"]["pct"] = pct
        
        if "ai_time_short_allocation" in allocation_rules:
            for ai_time_id, ai_time_info in ai_time_map.items():
                ai_time_name = ai_time_info["name"]
                if ai_time_name in allocation_rules["ai_time_short_allocation"]:
                    pct = str(allocation_rules["ai_time_short_allocation"][ai_time_name])
                    if "short" in ai_time_info["direction"]:
                        ai_time_info["direction"]["short"]["pct"] = pct
        
        # 处理细分组分配（按方向+行情组合）
        if "sub_group_allocation" in allocation_rules:
            for ai_time_id, ai_time_info in ai_time_map.items():
                ai_time_name = ai_time_info["name"]
                for direction in ai_time_info["direction"]:
                    # 构建细分组名称：如"2025年震荡做多"
                    sub_group_name = f"{ai_time_name}{direction}"
                    if sub_group_name in allocation_rules["sub_group_allocation"]:
                        pct = str(allocation_rules["sub_group_allocation"][sub_group_name])
                        ai_time_info["direction"][direction]["pct"] = pct
    
    # 构建最终的参数数组（模仿前端calcMargin逻辑）
    for coin, coin_info in long_coin_map.items():
        if coin_info["pct"]:  # 只添加有设置比例的
            long_coin_pcts.append(coin_info)
    
    for coin, coin_info in short_coin_map.items():
        if coin_info["pct"]:  # 只添加有设置比例的
            short_coin_pcts.append(coin_info)
    
    for ai_time_id, ai_time_info in ai_time_map.items():
        if "short" in ai_time_info["direction"] and ai_time_info["direction"]["short"]["pct"]:
            short_ai_time_pcts.append({
                "ai_time_id": ai_time_id,
                "pct": ai_time_info["direction"]["short"]["pct"]
            })
        if "long" in ai_time_info["direction"] and ai_time_info["direction"]["long"]["pct"]:
            long_ai_time_pcts.append({
                "ai_time_id": ai_time_id,
                "pct": ai_time_info["direction"]["long"]["pct"]
            })
    
    # 添加到请求参数中
    if long_coin_pcts:
        data["long_coin_pcts"] = json.dumps(long_coin_pcts)
    if short_coin_pcts:
        data["short_coin_pcts"] = json.dumps(short_coin_pcts)
    if long_ai_time_pcts:
        data["long_ai_time_pcts"] = json.dumps(long_ai_time_pcts)
    if short_ai_time_pcts:
        data["short_ai_time_pcts"] = json.dumps(short_ai_time_pcts)
        
    try:
        print(f"[DEBUG] calc_margin接口请求参数:")
        for key, value in data.items():
            print(f"  {key}: {value}")
        
        resp = requests.post(url, data=data, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        
        # 检查返回状态
        if result.get("status") != 1:
            return {"error": f"接口调用失败: {result.get('msg', '未知错误')}"}
        
        return result
    except requests.RequestException as e:
        return {"error": str(e)}


def get_strategies_with_grouping(token: str, strategy_ids: str) -> dict:
    """
    获取策略详细信息并进行分组
    
    Args:
        token: 用户登录token
        strategy_ids: 策略IDs，逗号分隔
    
    Returns:
        dict: {
            "strategies": [...],           # 原始策略列表
            "grouped": {...},              # 分组结果
            "sub_groups": {...}            # 细分组信息
        }
    """
    strategy_id_list = [sid.strip() for sid in strategy_ids.split(",") if sid.strip()]
    print(f"[DEBUG] 查找目标策略ID: {strategy_id_list}")
    target_strategies = []
    
    # 方案1: 分页查询策略组（默认limit=20，逐步增加）
    page = 1
    limit = 20
    max_attempts = 10  # 最大尝试次数，防止无限循环
    attempts = 0
    
    while len(target_strategies) < len(strategy_id_list) and attempts < max_attempts:
        print(f"[DEBUG] 策略组查询 - 页码:{page}, limit:{limit}")
        groups_result = get_group_lists(token, page=page, limit=limit)
        
        print(f"[DEBUG] 策略组查询结果状态: {groups_result.get('status', 'unknown')}")
        if "error" in groups_result or groups_result.get("status") != 1:
            print(f"[DEBUG] 策略组查询失败: {groups_result}")
            break
            
        groups = groups_result.get("info", [])
        print(f"[DEBUG] 获取到 {len(groups)} 个策略组")
        
        found_in_this_page = False
        for group in groups:
            strategy_lists = group.get("strategy_lists", [])
            for strategy in strategy_lists:
                strategy_id = str(strategy.get("id", ""))
                if strategy_id in strategy_id_list:
                    # 检查是否已存在（去重）
                    if not any(str(s.get("id")) == strategy_id for s in target_strategies):
                        target_strategies.append(strategy)
                        found_in_this_page = True
                        print(f"[DEBUG] 在策略组中找到策略: {strategy_id}")
        
        # 如果找齐了所有策略，退出
        found_ids = {str(s.get("id")) for s in target_strategies}
        if all(sid in found_ids for sid in strategy_id_list):
            print(f"[DEBUG] 策略组查询完成，找到所有策略")
            break
            
        # 如果这一页没找到任何目标策略
        if not found_in_this_page:
            if limit < 100:
                limit = min(100, limit * 2)  # 增加limit
                page = 1  # 重新开始
                print(f"[DEBUG] 增加limit重新查询: {limit}")
            else:
                print(f"[DEBUG] 策略组查询已达到最大limit，跳出")
                break
        else:
            page += 1
        
        attempts += 1
    
    # 方案2: 如果策略组里没找全，查策略列表
    found_ids = {str(s.get("id")) for s in target_strategies}
    missing_ids = [sid for sid in strategy_id_list if sid not in found_ids]
    
    if missing_ids:
        print(f"[DEBUG] 策略组中未找到的策略ID: {missing_ids}")
        
        # 分页查询策略列表
        page = 1
        limit = 20
        attempts = 0
        
        while missing_ids and attempts < max_attempts:
            print(f"[DEBUG] 策略列表查询 - 页码:{page}, limit:{limit}")
            strategies_result = get_strategy_lists(token, page=page, limit=limit)
            
            print(f"[DEBUG] 策略列表查询结果状态: {strategies_result.get('status', 'unknown')}")
            if "error" in strategies_result or strategies_result.get("status") != 1:
                print(f"[DEBUG] 策略列表查询失败: {strategies_result}")
                break
                
            all_strategies = strategies_result.get("info", [])
            print(f"[DEBUG] 获取到 {len(all_strategies)} 个策略")
            
            found_in_this_page = False
            for strategy in all_strategies:
                strategy_id = str(strategy.get("id", ""))
                if strategy_id in missing_ids:
                    target_strategies.append(strategy)
                    missing_ids.remove(strategy_id)
                    found_in_this_page = True
                    print(f"[DEBUG] 在策略列表中找到策略: {strategy_id}")
            
            if not found_in_this_page:
                if limit < 100:
                    limit = min(100, limit * 2)
                    page = 1
                    print(f"[DEBUG] 增加limit重新查询: {limit}")
                else:
                    print(f"[DEBUG] 策略列表查询已达到最大limit")
                    break
            else:
                page += 1
            
            attempts += 1
    
    # 最终去重处理
    unique_strategies = {}
    for strategy in target_strategies:
        strategy_id = str(strategy.get("id", ""))
        if strategy_id not in unique_strategies:
            unique_strategies[strategy_id] = strategy
    
    target_strategies = list(unique_strategies.values())
    
    print(f"[DEBUG] 最终找到策略数量: {len(target_strategies)}")
    print(f"[DEBUG] 找到的策略ID: {[str(s.get('id')) for s in target_strategies]}")
    
    # 分析查询失败的原因并提供解决方案
    if len(target_strategies) == 0:
        print("[DEBUG] 查询失败，分析失败原因...")
        
        # 检查API响应状态，分析具体问题
        error_details = []
        
        # 再次测试策略组接口，获取详细错误信息
        test_groups = get_group_lists(token, page=1, limit=1)
        if "error" in test_groups:
            error_details.append(f"策略组接口错误: {test_groups.get('error')}")
        elif test_groups.get("status") != 1:
            error_details.append(f"策略组接口返回状态异常: {test_groups.get('msg', '未知错误')}")
        elif test_groups.get("info") is None or len(test_groups.get("info", [])) == 0:
            error_details.append("策略组接口返回空数据，可能该账号没有策略组")
        
        # 再次测试策略列表接口
        test_strategies = get_strategy_lists(token, page=1, limit=1)
        if "error" in test_strategies:
            error_details.append(f"策略列表接口错误: {test_strategies.get('error')}")
        elif test_strategies.get("status") != 1:
            error_details.append(f"策略列表接口返回状态异常: {test_strategies.get('msg', '未知错误')}")
        elif test_strategies.get("info") is None or len(test_strategies.get("info", [])) == 0:
            error_details.append("策略列表接口返回空数据，可能该账号没有策略")
        
        # 根据错误类型返回不同的处理建议
        if error_details:
            error_msg = "查询策略失败，具体问题:\n" + "\n".join(error_details)
            error_msg += f"\n\n请检查以下事项:"
            error_msg += f"\n1. Token是否正确且有效"
            error_msg += f"\n2. 策略ID是否属于当前账号: {strategy_ids}"
            error_msg += f"\n3. 策略是否已被删除或处于不可用状态"
            
            return {"error": error_msg}
        else:
            # API正常但找不到策略，可能是策略ID问题
            # 尝试扩大查询范围最后一次
            print("[DEBUG] API接口正常，尝试扩大查询范围...")
            
            # 查询更多策略组
            large_groups = get_group_lists(token, page=1, limit=500)
            if "error" not in large_groups and large_groups.get("status") == 1:
                groups = large_groups.get("info", [])
                for group in groups:
                    strategy_lists = group.get("strategy_lists", [])
                    for strategy in strategy_lists:
                        strategy_id = str(strategy.get("id", ""))
                        if strategy_id in strategy_id_list:
                            target_strategies.append(strategy)
                            print(f"[DEBUG] 扩大范围后找到策略: {strategy_id}")
            
            # 查询更多策略
            if len(target_strategies) == 0:
                large_strategies = get_strategy_lists(token, page=1, limit=500)
                if "error" not in large_strategies and large_strategies.get("status") == 1:
                    all_strategies = large_strategies.get("info", [])
                    for strategy in all_strategies:
                        strategy_id = str(strategy.get("id", ""))
                        if strategy_id in strategy_id_list:
                            target_strategies.append(strategy)
                            print(f"[DEBUG] 扩大范围后找到策略: {strategy_id}")
            
            # 去重处理
            if len(target_strategies) > 0:
                unique_strategies = {}
                for strategy in target_strategies:
                    strategy_id = str(strategy.get("id", ""))
                    if strategy_id not in unique_strategies:
                        unique_strategies[strategy_id] = strategy
                target_strategies = list(unique_strategies.values())
                print(f"[DEBUG] 扩大范围后找到策略数量: {len(target_strategies)}")
            
            # 最终还是找不到，询问用户确认
            if len(target_strategies) == 0:
                return {"error": f"未找到指定的策略ID: {strategy_ids}\n\n请确认:\n1. 策略ID是否正确\n2. 策略是否属于当前账号\n3. 策略是否处于可用状态\n\n如果策略ID有误，请提供正确的策略ID"}
    
    target_strategies = list(unique_strategies.values())
    
    # 对策略进行分组
    grouped = group_strategies_by_market_direction(target_strategies)
    
    # 生成细分组信息
    sub_groups = {}
    for direction, sub_groups_dict in grouped.items():
        for sub_group_name, strategies in sub_groups_dict.items():
            strategy_count = len(strategies)
            sub_groups[sub_group_name] = {
                "direction": direction,
                "count": strategy_count,
                "strategy_ids": [str(s.get("strategy_id", s.get("id", ""))) for s in strategies],
                "coins": list(set([s.get("coin", "") for s in strategies if s.get("coin")]))
            }
    
    return {
        "strategies": target_strategies,
        "grouped": grouped,
        "sub_groups": sub_groups
    }


def group_strategies_by_market_direction(strategies: list) -> dict:
    """
    根据AI时间类型和方向对策略进行多层级分组
    
    Args:
        strategies: 策略列表，每个策略包含ai_time_id, ai_time_name, direction等字段
    
    Returns:
        dict: 分组结果 {
            "做多": {
                "2025年震荡做多": [strategy1, strategy2, ...],
                "2024年趋势做多": [strategy3, ...]
            },
            "做空": {
                "2025年震荡做空": [strategy4, ...],
                "2024年趋势做空": [strategy5, ...]
            }
        }
    """
    grouped = {"做多": {}, "做空": {}}
    
    for strategy in strategies:
        direction = strategy.get("direction", "").strip()
        ai_time_name = strategy.get("ai_time_name", "").strip()
        ai_time_id = strategy.get("ai_time_id", "")
        
        # 确定大方向组
        if "做多" in direction or "long" in direction.lower():
            main_group = "做多"
        elif "做空" in direction or "short" in direction.lower():
            main_group = "做空"
        else:
            # 默认归类到做多
            main_group = "做多"
        
        # 构建细分组名：时间+行情+方向
        if ai_time_name:
            # 如果ai_time_name已经包含方向，直接使用
            if main_group in ai_time_name:
                sub_group_name = ai_time_name
            else:
                # 否则添加方向后缀
                sub_group_name = f"{ai_time_name}{main_group}"
        else:
            # 没有ai_time_name时，使用ai_time_id
            sub_group_name = f"类型{ai_time_id}{main_group}" if ai_time_id else f"默认{main_group}"
        
        # 初始化子组
        if sub_group_name not in grouped[main_group]:
            grouped[main_group][sub_group_name] = []
        
        # 添加策略到对应子组
        grouped[main_group][sub_group_name].append(strategy)
    
    return grouped


def format_strategy_groups(grouped_strategies: dict) -> str:
    """
    格式化显示策略分组信息
    
    Args:
        grouped_strategies: group_strategies_by_market_direction的返回结果
    
    Returns:
        str: 格式化的分组显示字符串
    """
    lines = ["策略分组结果:\n"]
    
    for direction, sub_groups in grouped_strategies.items():
        lines.append(f"📊 **{direction}方向组** (共{len(sub_groups)}个子组)")
        
        for sub_group_name, strategies in sub_groups.items():
            strategy_count = len(strategies)
            lines.append(f"  └─ {sub_group_name}: {strategy_count}个策略")
            
            # 显示每个策略的简要信息
            for i, strategy in enumerate(strategies[:3]):  # 最多显示3个
                name = strategy.get("name", "未知策略")[:20]
                coin = strategy.get("coin", "")
                lines.append(f"     {i+1}. {name} ({coin})")
            
            if strategy_count > 3:
                lines.append(f"     ... 还有{strategy_count-3}个策略")
        
        lines.append("")  # 空行
    
    return "\n".join(lines)


def format_groups(data: dict) -> str:
    """格式化策略组列表输出"""
    if "error" in data:
        return f"错误: {data['error']}"
    
    info = data.get("info", [])
    if not info:
        return "暂无策略组"
    
    lines = [f"共 {len(info)} 个策略组:\n"]
    lines.append("| ID | 名称 | 策略数量 | 创建时间 |")
    lines.append("|---|---|---|---|")
    
    for item in info:
        lines.append(
            f"| {item.get('id', '')} "
            f"| {item.get('name', '')} "
            f"| {item.get('strategy_count', '')} "
            f"| {item.get('create_time', '')} |"
        )
    
    return "\n".join(lines)


def format_strategies(data: dict) -> str:
    """格式化策略列表输出"""
    if "error" in data:
        return f"错误: {data['error']}"
    
    info = data.get("info", [])
    if not info:
        return "暂无策略"
    
    lines = [f"共 {len(info)} 个策略:\n"]
    lines.append("| ID | 策略ID | 名称 | 币种 | 类型 | 方向 |")
    lines.append("|---|---|---|---|---|---|")
    
    amt_type_map = {1: "现货", 2: "合约"}
    
    for item in info:
        name = item.get('name', '')
        # 确保name不是None，如果是None则使用空字符串
        if name is None:
            name = ''
        lines.append(
            f"| {item.get('id', '')} "
            f"| {item.get('strategy_id', '')[:15]}... "
            f"| {name[:20]} "
            f"| {item.get('coin', '')} "
            f"| {amt_type_map.get(item.get('amt_type', ''), '')} "
            f"| {item.get('direction', '')} |"
        )
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="启动回测")
    parser.add_argument("--token", help="用户 token（可选，未提供时自动获取）")
    
    # 功能选项
    parser.add_argument("--list-groups", action="store_true", help="查看策略组列表")
    parser.add_argument("--list-strategies", action="store_true", help="查看当前账号下策略列表")
    parser.add_argument("--list-coins", action="store_true", help="列出可用币种")
    parser.add_argument("--apply", action="store_true", help="开始回测")
    parser.add_argument("--refresh-cache", action="store_true", help="强制刷新缓存")
    
    # 通用参数
    parser.add_argument("--page", type=int, default=1, help="页码（默认1）")
    parser.add_argument("--limit", type=int, default=10, help="每页数量（默认10）")
    parser.add_argument("--format", default="table", choices=["json", "table"],
                        help="输出格式")
    
    # 策略列表筛选参数
    parser.add_argument("--search-val", dest="search_val", help="策略名称搜索关键词")
    parser.add_argument("--name", dest="search_val", help="策略名称搜索（--search-val别名）")
    parser.add_argument("--coin", dest="search_coin", help="币种筛选")
    parser.add_argument("--amt-type", dest="search_amt_type", type=int,
                        choices=[1, 2], help="类型: 1现货 2合约")
    parser.add_argument("--status", dest="search_status", type=int, help="状态筛选")
    parser.add_argument("--data-grade", dest="data_grade", type=int, default=1,
                        help="排序方式: 1=按创建时间排序（默认）")
    parser.add_argument("--show-type", dest="show_type", type=int, default=1,
                        help="显示类型: 1=标准显示（默认）")
    parser.add_argument("--app-v", dest="app_v", default="2.0.0",
                        help="API版本（默认2.0.0）")
    parser.add_argument("--lang", dest="lang", type=int, default=1,
                        help="语言: 1=中文（默认）")
    
    # 回测参数
    parser.add_argument("--strategy-id", help="策略 ID（单个策略）")
    parser.add_argument("--strategy-ids", help="策略 IDs（多策略，逗号分隔）")
    parser.add_argument("--detail", dest="back_id", type=int, help="查看回测详情（需要回测记录ID）")
    parser.add_argument("--calc-margin", action="store_true", help="计算保证金分配方案")
    parser.add_argument("--group-strategies", action="store_true", help="查看策略分组（按ai_time和方向）")
    parser.add_argument("--bgn-date", help="开始日期 YYYY-MM-DD（回测必填）")
    parser.add_argument("--end-date", help="结束日期 YYYY-MM-DD（回测必填）")
    parser.add_argument("--init-balance", type=float, help="初始资金（默认10000）")
    parser.add_argument("--leverage", type=float, help="杠杆倍数（支持小数，如1.5）")
    parser.add_argument("--margin-mode", choices=["exclusive", "shared"],
                        help="保证金模式: exclusive=独占, shared=共享")
    parser.add_argument("--margin-allocation",
                        help="共享模式分配金额（逗号分隔，来自calc_margin接口计算结果），如: 3000,2000,5000")
    parser.add_argument("--data-type", type=int, default=1,
                        help="数据类型（默认1）")
    
    # 保证金计算参数
    parser.add_argument("--coin-long-allocation", help="按币种做多分配比例，JSON格式：{'BTC': 40, 'ETH': 30, 'SOL': 30}")
    parser.add_argument("--coin-short-allocation", help="按币种做空分配比例，JSON格式：{'BTC': 50, 'ETH': 50}")
    parser.add_argument("--direction-allocation", help="按方向分配比例，JSON格式：{'做多': 70, '做空': 30}")
    parser.add_argument("--ai-time-long-allocation", help="按AI回测时间类型(市场行情)做多分配，JSON格式：{'2025年震荡': 50, '2025年牛市': 30}")
    parser.add_argument("--ai-time-short-allocation", help="按AI回测时间类型(市场行情)做空分配，JSON格式：{'2025年震荡': 50, '2025年牛市': 30}")
    parser.add_argument("--sub-group-allocation", help="按细分组分配，JSON格式：{'2025年震荡做多': 40, '2024年趋势做空': 30}")
    parser.add_argument("--strategy-type-allocation", help="按策略类型分配，JSON格式")
    parser.add_argument("--total-balance", type=float, default=10000, help="总保证金（默认10000）")
    parser.add_argument("--long-pct", type=int, default=90, help="做多保证金占比（默认90）")
    parser.add_argument("--short-pct", type=int, default=20, help="做空保证金占比（默认20）")
        
    args = parser.parse_args()
    
    # 自动获取 token（如果未提供或为空）
    if not args.token or not args.token.strip():
        args.token = auto_get_token()
        if not args.token:
            print("错误: 无法自动获取 token，请手动提供 --token 参数")
            print("检查路径：")
            print("  1. ~/.quantclaw/users.json")
            print("  2. templates/users.json")
            sys.exit(1)
        print(f"[INFO] 自动获取到token: {args.token[:20]}...")
    else:
        print(f"[INFO] 使用外部传递的token: {args.token[:20]}...")
    
    # 列出币种
    if args.list_coins:
        result = get_coin_list(args.token, force_refresh=args.refresh_cache)
        if "error" in result:
            print(f"错误: {result['error']}")
            sys.exit(1)
        info = result.get("info", [])
        print("可用币种:")
        for item in info:
            print(f"  {item.get('coin')} - {item.get('name', '')}")
        return
    
    # 查看策略组列表
    if args.list_groups:
        result = get_group_lists(args.token, page=args.page, limit=args.limit)
        if args.format == "json":
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(format_groups(result))
        return
    
    # 查看策略列表
    if args.list_strategies:
        result = get_strategy_lists(
            token=args.token,
            page=args.page,
            limit=args.limit,
            search_val=args.search_val,
            search_coin=args.search_coin,
            search_amt_type=args.search_amt_type,
            search_status=args.search_status,
            data_grade=args.data_grade,
            show_type=args.show_type,
            app_v=args.app_v,
            lang=args.lang,
        )
        if args.format == "json":
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(format_strategies(result))
        return
    
    # 查看回测详情
    if args.back_id:
        result = get_backtest_detail(args.token, args.back_id)
        if args.format == "json":
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            if "error" in result:
                print(f"错误: {result['error']}")
            else:
                info = result.get("info", {})
                print(f"回测详情 - ID: {args.back_id}")
                print(f"年化收益率: {info.get('year_rate', 'N/A')}%")
                print(f"夏普比率: {info.get('sharp_rate', 'N/A')}")
                print(f"最大回撤: {info.get('max_loss', 'N/A')}%")
                print(f"胜率: {info.get('win_rate', 'N/A')}%")
                print(f"交易次数: {info.get('trade_num', 'N/A')}")
        return
    
    # 查看策略分组
    if args.group_strategies:
        if not args.strategy_ids:
            print("错误: 需要 --strategy-ids 参数")
            sys.exit(1)
        
        result = get_strategies_with_grouping(args.token, args.strategy_ids)
        
        if "error" in result:
            print(f"错误: {result['error']}")
            sys.exit(1)
        
        if args.format == "json":
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            grouped = result.get("grouped", {})
            sub_groups = result.get("sub_groups", {})
            
            print(format_strategy_groups(grouped))
            
            print("📋 细分组详情:")
            for sub_group_name, info in sub_groups.items():
                direction = info["direction"]
                count = info["count"]
                coins = ", ".join(info["coins"])
                print(f"  {sub_group_name}: {direction} | {count}个策略 | 币种: {coins}")
        return
    
    # 计算保证金分配
    if args.calc_margin:
        if not args.strategy_ids:
            print("错误: 需要 --strategy-ids 参数")
            sys.exit(1)
        
        allocation_rules = {}
        
        # 优先处理自然语言分配
        # 解析分配规则
        if getattr(args, 'coin_long_allocation', None):
            try:
                allocation_rules["coin_long_allocation"] = json.loads(args.coin_long_allocation)
            except json.JSONDecodeError:
                print("错误: --coin-long-allocation 参数格式错误，需要有效的JSON")
                sys.exit(1)
        
        if getattr(args, 'coin_short_allocation', None):
            try:
                allocation_rules["coin_short_allocation"] = json.loads(args.coin_short_allocation)
            except json.JSONDecodeError:
                print("错误: --coin-short-allocation 参数格式错误，需要有效的JSON")
                sys.exit(1)
        
        if getattr(args, 'ai_time_long_allocation', None):
            try:
                allocation_rules["ai_time_long_allocation"] = json.loads(args.ai_time_long_allocation)
            except json.JSONDecodeError:
                print("错误: --ai-time-long-allocation 参数格式错误，需要有效的JSON")
                sys.exit(1)
        
        if getattr(args, 'ai_time_short_allocation', None):
            try:
                allocation_rules["ai_time_short_allocation"] = json.loads(args.ai_time_short_allocation)
            except json.JSONDecodeError:
                print("错误: --ai-time-short-allocation 参数格式错误，需要有效的JSON")
                sys.exit(1)
        
        if getattr(args, 'sub_group_allocation', None):
            try:
                allocation_rules["sub_group_allocation"] = json.loads(args.sub_group_allocation)
            except json.JSONDecodeError:
                print("错误: --sub-group-allocation 参数格式错误，需要有效的JSON")
                sys.exit(1)
        
        if args.direction_allocation:
            try:
                allocation_rules["direction_allocation"] = json.loads(args.direction_allocation)
            except json.JSONDecodeError:
                print("错误: --direction-allocation 参数格式错误，需要有效的JSON")
                sys.exit(1)
        
        if args.strategy_type_allocation:
            try:
                allocation_rules["strategy_type_allocation"] = json.loads(args.strategy_type_allocation)
            except json.JSONDecodeError:
                print("错误: --strategy-type-allocation 参数格式错误，需要有效的JSON")
                sys.exit(1)
        
        # 调用保证金计算接口
        result = calc_margin_allocation(
            token=args.token,
            strategy_ids=args.strategy_ids,
            allocation_rules=allocation_rules,
            total_balance=args.total_balance,
            leverage=getattr(args, 'leverage', 1.5),  # 使用用户指定的杠杆倍数，默认1.5
            long_pct=args.long_pct,
            short_pct=args.short_pct
        )
        
        print(f"[DEBUG] 使用参数: leverage={getattr(args, 'leverage', 1.5)}, long_pct={args.long_pct}, short_pct={args.short_pct}")
               
        if args.format == "json":
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            if "error" in result:
                print(f"错误: {result['error']}")
            else:
                info = result.get("info", [])
                print(f"保证金分配方案（总保证金: {args.total_balance}）:")
                print(f"策略ID | 币种 | 方向 | 杠杆 | 保证金金额")
                print(f"-------|------|------|------|----------")
                if isinstance(info, list):
                    for allocation in info:
                        strategy_id = allocation.get("id", "N/A")
                        coin = allocation.get("coin", "N/A")
                        direction = allocation.get("direction", "N/A")
                        multiple_num = allocation.get("multiple_num", "N/A")
                        margin = allocation.get("margin", "N/A")
                        print(f"{strategy_id} | {coin} | {direction} | {multiple_num} | {margin}")
                else:
                    print("返回数据格式异常")
        return
    
    # 开始回测
    if args.apply:
        # 验证必填参数
        missing = []
        if not args.strategy_id and not args.strategy_ids:
            missing.append("--strategy-id / --strategy-ids（至少一个）")
        if not args.bgn_date:
            missing.append("--bgn-date")
        if not args.end_date:
            missing.append("--end-date")
        
        if missing:
            print(f"错误: 缺少必填参数: {', '.join(missing)}")
            sys.exit(1)
        
        # 验证共享模式参数
        if args.margin_mode == "shared" and not args.margin_allocation:
            print("错误: 共享模式需要 --margin-allocation 参数")
            sys.exit(1)
        
        # 验证日期格式
        try:
            datetime.strptime(args.bgn_date, "%Y-%m-%d")
            datetime.strptime(args.end_date, "%Y-%m-%d")
        except ValueError:
            print("错误: 日期格式应为 YYYY-MM-DD")
            sys.exit(1)
        
        result = apply_backtest(
            token=args.token,
            strategy_id=args.strategy_id or args.strategy_ids,
            bgn_date=args.bgn_date,
            end_date=args.end_date,
            init_balance=args.init_balance,
            leverage=args.leverage,
            margin_mode=args.margin_mode,
            margin_allocation=args.margin_allocation,
            data_type=args.data_type,
        )
        
        if "error" in result:
            print(f"❌ 回测提交失败: {result['error']}")
            sys.exit(1)
        
        if args.format == "json":
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            back_id = result.get("info", {}).get("back_id") or result.get("info", {}).get("id")
            strategy_display = args.strategy_id or args.strategy_ids
            print(f"✅ 回测任务已提交")
            print(f"   任务 ID: {back_id}")
            print(f"   策略: {strategy_display[:50]}...")
            print(f"   时间范围: {args.bgn_date} ~ {args.end_date}")
            if args.margin_mode:
                mode_text = "独占模式" if args.margin_mode == "exclusive" else "共享模式"
                print(f"   保证金模式: {mode_text}")
                if args.margin_allocation:
                    print(f"   分配金额: {args.margin_allocation}")
            if args.leverage:
                print(f"   杠杆倍数: {args.leverage}x")
            print(f"\n查询状态: python skills/backtest-query/query.py --token {args.token} --detail {back_id}")
        return
    
    # 没有指定操作，显示帮助
    parser.print_help()


if __name__ == "__main__":
    main()
