#!/usr/bin/env python3
"""单个机器人操作 — /Trade/status_do（含预检）"""
from typing import Optional

from api_client import api_post, check_auth
from bot_check import check_bots, filter_executable, STATUS_LABEL
from agent_display import blocked_result, preview_result, ok_result, error_result

SAVE_TYPE_LABEL = {
    "4": "停止", "5": "停止当周期", "6": "预约停止",
    "7": "取消预约终止", "8": "暂停加仓", "9": "取消暂停加仓",
}

_STOP_RULES = {
    "4": ({"1", "2"}, None, None),
    "5": ({"1", "2"}, None, None),
    "6": ({"1", "2"}, {"0"}, None),
    "7": ({"1", "2"}, {"1", "2"}, None),
    "8": ({"1", "2"}, None, {"0"}),
    "9": ({"1", "2"}, None, {"1"}),
}


def run(
    token: str,
    bot_id: str,
    save_type: str,
    confirm: bool = False,
    agent_id: Optional[str] = None,
) -> dict:
    action_label = SAVE_TYPE_LABEL.get(save_type, f"未知操作({save_type})")

    statuses, reserves, pause_statuses = _STOP_RULES.get(save_type, (set(), None, None))
    pre = check_bots(token, [bot_id], statuses, reserves, pause_statuses, agent_id)
    bot_state = pre["bots"][0]

    if not confirm:
        if not bot_state["can_execute"]:
            return blocked_result(
                title=f"❌ 无法{action_label}",
                reason=bot_state["reason"],
                rule="该机器人不可执行此操作，不得尝试绕过",
            )
        return preview_result(
            title=f"⚠️ {action_label} - 待确认",
            detail_lines=[
                f"机器人: {bot_id}",
                f"当前状态: {bot_state['status_label']}",
                f"操作: {action_label}",
            ],
            rule="必须等待用户确认后才执行，不得自行跳过确认步骤",
            bot_id=bot_id,
            action=action_label,
            save_type=save_type,
            bot_state=bot_state,
        )

    executable = filter_executable(pre["bots"])
    if not executable:
        return blocked_result(
            title=f"❌ 无法{action_label}",
            reason=bot_state["reason"],
            rule="该机器人不可执行此操作",
        )

    data = api_post(
        "/Trade/status_do",
        {"usertoken": token, "app_v": "2.0.0", "bot_id": bot_id, "save_type": save_type},
        agent_id,
    )
    ok_msg, msg = check_auth(data)
    if not ok_msg:
        return error_result(title=f"❌ {action_label}失败", message=msg, rule="不得自行重试")
    if data.get("status") != 1:
        return error_result(title=f"❌ {action_label}失败",
                            message=data.get("msg", "未知错误"), rule="不得自行重试")

    info = data.get("info", {})
    new_status = str(info.get("status", ""))
    return ok_result(
        title=f"✅ {action_label}成功",
        detail_lines=[
            f"机器人: {bot_id}",
            f"{bot_state['status_label']} → {STATUS_LABEL.get(new_status, new_status)}",
        ],
        bot_id=bot_id,
        action=action_label,
        before_status=bot_state["status_label"],
        after_status=STATUS_LABEL.get(new_status, new_status),
    )
