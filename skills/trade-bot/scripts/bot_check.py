#!/usr/bin/env python3
"""机器人状态批量查询 — /Trade/batch_check_status

供 stop / batch 等写操作前的预检复用。
"""
from typing import Optional, List

from api_client import api_post

STATUS_LABEL = {
    "0": "未运行", "1": "实盘运行中", "2": "模拟运行",
    "3": "已停止", "4": "模拟已停止",
}
RESERVE_STATUS_LABEL = {"0": "未预约", "1": "预约停止中", "2": "预约已终止"}

# 各操作允许的 bot status
_allowed_status = {
    "4": {"1", "2"},    # 停止 → 仅运行中
    "5": {"1", "2"},    # 停止当周期 → 仅运行中
    "6": {"1", "2"},    # 预约停止 → 仅运行中
    "7": {"1", "2"},    # 取消预约终止 → 仅运行中
}

# 各操作允许的 reserve_status（未列出的 save_type 不检查 reserve_status）
_allowed_reserve = {
    "6": {"0"},          # 预约停止 → 不在预约中
    "7": {"1", "2"},     # 取消预约 → 仅在预约中
}


def check_bots(
    token: str,
    bot_ids: List[str],
    save_type: str,
    agent_id: Optional[str] = None,
) -> dict:
    """
    批量查询机器人状态，并判断操作是否可执行。

    Returns:
        {
            "bots": [{"id", "status", "status_label", "reserve_status",
                      "reserve_status_label", "can_execute", "reason"|null}],
            "executable_count": int,
            "blocked_count": int,
        }
    """
    data = api_post(
        "/Trade/batch_check_status",
        {"usertoken": token, "app_v": "2.0.0", "bot_id": ",".join(bot_ids)},
        agent_id,
    )
    # 鉴权失败 / 网络错误
    if data.get("_error") or data.get("status") != 1:
        # 不回退，返回不可判断状态
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

    allowed_status = _allowed_status.get(save_type, set())
    allowed_reserve = _allowed_reserve.get(save_type, set())
    check_reserve = save_type in _allowed_reserve  # 仅 6,7 检查

    bots = []
    executable = 0
    blocked = 0

    info_list = data.get("info", [])
    for i, bid in enumerate(bot_ids):
        item = info_list[i] if i < len(info_list) else {}
        s = str(item.get("status", ""))
        r = str(item.get("reserve_status", ""))

        can_exec = True
        reason = None

        if item:
            if s not in allowed_status:
                can_exec = False
                reason = f"当前状态为「{STATUS_LABEL.get(s, s)}」，不支持此操作"
            elif check_reserve and r not in allowed_reserve:
                can_exec = False
                reason = f"预约状态为「{RESERVE_STATUS_LABEL.get(r, r)}」，不支持此操作"

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
