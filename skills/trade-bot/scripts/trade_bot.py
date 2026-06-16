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
    token = get_user_token_by_agent_id(args.agent_id)
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
    token = get_user_token_by_agent_id(args.agent_id)
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
    token = get_user_token_by_agent_id(args.agent_id)
    if not token:
        return
    result = run(
        token=token, page=args.page, limit=args.limit,
        agent_id=args.agent_id,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_detail(args):
    """查询机器人详情"""
    from detail_bot import run
    token = get_user_token_by_agent_id(args.agent_id)
    if not token:
        return
    result = run(token=token, bot_id=args.bot_id, agent_id=args.agent_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_stop(args):
    """停止/停止当周期/预约停止/取消预约终止/暂停加仓/取消暂停加仓"""
    from stop_bot import run
    token = get_user_token_by_agent_id(args.agent_id)
    if not token:
        return
    result = run(
        token=token, bot_id=args.bot_id, save_type=args.save_type,
        agent_id=args.agent_id,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_batch(args):
    """批量停止/预约停止/取消预约终止/暂停加仓/取消暂停加仓"""
    from batch_bot import run
    token = get_user_token_by_agent_id(args.agent_id)
    if not token:
        return
    result = run(
        token=token, bot_ids=args.bot_ids, save_type=args.save_type,
        agent_id=args.agent_id,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_scale(args):
    """手动加仓/取消加仓"""
    from scale_bot import run
    token = get_user_token_by_agent_id(args.agent_id)
    if not token:
        return
    result = run(
        token=token, bot_id=args.bot_id, save_type=args.save_type,
        price=args.price, amt=args.amt, order_id=args.order_id,
        agent_id=args.agent_id,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_margin(args):
    """调整保证金"""
    from margin_bot import run
    token = get_user_token_by_agent_id(args.agent_id)
    if not token:
        return
    result = run(
        token=token, bot_id=args.bot_id, amt=args.amt, save_type=args.save_type,
        agent_id=args.agent_id,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_reject(args):
    """清除当前 agent 所有 nonce 凭证（用户拒绝确认时调用）"""
    from confirm_nonce import reject
    n = reject(args.agent_id)
    result = {
        "ok": True,
        "message": f"已清除 {n} 个待确认凭证" if n else "没有待确认凭证",
        "cleared": n,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_edit(args):
    """编辑策略参数（三步流程：预览 → 差异对比 → 确认执行）"""
    from edit_bot import run, run_diff, run_execute
    token = get_user_token_by_agent_id(args.agent_id)
    if not token:
        return

    if args.merged_rule:
        # 第③步：确认执行
        merged = json.loads(args.merged_rule)
        result = run_execute(
            token=token, bot_id=args.bot_id,
            merged_rule=merged,
            update_type=args.update_type,
            agent_id=args.agent_id,
        )
    elif args.rule:
        # 第②步：差异对比
        proposed = json.loads(args.rule)
        result = run_diff(
            token=token, bot_id=args.bot_id,
            proposed=proposed,
            agent_id=args.agent_id,
        )
    else:
        # 第①步：预览可编辑参数
        result = run(
            token=token, bot_id=args.bot_id,
            agent_id=args.agent_id,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_realtime(args):
    """查询实时数据（币价/余额）"""
    from realtime_info import run
    token = get_user_token_by_agent_id(args.agent_id)
    if not token:
        return
    result = run(
        token=token, bot_id=args.bot_id,
        show_type=args.show_type,
        agent_id=args.agent_id,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_grid_detail(args):
    """查询周期挂单明细"""
    from grid_detail import run
    token = get_user_token_by_agent_id(args.agent_id)
    if not token:
        return
    result = run(
        token=token, bot_id=args.bot_id,
        grid_id=args.grid_id,
        agent_id=args.agent_id,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    p = argparse.ArgumentParser(description="交易机器人管理")
    subs = p.add_subparsers(dest="command")

    # ── list ──
    sp = subs.add_parser("list", help="查询交易机器人列表")
    sp.add_argument("--agent-id", required=True, help="Agent ID")
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
    sp.add_argument("--agent-id", required=True, help="Agent ID")
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
    sp.add_argument("--agent-id", required=True, help="Agent ID")
    sp.add_argument("--page", type=int, default=1, help="第几页")
    sp.add_argument("--limit", type=int, default=-1, help="每页条数，-1=全部")
    sp.set_defaults(func=cmd_exchange_list)

    # ── batch ──
    sp = subs.add_parser("batch", help="批量操作机器人（停止/预约停止/取消预约终止/暂停加仓/取消暂停加仓）")
    sp.add_argument("--agent-id", required=True, help="Agent ID")
    sp.add_argument("--bot-ids", required=True, help="机器人 ID，多个逗号分隔")
    sp.add_argument("--save-type", required=True, choices=["4", "6", "7", "8", "9"],
                    help="4=停止, 6=预约停止, 7=取消预约终止, 8=暂停加仓, 9=取消暂停加仓")
    sp.set_defaults(func=cmd_batch)

    # ── detail ──
    sp = subs.add_parser("detail", help="查询机器人详情")
    sp.add_argument("--agent-id", required=True, help="Agent ID")
    sp.add_argument("--bot-id", required=True, help="机器人 ID")
    sp.set_defaults(func=cmd_detail)

    # ── stop ──
    sp = subs.add_parser("stop", help="停止/停止当周期/预约停止/取消预约终止/暂停加仓/取消暂停加仓")
    sp.add_argument("--agent-id", required=True, help="Agent ID")
    sp.add_argument("--bot-id", required=True, help="机器人 ID")
    sp.add_argument("--save-type", required=True, choices=["4", "5", "6", "7", "8", "9"],
                    help="4=停止, 5=停止当周期, 6=预约停止, 7=取消预约终止, 8=暂停加仓, 9=取消暂停加仓")
    sp.set_defaults(func=cmd_stop)

    # ── scale ──
    sp = subs.add_parser("scale", help="手动加仓/取消加仓")
    sp.add_argument("--agent-id", required=True, help="Agent ID")
    sp.add_argument("--bot-id", required=True, help="机器人 ID")
    sp.add_argument("--save-type", required=True, choices=["8", "9"],
                    help="8=手动加仓, 9=取消加仓")
    sp.add_argument("--price", type=float, help="加仓价格（save_type=8 必传）")
    sp.add_argument("--amt", type=float, help="加仓金额（save_type=8 必传）")
    sp.add_argument("--order-id", help="网格订单ID（save_type=9 必传）")
    sp.set_defaults(func=cmd_scale)

    # ── margin ──
    sp = subs.add_parser("margin", help="调整保证金")
    sp.add_argument("--agent-id", required=True, help="Agent ID")
    sp.add_argument("--bot-id", required=True, help="机器人 ID")
    sp.add_argument("--amt", type=float, help="保证金金额（不传则查询最大可用额度）")
    sp.add_argument("--save-type", required=True, choices=["6", "7"],
                    help="6=增加保证金, 7=减少保证金")
    sp.set_defaults(func=cmd_margin)

    # ── edit ──
    sp = subs.add_parser("edit", help="编辑策略参数（预览→差异→确认）")
    sp.add_argument("--agent-id", required=True, help="Agent ID")
    sp.add_argument("--bot-id", required=True, help="机器人 ID")
    sp.add_argument("--rule", help="提议修改的参数 (JSON)，不传则预览")
    sp.add_argument("--merged-rule", dest="merged_rule", help="合并后的完整参数 (JSON)，确认执行")
    sp.add_argument("--update-type", dest="update_type", type=int, default=1,
                    choices=[1, 2], help="更新方式: 1=永久 2=仅当前周期 (默认1)")
    sp.set_defaults(func=cmd_edit)

    # ── realtime ──
    sp = subs.add_parser("realtime", help="查询实时数据（币价/可用余额）")
    sp.add_argument("--agent-id", required=True, help="Agent ID")
    sp.add_argument("--bot-id", required=True, help="机器人 ID")
    sp.add_argument("--show-type", dest="show_type", default="1,2",
                    help="类型: 1=币价 2=余额 3=可减少保证金 (默认1,2)")
    sp.set_defaults(func=cmd_realtime)

    # ── grid-detail ──
    sp = subs.add_parser("grid-detail", help="查询周期挂单明细（买入/卖出/状态/价格/金额）")
    sp.add_argument("--agent-id", required=True, help="Agent ID")
    sp.add_argument("--bot-id", required=True, help="机器人 ID")
    sp.add_argument("--grid-id", required=True, help="周期ID（grid_id）")
    sp.set_defaults(func=cmd_grid_detail)

    # ── reject ──
    sp = subs.add_parser("reject", help="清除待确认的 nonce 凭证（用户拒绝确认时调用）")
    sp.add_argument("--agent-id", required=True, help="Agent ID")
    sp.set_defaults(func=cmd_reject)

    args = p.parse_args()
    if not args.command:
        p.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()