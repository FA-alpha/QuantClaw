#!/usr/bin/env python3
"""机器人状态批量查询 — /Trade/batch_check_status

供 stop / batch / scale / margin 等写操作前的预检复用。
各调用方通过 allowed_statuses / allowed_reserve / require_*_btn 传入自己的规则。
"""
import json
import os
from typing import Optional, List, Set

from api_client import api_post

STATUS_LABEL = {
    "0": "未运行", "1": "实盘运行中", "2": "模拟运行",
    "3": "已停止", "4": "模拟已停止",
}
RESERVE_STATUS_LABEL = {"0": "未预约", "1": "预约停止中", "2": "预约已终止"}

DETAIL_CACHE_DIR = "/tmp/quantclaw/bot_details"


def _read_cached_btn(bot_id: str) -> tuple:
    """读取 detail 缓存中的 is_reserve_stop_btn 和 is_add_pause_btn，缺失返回 (None, None)"""
    try:
        path = os.path.join(DETAIL_CACHE_DIR, f"{bot_id}.json")
        if not os.path.exists(path):
            return None, None
        with open(path) as f:
            info = json.load(f)
        return info.get("is_reserve_stop_btn"), info.get("is_add_pause_btn")
    except Exception:
        return None, None


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
            is_reserve_btn, is_pause_btn = _read_cached_btn(bid)
            if require_reserve_btn:
                if is_reserve_btn is None:
                    can_exec = False
                    reason = "未查询过机器人详情，请先查看详情后再操作"
                elif is_reserve_btn != 1:
                    can_exec = False
                    reason = "该机器人不支持预约终止操作"
            if require_pause_btn:
                if is_pause_btn is None:
                    can_exec = False
                    reason = "未查询过机器人详情，请先查看详情后再操作"
                elif is_pause_btn != 1:
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