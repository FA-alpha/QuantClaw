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
    data = {"usertoken": token}
    
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
    strategy_token: str = None,
    strategy_id: str = None,
    strategy_tokens: str = None,
    bgn_date: str = None,
    end_date: str = None,
    init_balance: float = None,
    leverage: int = None,
    margin_mode: str = None,
    margin_allocation: str = None,
    data_type: int = 1,
) -> dict:
    """
    开始回测
    
    API: POST /Backtrack/apply_do
    
    参数说明:
    - strategy_token: 单策略的 token
    - strategy_id: 多策略 ID（逗号分隔）
    - strategy_tokens: 多策略 tokens（逗号分隔）
    - margin_mode: 保证金模式（exclusive=独占, shared=共享）
    - margin_allocation: 共享模式分配比例（逗号分隔，总和100）
    - data_type: 数据类型（默认1）
    """
    url = f"{API_BASE}/Backtrack/apply_do"
    data = {
        "usertoken": token,
        "data_type": str(data_type),
    }

    # 策略参数：支持 strategy_token 或 strategy_id
    if strategy_tokens:
        data["strategy_token"] = strategy_tokens
    elif strategy_id:
        data["strategy_id"] = strategy_id
    elif strategy_token:
        data["strategy_token"] = strategy_token
    
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
        
        # 如果有分配比例，添加到 strategy_margin_limit
        if margin_allocation and margin_mode == "shared":
            # 需要知道策略 ID，从 strategy_ids 中提取
            if strategy_id:
                strategy_ids = strategy_id.split(",")
                allocations = margin_allocation.split(",")
                strategy_margin_limit = {}
                for i, (sid, alloc) in enumerate(zip(strategy_ids, allocations)):
                    try:
                        # 计算实际保证金：比例 * 总额 / 100
                        total_margin = 10000 if init_balance is None else init_balance
                        actual_margin = float(alloc) * total_margin / 100
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
    lines.append("| ID | 策略Token | 名称 | 币种 | 类型 | 方向 |")
    lines.append("|---|---|---|---|---|---|")
    
    amt_type_map = {1: "现货", 2: "合约"}
    
    for item in info:
        lines.append(
            f"| {item.get('id', '')} "
            f"| {item.get('strategy_token', '')[:15]}... "
            f"| {item.get('name', '')[:20]} "
            f"| {item.get('coin', '')} "
            f"| {amt_type_map.get(item.get('amt_type'), '')} "
            f"| {item.get('direction', '')} |"
        )
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="启动回测")
    parser.add_argument("--token", required=True, help="用户 token（必填）")
    
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
    parser.add_argument("--name", dest="search_val", help="策略名称搜索")
    parser.add_argument("--coin", dest="search_coin", help="币种筛选")
    parser.add_argument("--amt-type", dest="search_amt_type", type=int,
                        choices=[1, 2], help="类型: 1现货 2合约")
    parser.add_argument("--status", dest="search_status", type=int, help="状态筛选")
    
    # 回测参数
    parser.add_argument("--strategy-token", help="策略 token（单策略）")
    parser.add_argument("--strategy-id", help="策略 ID（多策略，逗号分隔）")
    parser.add_argument("--strategy-tokens", help="策略 tokens（多策略，逗号分隔）")
    parser.add_argument("--bgn-date", help="开始日期 YYYY-MM-DD（回测必填）")
    parser.add_argument("--end-date", help="结束日期 YYYY-MM-DD（回测必填）")
    parser.add_argument("--init-balance", type=float, help="初始资金（默认10000）")
    parser.add_argument("--leverage", type=int, help="杠杆倍数（合约必填）")
    parser.add_argument("--margin-mode", choices=["exclusive", "shared"],
                        help="保证金模式: exclusive=独占, shared=共享")
    parser.add_argument("--margin-allocation",
                        help="共享模式分配比例（逗号分隔，总和100），如: 40,30,30")
    parser.add_argument("--data-type", type=int, default=1,
                        help="数据类型（默认1）")
    
    args = parser.parse_args()
    
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
        )
        if args.format == "json":
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(format_strategies(result))
        return
    
    # 开始回测
    if args.apply:
        # 验证必填参数
        missing = []
        if not args.strategy_token and not args.strategy_id and not args.strategy_tokens:
            missing.append("--strategy-token / --strategy-id / --strategy-tokens（至少一个）")
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
            strategy_token=args.strategy_token,
            strategy_id=args.strategy_id,
            strategy_tokens=args.strategy_tokens,
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
            strategy_display = args.strategy_token or args.strategy_id or args.strategy_tokens
            print(f"✅ 回测任务已提交")
            print(f"   任务 ID: {back_id}")
            print(f"   策略: {strategy_display[:50]}...")
            print(f"   时间范围: {args.bgn_date} ~ {args.end_date}")
            if args.margin_mode:
                mode_text = "独占模式" if args.margin_mode == "exclusive" else "共享模式"
                print(f"   保证金模式: {mode_text}")
                if args.margin_allocation:
                    print(f"   分配比例: {args.margin_allocation}")
            if args.leverage:
                print(f"   杠杆倍数: {args.leverage}x")
            print(f"\n查询状态: python skills/backtest-query/query.py --token {args.token} --detail {back_id}")
        return
    
    # 没有指定操作，显示帮助
    parser.print_help()


if __name__ == "__main__":
    main()
