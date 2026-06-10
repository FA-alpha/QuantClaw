#!/usr/bin/env python3
"""机器人状态批量查询 — /Trade/batch_check_status

供 stop / batch / scale / margin 等写操作前的预检复用。
各调用方通过 allowed_statuses / allowed_reserve / require_*_btn 传入自己的规则。
"""
from typing import Optional, List, Set

from api_client import api_post

STATUS_LABEL = {
    "0": "未运行", "1": "实盘运行中", "2": "模拟运行",
    "3": "已停止", "4": "模拟已停止",
}
RESERVE_STATUS_LABEL = {"0": "未预约", "1": "预约停止中", "2": "预约已终止"}


def _fetch_btn_map(token: str, agent_id: str) -> dict:
    """从 /Trade/lists 批量获取 is_reserve_stop_btn / is_add_pause_btn，返回 {bot_id: {...}}"""
    data = api_post(
        "/Trade/lists",
        {"usertoken": token, "app_v": "2.0.0", "page": 1, "limit": -1,
         "sort_type": 1, "sort_desc_type": 1, "lang": 1},
        agent_id,
    )
    btn_map = {}
    for b in data.get("info", []) or []:
        bid = str(b.get("id", ""))
        if bid:
            btn_map[bid] = {
                "is_reserve_stop_btn": b.get("is_reserve_stop_btn"),
                "is_add_pause_btn": b.get("is_add_pause_btn"),
            }
    return btn_map


def check_bots(
    token: str,
    bot_ids: List[str],
    allowed_statuses: Set[str],
    allowed_reserve: Optional[Set[str]] = None,
    allowed_add_pause_status: Optional[Set[str]] = None,
    require_reserve_btn: bool = False,
    require_pause_btn: bool = False,
    agent_id: Optional[str] = None,
) -> dict:
    """
    批量查询机器人状态，并判断操作是否可执行。

    Args:
        allowed_statuses: 允许的 bot status 集合，如 {"1", "2"}
        allowed_reserve: 允许的 reserve_status 集合，None / 空 = 不检查
        allowed_add_pause_status: 允许的 add_pause_status，None = 不检查
        require_reserve_btn: 如果 True，检查 detail 缓存中 is_reserve_stop_btn=1
        require_pause_btn: 如果 True，检查 detail 缓存中 is_add_pause_btn=1

    Returns:
        {"bots": [...], "executable_count": int, "blocked_count": int}
    """
    data = api_post(
        "/Trade/batch_check_status",
        {"usertoken": token, "app_v": "2.0.0", "bot_id": ",".join(bot_ids)},
        agent_id,
    )
    if data.get("_error") or data.get("status") != 1:
        return {
            "bots": [
                {"id": bid, "status": "?", "status_label": "查询失败",
                 "reserve_status": "?", "reserve_status_label": "",
                 "can_execute": False, "reason": "状态查询失败"}
                for bid in bot_ids
            ],
            "executable_count": 0,
            "blocked_count": len(bot_ids),
        }

    check_reserve = bool(allowed_reserve)
    check_pause = bool(allowed_add_pause_status)

    # 需要按钮校验时，从 /Trade/lists 一把取全量按钮数据
    btn_map = {}
    if require_reserve_btn or require_pause_btn:
        btn_map = _fetch_btn_map(token, agent_id or "")

    bots = []
    executable = 0
    blocked = 0

    info_list = data.get("info", [])
    for i, bid in enumerate(bot_ids):
        item = info_list[i] if i < len(info_list) else {}
        s = str(item.get("status", ""))
        r = str(item.get("reserve_status", ""))
        p = str(item.get("add_pause_status", "0"))

        can_exec = True
        reason = None

        if item:
            if s not in allowed_statuses:
                can_exec = False
                reason = f"当前状态为「{STATUS_LABEL.get(s, s)}」，不支持此操作"
            elif check_reserve and r not in allowed_reserve:
                can_exec = False
                reason = f"预约状态为「{RESERVE_STATUS_LABEL.get(r, r)}」，不支持此操作"
            elif check_pause and p not in allowed_add_pause_status:
                pause_label = "已暂停" if p == "1" else "未暂停"
                can_exec = False
                reason = f"加仓暂停状态为「{pause_label}」，不支持此操作"

        if can_exec and (require_reserve_btn or require_pause_btn):
            btns = btn_map.get(str(bid), {})
            if require_reserve_btn:
                if btns.get("is_reserve_stop_btn") != 1:
                    can_exec = False
                    reason = "该机器人不支持预约终止操作"
            if require_pause_btn:
                if btns.get("is_add_pause_btn") != 1:
                    can_exec = False
                    reason = "该机器人不支持暂停加仓操作"

        if can_exec:
            executable += 1
        else:
            blocked += 1

        bots.append({
            "id": bid,
            "status": s,
            "status_label": STATUS_LABEL.get(s, s),
            "reserve_status": r,
            "reserve_status_label": RESERVE_STATUS_LABEL.get(r, r),
            "add_pause_status": str(item.get("add_pause_status", "0")),
            "can_execute": can_exec,
            "reason": reason,
        })

    return {
        "bots": bots,
        "executable_count": executable,
        "blocked_count": blocked,
    }


def filter_executable(bot_states: list) -> List[str]:
    """从 check_bots() 返回的 bots 列表中提取可执行的 bot_id"""
    return [b["id"] for b in bot_states if b["can_execute"]]