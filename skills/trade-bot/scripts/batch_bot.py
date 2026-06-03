#!/usr/bin/env python3
"""批量操作交易机器人 — /Trade/batch_do"""
from typing import Optional

from api_client import api_post, check_auth

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

    Args:
        token: 用户 token
        bot_ids: 机器人 ID，多个逗号分隔
        save_type: 4=停止, 6=预约停止, 7=取消预约终止
        confirm: False=预览, True=执行

    Returns:
        {"status": "preview"|"ok"|"error", ...}
    """
    ids = [x.strip() for x in bot_ids.split(",") if x.strip()]
    if not ids:
        return {"status": "error", "message": "bot_ids 不能为空"}

    action_label = SAVE_TYPE_LABEL.get(save_type, f"未知操作({save_type})")

    if not confirm:
        return {
            "status": "preview",
            "action": f"批量{action_label}",
            "danger_level": "red",
            "summary": {
                "操作类型": f"{action_label} (save_type={save_type})",
                "机器人数量": len(ids),
                "机器人 ID": ids,
            },
            "warning": f"⚠️ 即将对 {len(ids)} 个机器人执行「{action_label}」操作",
        }

    data = api_post(
        "/Trade/batch_do",
        {
            "usertoken": token,
            "app_v": "2.0.0",
            "bot_id": ",".join(ids),
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
        "bot_count": len(ids),
        "bot_ids": ids,
    }
