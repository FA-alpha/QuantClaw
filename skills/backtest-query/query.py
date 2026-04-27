#!/usr/bin/env python3
"""
回测数据查询脚本
用法: python query.py --token <token> [选项]
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
AI_TIME_CACHE_FILE = os.path.join(CACHE_DIR, "ai_times.json")
AI_STRATEGY_CACHE_FILE = os.path.join(CACHE_DIR, "ai_strategies.json")
CACHE_TTL = 86400  # 24 小时


def check_auth(response: dict) -> tuple[bool, str]:
    """
    检查 API 响应状态
    
    Args:
        response: API 响应数据
    
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
    
    Args:
        token: 用户登录 token
        force_refresh: 强制刷新缓存
    
    Returns:
        dict: API 响应数据
    """
    # 检查缓存
    if not force_refresh and os.path.exists(COIN_CACHE_FILE):
        try:
            with open(COIN_CACHE_FILE, "r") as f:
                cache = json.load(f)
            if time.time() - cache.get("timestamp", 0) < CACHE_TTL:
                return cache.get("data", {})
        except:
            pass
    
    # 请求 API
    url = f"{API_BASE}/Strategy/coin_lists"
    data = {"usertoken": token}
    
    try:
        resp = requests.post(url, data=data, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        
        # 检查认证状态
        ok, msg = check_auth(result)
        if not ok:
            return {"error": msg}
        
        # 保存缓存
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(COIN_CACHE_FILE, "w") as f:
            json.dump({"timestamp": time.time(), "data": result}, f)
        
        return result
    except requests.RequestException as e:
        return {"error": str(e)}


def get_ai_time_list(token: str, force_refresh: bool = False) -> dict:
    """
    获取 AI 回测时间列表（带缓存）
    
    Args:
        token: 用户登录 token
        force_refresh: 强制刷新缓存
    
    Returns:
        dict: API 响应数据
    """
    # 检查缓存
    if not force_refresh and os.path.exists(AI_TIME_CACHE_FILE):
        try:
            with open(AI_TIME_CACHE_FILE, "r") as f:
                cache = json.load(f)
            if time.time() - cache.get("timestamp", 0) < CACHE_TTL:
                return cache.get("data", {})
        except:
            pass
    
    # 请求 API
    url = f"{API_BASE}/Extend/ai_time_lists"
    data = {"usertoken": token}
    
    try:
        resp = requests.post(url, data=data, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        
        # 检查认证状态
        ok, msg = check_auth(result)
        if not ok:
            return {"error": msg}
        
        # 保存缓存
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(AI_TIME_CACHE_FILE, "w") as f:
            json.dump({"timestamp": time.time(), "data": result}, f)
        
        return result
    except requests.RequestException as e:
        return {"error": str(e)}


def get_ai_strategy_list(token: str, force_refresh: bool = False) -> dict:
    """
    获取 AI 回测策略列表（带缓存）
    
    Args:
        token: 用户登录 token
        force_refresh: 强制刷新缓存
    
    Returns:
        dict: API 响应数据
    """
    # 检查缓存
    if not force_refresh and os.path.exists(AI_STRATEGY_CACHE_FILE):
        try:
            with open(AI_STRATEGY_CACHE_FILE, "r") as f:
                cache = json.load(f)
            if time.time() - cache.get("timestamp", 0) < CACHE_TTL:
                return cache.get("data", {})
        except:
            pass
    
    # 请求 API
    url = f"{API_BASE}/Extend/ai_strategy_lists"
    data = {"usertoken": token}
    
    try:
        resp = requests.post(url, data=data, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        
        # 检查认证状态
        ok, msg = check_auth(result)
        if not ok:
            return {"error": msg}
        
        # 保存缓存
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(AI_STRATEGY_CACHE_FILE, "w") as f:
            json.dump({"timestamp": time.time(), "data": result}, f)
        
        return result
    except requests.RequestException as e:
        return {"error": str(e)}


def create_strategy_group(token: str, strategy_tokens: str, name: str) -> dict:
    """
    创建策略组
    
    Args:
        token: 用户登录 token
        strategy_tokens: 策略 token（多个逗号分隔）
        name: 策略组名称
    
    Returns:
        dict: API 响应数据
    """
    url = f"{API_BASE}/Strategy/group_adds_do"
    data = {
        "usertoken": token,
        "strategy_token": strategy_tokens,
        "name": name
    }
    
    try:
        resp = requests.post(url, data=data, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        
        # 检查认证状态
        ok, msg = check_auth(result)
        if not ok:
            return {"error": msg}
        
        return result
    except requests.RequestException as e:
        return {"error": str(e)}


def get_backtest_detail(token: str, back_id: int) -> dict:
    """
    获取回测详细统计信息
    
    Args:
        token: 用户登录 token
        back_id: 回测记录 ID
    
    Returns:
        dict: API 响应数据
    """
    url = f"{API_BASE}/Backtrack/stat_info"
    data = {
        "usertoken": token,
        "back_id": back_id
    }
    
    try:
        resp = requests.post(url, data=data, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        
        # 检查认证状态
        ok, msg = check_auth(result)
        if not ok:
            return {"error": msg}
        
        return result
    except requests.RequestException as e:
        return {"error": str(e)}


def get_version_info(token: str, strategy_type: int, version: str) -> dict:
    """
    根据策略类型和版本获取版本信息
    
    Args:
        strategy_type: 策略类型
        version: 策略版本
    
    Returns:
        dict: 版本信息（不含 id 和 name）
    """
    strategies = get_ai_strategy_list(token)
    info = strategies.get("info", [])
    
    for strategy in info:
        if strategy.get("strategy_type") == strategy_type:
            for v in strategy.get("versions", []):
                if str(v.get("version")) == str(version):
                    # 返回除 id 和 name 外的所有字段
                    return {k: v for k, v in v.items() if k not in ("id", "name")}
    return {}


def query_backtest(
    token: str,
    page: int = 1,
    limit: int = 10,
    search_val: str = None,
    search_status: int = None,
    search_bgn_date: str = None,
    search_end_date: str = None,
    search_amt_type: int = None,
    sort_type: int = None,
    search_coin: str = None,
    type_: int = None,
    search_year: str = None,
    search_pct: str = None,
    strategy_type: int = None,
    search_direction: str = None,
    ai_time_id: str = None,
    search_recommand_type: int = None,
    version: str = None,
    leverage: int = None,
    search_extend: str = None,
    app_v: str = "1.0.1",
    version_extra: dict = None,
) -> dict:
    """
    查询回测列表
    
    Args:
        token: 用户登录 token
        page: 第几页（默认第一页）
        limit: 每页几个（默认10个，-1获取全部）
        search_val: 策略名称
        search_status: 回测状态（-1已删除 2回测中 3回测成功 4回测失败）
        search_bgn_date: 回测搜索开始日期
        search_end_date: 回测搜索结束日期
        search_amt_type: 类型（1现货 2合约）
        sort_type: 排序类型（1最新 2收益率最高 3夏普率最高 4回撤率最低）
        search_coin: 币种选择（多选逗号分割）
        type_: 类型（1个人回测 2AI回测推荐 3别人回测推荐）
        search_year: 年份
        search_pct: 比例选择
        strategy_type: 策略类型（1风霆 3鲲鹏v1）
        search_direction: 方向选择（long做多 short做空）
        ai_time_id: 时间ID
        search_recommand_type: 推荐类型（1推荐 2交易中策略）
        version: 策略版本
    
    Returns:
        dict: API 响应数据
    """
    url = f"{API_BASE}/Backtrack/lists"
    
    data = {"usertoken": token}
    
    if page is not None:
        data["page"] = page
    if limit is not None:
        data["limit"] = limit
    if search_val:
        data["search_val"] = search_val
    if search_status is not None:
        data["search_status"] = search_status
    if search_bgn_date:
        data["search_bgn_date"] = search_bgn_date
    if search_end_date:
        data["search_end_date"] = search_end_date
    if search_amt_type is not None:
        data["search_amt_type"] = search_amt_type
    if sort_type is not None:
        data["sort_type"] = sort_type
    if search_coin:
        data["search_coin"] = search_coin
    data["type"] = 2  # 固定为 AI 回测推荐
    if search_year:
        data["search_year"] = search_year
    if search_pct:
        data["search_pct"] = search_pct
    if strategy_type is not None:
        data["strategy_type"] = strategy_type
    if search_direction:
        data["search_direction"] = search_direction
    if ai_time_id:
        data["ai_time_id"] = ai_time_id
    if search_recommand_type is not None:
        data["search_recommand_type"] = search_recommand_type
    if version:
        data["version"] = version
    
    # 合并版本额外信息
    if version_extra:
        data.update(version_extra)
    
    # 额外参数
    if leverage is not None:
        data["leverage"] = leverage
    if search_extend:
        data["search_extend"] = search_extend
    if app_v:
        data["app_v"] = app_v
    
    try:
        resp = requests.post(url, data=data, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        
        # 检查认证状态
        ok, msg = check_auth(result)
        if not ok:
            return {"error": msg}
        
        return result
    except requests.RequestException as e:
        return {"error": str(e)}


def format_result(data: dict, output_format: str = "table") -> str:
    """
    格式化输出结果
    
    Args:
        data: API 响应数据
        output_format: 输出格式（json/table/summary）
    
    Returns:
        str: 格式化后的字符串
    """
    if "error" in data:
        return f"错误: {data['error']}"
    
    if output_format == "json":
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    info = data.get("info", [])
    if not info:
        return "未找到回测数据"
    
    if output_format == "summary":
        lines = [f"共找到 {len(info)} 条回测记录:\n"]
        for i, item in enumerate(info, 1):
            lines.append(
                f"{i}. {item.get('name', 'N/A')} | "
                f"年化: {item.get('year_rate', 'N/A')}% | "
                f"夏普: {item.get('sharp_rate', 'N/A')} | "
                f"回撤: {item.get('max_loss', 'N/A')}% | "
                f"胜率: {item.get('win_rate', 'N/A')}%"
            )
        return "\n".join(lines)
    
    # table format
    lines = [
        "| ID | 名称 | 年化收益 | 夏普比率 | 最大回撤 | 胜率 | 状态 |",
        "|---|---|---|---|---|---|---|"
    ]
    status_map = {1: "排队中", 2: "回测中", 3: "成功", 4: "失败"}
    for item in info:
        lines.append(
            f"| {item.get('id', '')} "
            f"| {item.get('name', '')[:20]} "
            f"| {item.get('year_rate', '')}% "
            f"| {item.get('sharp_rate', '')} "
            f"| {item.get('max_loss', '')}% "
            f"| {item.get('win_rate', '')}% "
            f"| {status_map.get(item.get('status'), '')} |"
        )
    return "\n".join(lines)


def auto_get_token():
    """自动获取当前 Agent 的 token"""
    workspace = os.getcwd()
    agent_id = os.path.basename(workspace).replace('clawd-', '')
    
    users_file = os.path.expanduser('~/.quantclaw/users.json')
    if not os.path.exists(users_file):
        return None
    
    try:
        with open(users_file, 'r') as f:
            data = json.load(f)
        users = data.get('users', [])
        for user in users:
            if user.get('agentId') == agent_id:
                return user.get('token')
    except:
        pass
    
    return None


def main():
    parser = argparse.ArgumentParser(description="查询回测数据")
    parser.add_argument("--token", help="用户 token（可选，未提供时自动获取）")
    parser.add_argument("--detail", dest="back_id", type=int, help="查看回测详情（需要回测记录ID）")
    parser.add_argument("--create-group", action="store_true", help="创建策略组")
    parser.add_argument("--group-name", help="策略组名称")
    parser.add_argument("--strategy-tokens", help="策略 token（多个逗号分隔）")
    parser.add_argument("--list-coins", action="store_true", help="列出可用币种")
    parser.add_argument("--list-ai-times", action="store_true", help="列出 AI 回测时间")
    parser.add_argument("--list-strategies", action="store_true", help="列出 AI 回测策略")
    parser.add_argument("--refresh-cache", action="store_true", help="强制刷新缓存")
    parser.add_argument("--page", type=int, default=1, help="页码")
    parser.add_argument("--limit", type=int, default=10, help="每页数量，-1获取全部")
    parser.add_argument("--name", dest="search_val", help="策略名称")
    
    # 查询回测时的参数（查询时必填）
    parser.add_argument("--coin", dest="search_coin", help="币种，多选逗号分割")
    parser.add_argument("--amt-type", dest="search_amt_type", type=int,
                        choices=[1, 2], help="类型: 1现货 2合约")
    parser.add_argument("--sort", dest="sort_type", type=int,
                        choices=[1, 2, 3, 4], help="排序: 1最新 2收益率 3夏普 4回撤")
    parser.add_argument("--strategy-type", dest="strategy_type", type=int,
                        help="策略类型")
    
    # 可选参数
    parser.add_argument("--status", dest="search_status", type=int,
                        choices=[-1, 2, 3, 4], help="状态: -1删除 2回测中 3成功 4失败")
    parser.add_argument("--start-date", dest="search_bgn_date", help="开始日期")
    parser.add_argument("--end-date", dest="search_end_date", help="结束日期")
    current_year = datetime.now().year
    parser.add_argument("--year", dest="search_year", type=int,
                        choices=range(2011, current_year + 1), metavar="YEAR",
                        help=f"按年份查询（2011-{current_year}），与 --ai-time-id 二选一")
    parser.add_argument("--ai-time-id", dest="ai_time_id",
                        help="按时间ID查询，与 --year 二选一")
    parser.add_argument("--recommand-type", dest="search_recommand_type", type=int,
                        choices=[1, 2], help="推荐类型: 1推荐 2交易中策略")
    parser.add_argument("--pct", dest="search_pct", 
                        help="比例选择 (BTC: 10/20/30/40/50/60/80/100/120, 其他: 60/80/100/120/140)")
    parser.add_argument("--version", dest="version", help="策略版本")
    parser.add_argument("--leverage", type=int, help="杠杆倍数")
    parser.add_argument("--search-extend", dest="search_extend", help="扩展参数")
    parser.add_argument("--direction", dest="search_direction",
                        choices=["long", "short"], help="方向: long做多 short做空（策略类型1,7,11需要）")
    parser.add_argument("--format", dest="output_format", default="summary",
                        choices=["json", "table", "summary"], help="输出格式")
    
    args = parser.parse_args()
    
    # 自动获取 token（如果未提供）
    if not args.token:
        args.token = auto_get_token()
        if not args.token:
            print("错误: 无法自动获取 token，请手动提供 --token 参数")
            sys.exit(1)
    
    # 强制刷新缓存（清除并重新获取 defaults 模块的全局缓存）
    if args.refresh_cache and args.token:
        try:
            from defaults import DefaultParams
            print("🔄 正在刷新全局缓存...")
            DefaultParams.refresh_cache(args.token, verbose=True)
            print()
        except Exception as e:
            print(f"⚠️  刷新缓存失败: {e}")
            print()
    
    # 列出币种
    if args.list_coins:
        if not args.token:
            print("错误: 需要 --token")
            return
        result = get_coin_list(args.token, force_refresh=args.refresh_cache)
        if "error" in result:
            print(f"错误: {result['error']}")
        else:
            info = result.get("info", [])
            print("可用币种:")
            for item in info:
                print(f"  {item.get('coin')} - {item.get('name')}")
        return
    
    # 列出 AI 回测时间
    if args.list_ai_times:
        if not args.token:
            print("错误: 需要 --token")
            return
        result = get_ai_time_list(args.token, force_refresh=args.refresh_cache)
        if "error" in result:
            print(f"错误: {result['error']}")
        else:
            info = result.get("info", [])
            print("AI 回测时间:")
            for item in info:
                print(f"  {item.get('id')} - {item.get('name')}")
        return
    
    # 列出 AI 回测策略
    if args.list_strategies:
        if not args.token:
            print("错误: 需要 --token")
            return
        result = get_ai_strategy_list(args.token, force_refresh=args.refresh_cache)
        if "error" in result:
            print(f"错误: {result['error']}")
        else:
            info = result.get("info", [])
            print("AI 回测策略:")
            for item in info:
                print(f"  [{item.get('strategy_type')}] {item.get('name')} (id: {item.get('id')})")
                versions = item.get("versions", [])
                for v in versions:
                    print(f"      - {v.get('name')} (版本: {v.get('version')}, 杠杆: {v.get('leverage')})")
        return
    
    # 创建策略组
    if args.create_group:
        if not args.token:
            print("错误: 创建策略组需要 --token")
            return
        if not args.group_name:
            print("错误: 需要 --group-name")
            return
        if not args.strategy_tokens:
            print("错误: 需要 --strategy-tokens")
            return
        result = create_strategy_group(args.token, args.strategy_tokens, args.group_name)
        if "error" in result:
            print(f"错误: {result['error']}")
        else:
            group_id = result.get("info", {}).get("id")
            print(f"✅ 策略组创建成功: {args.group_name} (ID: {group_id})")
        return
    
    # 查看详情
    if args.back_id:
        if not args.token:
            print("错误: 查看详情需要 --token")
            return
        result = get_backtest_detail(args.token, args.back_id)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    
    # 查询回测需要 token
    if not args.token:
        print("错误: 查询回测数据需要 --token")
        return
    
    # 验证时间参数（二选一必传）
    if args.search_year and args.ai_time_id:
        print("错误: --year 和 --ai-time-id 参数不能同时使用，请选择其一")
        return
    if not args.search_year and not args.ai_time_id:
        print("错误: --year 或 --ai-time-id 必须传一个")
        return
    
    # 验证方向参数
    if args.search_direction and args.strategy_type not in (1, 7, 11):
        print(f"警告: 策略类型 {args.strategy_type} 不支持方向参数，已忽略")
        args.search_direction = None
    
    # 验证 search_pct 参数
    if args.strategy_type == 3 and args.search_recommand_type == 2 and args.search_pct:
        print(f"警告: 策略类型3 + 推荐类型2 时不需要 search_pct 参数，已忽略")
        args.search_pct = None
    elif args.search_pct:
        # 验证 search_pct 值是否有效
        btc_opts = ['10', '20', '30', '40', '50', '60', '80', '100', '120']
        other_opts = ['60', '80', '100', '120', '140']
        is_btc = args.search_coin and 'BTC' in args.search_coin.upper()
        valid_opts = btc_opts if is_btc else other_opts
        if args.search_pct not in valid_opts:
            print(f"警告: search_pct 值 '{args.search_pct}' 无效，{'BTC' if is_btc else '其他币种'} 可选: {', '.join(valid_opts)}")
            args.search_pct = None
    
    # 获取版本额外信息
    version_extra = None
    if args.strategy_type and args.version:
        version_extra = get_version_info(args.token, args.strategy_type, args.version)
    
    result = query_backtest(
        token=args.token,
        page=args.page,
        limit=args.limit,
        search_val=args.search_val,
        search_status=args.search_status,
        search_bgn_date=args.search_bgn_date,
        search_end_date=args.search_end_date,
        search_amt_type=args.search_amt_type,
        sort_type=args.sort_type,
        search_coin=args.search_coin,
        # type 固定为 2
        search_year=args.search_year,
        strategy_type=args.strategy_type,
        version=args.version,
        version_extra=version_extra,
        search_direction=args.search_direction,
        ai_time_id=args.ai_time_id,
        search_pct=args.search_pct,
        search_recommand_type=args.search_recommand_type,
        leverage=args.leverage,
        search_extend=args.search_extend,
    )
    
    print(format_result(result, args.output_format))


if __name__ == "__main__":
    main()
