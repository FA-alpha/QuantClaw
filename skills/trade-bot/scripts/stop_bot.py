#!/usr/bin/env python3
"""单个机器人操作 — /Trade/status_do"""
from typing import Optional

from api_client import api_post, check_auth

SAVE_TYPE_LABEL = {
    "4": "停止",
    "5": "停止当周期",
    "6": "预约停止",
    "7": "取消预约终止",
}
STATUS_LABEL = {"0": "未运行", "1": "实盘运行中", "2": "模拟运行", "3": "已停止"}


def run(
    token: str,
    bot_id: str,
    save_type: str,
    confirm: bool = False,
    agent_id: Optional[str] = None,
) -> dict:
    """
    单个机器人操作（停止 / 重启 / 预约停止 / 取消预约）

    Args:
        token: 用户 token
        bot_id: 机器人 ID
        save_type: 4=停止, 5=停止当周期, 6=预约停止, 7=取消预约终止
        confirm: False=预览, True=执行

    Returns:
        {"status": "preview"|"ok"|"error", ...}
    """
    action_label = SAVE_TYPE_LABEL.get(save_type, f"未知操作({save_type})")

    if not confirm:
        return {
            "status": "preview",
            "action": action_label,
            "danger_level": "red",
            "summary": {
                "机器人 ID": bot_id,
                "操作": action_label,
                "save_type": save_type,
            },
            "warning": f"⚠️ 即将对机器人 {bot_id} 执行「{action_label}」",
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
    return {
        "status": "ok",
        "action": action_label,
        "bot_id": bot_id,
        "bot_status": info.get("status"),
        "bot_status_label": STATUS_LABEL.get(str(info.get("status")), ""),
    }
