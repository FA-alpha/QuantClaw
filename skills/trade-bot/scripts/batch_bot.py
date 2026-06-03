#!/usr/bin/env python3
"""批量操作交易机器人 — /Trade/batch_do（含预检 /Trade/batch_check_status）"""
from typing import Optional

from api_client import api_post, check_auth
from bot_check import check_bots, filter_executable, STATUS_LABEL

SAVE_TYPE_LABEL = {
    "4": "停止",
    "6": "预约停止",
    "7": "取消预约终止",
}


def run(
    token: str,
    bot_ids: str,
    save_type: str,
    confirm: bool = False,
    agent_id: Optional[str] = None,
) -> dict:
    """
    批量操作机器人（停止 / 预约停止 / 取消预约终止）

    - 预览时查询所有 bot 当前状态，标记可执行/不可执行
    - 确认执行时只对可执行的 bot 调 API

    Returns:
        {"status": "preview"|"ok"|"error", ...}
    """
    ids = [x.strip() for x in bot_ids.split(",") if x.strip()]
    if not ids:
        return {"status": "error", "message": "bot_ids 不能为空"}

    action_label = SAVE_TYPE_LABEL.get(save_type, f"未知操作({save_type})")

    # ── 预检 ──
    pre = check_bots(token, ids, save_type, agent_id)

    if not confirm:
        return {
            "status": "preview",
            "action": f"批量{action_label}",
            "danger_level": "red",
            "bots": pre["bots"],
            "executable_count": pre["executable_count"],
            "blocked_count": pre["blocked_count"],
            "summary": {
                "操作类型": f"{action_label} (save_type={save_type})",
                "总数": len(ids),
                "可执行": pre["executable_count"],
                "被阻止": pre["blocked_count"],
            },
            "warning": f"⚠️ 即将对 {pre['executable_count']} 个机器人执行「{action_label}」"
                if pre["executable_count"] > 0
                else "❌ 所有机器人均不可执行此操作",
        }

    # ── 执行前过滤 ──
    exec_ids = filter_executable(pre["bots"])
    if not exec_ids:
        return {
            "status": "error",
            "message": "所有机器人均不可执行此操作",
            "bots": pre["bots"],
        }

    data = api_post(
        "/Trade/batch_do",
        {
            "usertoken": token,
            "app_v": "2.0.0",
            "bot_id": ",".join(exec_ids),
            "save_type": save_type,
        },
        agent_id,
    )
    ok, msg = check_auth(data)
    if not ok:
        return {"status": "error", "message": msg}

    if data.get("status") != 1:
        return {"status": "error", "message": data.get("msg", "未知错误"), "raw": data}

    return {
        "status": "ok",
        "action": f"批量{action_label}",
        "executed": len(exec_ids),
        "skipped": len(ids) - len(exec_ids),
        "bot_ids": exec_ids,
    }
