#!/usr/bin/env python3
"""交易机器人管理 - argparse CLI 入口"""
import json
import os
import argparse
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).parent


def get_user_token_by_agent_id(agent_id: str) -> Optional[str]:
    """从 ~/.quantclaw/users.json 查询 token"""
    users_file = os.path.expanduser("~/.quantclaw/users.json")
    if not os.path.exists(users_file):
        print(json.dumps({"status": "error", "message": f"users.json 不存在: {users_file}"}))
        return None
    with open(users_file) as f:
        users = json.load(f)
    for u in users.get("users", []):
        if u.get("agentId") == agent_id:
            return u.get("token")
    print(json.dumps({"status": "error", "message": f"未找到 agentId={agent_id} 的 token"}))
    return None


def cmd_list(args):
    """查询交易机器人列表"""
    from list_bots import run
    token = args.token if args.token else get_user_token_by_agent_id(args.agent_id)
    if not token:
        return
    result = run(
        token=token, status=args.status, exchange_ids=args.exchange_ids,
        amt_type=args.amt_type, strategy_type=args.strategy_type,
        account_id=args.account_id, direction=args.direction,
        search=args.search, coin=args.coin, sort=args.sort, order=args.order,
        page=args.page, limit=args.limit, agent_id=args.agent_id,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_leverage(args):
    """查询杠杆率统计"""
    from leverage_bot import run
    token = args.token if args.token else get_user_token_by_agent_id(args.agent_id)
    if not token:
        return
    result = run(
        token=token, status=args.status, exchange_ids=args.exchange_ids,
        amt_type=args.amt_type, strategy_type=args.strategy_type,
        account_id=args.account_id, direction=args.direction,
        search=args.search, coin=args.coin, agent_id=args.agent_id,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_exchange_list(args):
    """查询交易所账户列表"""
    from exchange_list import run
    token = args.token if args.token else get_user_token_by_agent_id(args.agent_id)
    if not token:
        return
    result = run(
        token=token, page=args.page, limit=args.limit,
        agent_id=args.agent_id,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def _not_impl(name):
    print(json.dumps({"status": "error", "message": f"{name} 功能尚未实现"}, ensure_ascii=False))


def main():
    p = argparse.ArgumentParser(description="交易机器人管理")
    subs = p.add_subparsers(dest="command")

    # ── list ──
    sp = subs.add_parser("list", help="查询交易机器人列表")
    sp.add_argument("--agent-id", default="qc-test", help="Agent ID")
    sp.add_argument("--token", help="直接传 token（跳过 agent-id 查找）")
    sp.add_argument("--status", default="running", help="运行状态: running/sim/stopped/deleted/all")
    sp.add_argument("--exchange-ids", help="交易所账户ID，逗号分隔")
    sp.add_argument("--amt-type", help="交易品种: spot/futures/all")
    sp.add_argument("--strategy-type", type=int, help="策略类型ID")
    sp.add_argument("--account-id", type=int, help="交易所账号ID")
    sp.add_argument("--direction", help="合约方向: long/short/all")
    sp.add_argument("--search", help="机器人名称搜索")
    sp.add_argument("--coin", help="币种")
    sp.add_argument("--sort", default="latest", help="排序: latest/profit/runtime/capital/nav/stop-time")
    sp.add_argument("--order", default="desc", help="排序方向: desc/asc")
    sp.add_argument("--page", type=int, default=1, help="第几页")
    sp.add_argument("--limit", type=int, default=10, help="每页条数，-1=全部")
    sp.set_defaults(func=cmd_list)

    # ── leverage ──
    sp = subs.add_parser("leverage", help="查询杠杆率统计")
    sp.add_argument("--agent-id", default="qc-test", help="Agent ID")
    sp.add_argument("--token", help="直接传 token（跳过 agent-id 查找）")
    sp.add_argument("--status", default="running", help="运行状态: running/sim/stopped/deleted/all")
    sp.add_argument("--exchange-ids", help="交易所账户ID，逗号分隔")
    sp.add_argument("--amt-type", help="交易品种: spot/futures/all")
    sp.add_argument("--strategy-type", type=int, help="策略类型ID")
    sp.add_argument("--account-id", type=int, help="交易所账号ID")
    sp.add_argument("--direction", help="合约方向: long/short/all")
    sp.add_argument("--search", help="机器人名称搜索")
    sp.add_argument("--coin", help="币种")
    sp.set_defaults(func=cmd_leverage)

    # ── exchange-list ──
    sp = subs.add_parser("exchange-list", help="查询交易所账户列表")
    sp.add_argument("--agent-id", default="qc-test", help="Agent ID")
    sp.add_argument("--token", help="直接传 token（跳过 agent-id 查找）")
    sp.add_argument("--page", type=int, default=1, help="第几页")
    sp.add_argument("--limit", type=int, default=-1, help="每页条数，-1=全部")
    sp.set_defaults(func=cmd_exchange_list)

    # ── 占位子命令 ──
    for cmd in ["detail", "balance", "stop", "apply", "check-status",
                "orders", "scale", "margin", "update"]:
        sp = subs.add_parser(cmd, help=f"{cmd}（待实现）")
        sp.add_argument("--agent-id", required=True, help="Agent ID")
        sp.set_defaults(func=lambda a, n=cmd: _not_impl(n))

    args = p.parse_args()
    if not args.command:
        p.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()