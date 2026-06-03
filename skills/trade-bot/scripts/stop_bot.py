#!/usr/bin/env python3
"""单个机器人操作 — /Trade/status_do（含预检 /Trade/batch_check_status）"""
from typing import Optional

from api_client import api_post, check_auth
from bot_check import check_bots, filter_executable, STATUS_LABEL

SAVE_TYPE_LABEL = {
    "4": "停止",
    "5": "停止当周期",
    "6": "预约停止",
    "7": "取消预约终止",
}


def run(
    token: str,
    bot_id: str,
    save_type: str,
    confirm: bool = False,
    agent_id: Optional[str] = None,
) -> dict:
    """
    单个机器人操作（停止 / 重启 / 预约停止 / 取消预约）

    - 预览时自动查询 bot 当前状态，判断操作是否可执行
    - 确认执行前再次检查状态，过滤无效操作

    Returns:
        {"status": "preview"|"ok"|"error", ...}
    """
    action_label = SAVE_TYPE_LABEL.get(save_type, f"未知操作({save_type})")

    # ── 预检 ──
    pre = check_bots(token, [bot_id], save_type, agent_id)
    bot_state = pre["bots"][0]

    if not confirm:
        return {
            "status": "preview",
            "action": action_label,
            "danger_level": "red",
            "bot": bot_state,
            "can_execute": bot_state["can_execute"],
            "summary": {
                "机器人 ID": bot_id,
                "操作": action_label,
                "save_type": save_type,
            },
            "warning": f"⚠️ 即将对机器人 {bot_id} 执行「{action_label}」"
                if bot_state["can_execute"]
                else f"❌ 无法执行: {bot_state['reason']}",
        }

    # ── 执行前再次确认状态 ──
    executable = filter_executable(pre["bots"])
    if not executable:
        return {
            "status": "error",
            "message": f"操作被阻止: {bot_state['reason']}",
            "bot": bot_state,
        }

    data = api_post(
        "/Trade/status_do",
        {
            "usertoken": token,
            "app_v": "2.0.0",
            "bot_id": bot_id,
            "save_type": save_type,
        },
        agent_id,
    )
    ok, msg = check_auth(data)
    if not ok:
        return {"status": "error", "message": msg}

    if data.get("status") != 1:
        return {"status": "error", "message": data.get("msg", "未知错误"), "raw": data}

    info = data.get("info", {})
    new_status = str(info.get("status", ""))
    return {
        "status": "ok",
        "action": action_label,
        "bot": {
            "id": bot_id,
            "status": info.get("status"),
            "status_label": STATUS_LABEL.get(new_status, new_status),
            "before": {
                "status": bot_state["status"],
                "status_label": bot_state["status_label"],
            },
        },
    }
