#!/usr/bin/env python3
"""批量操作交易机器人 — /Trade/batch_do（含预检 + 二次确认）"""
from typing import Optional

from api_client import api_post, check_auth
from bot_check import check_bots, filter_executable
from agent_display import blocked_result, preview_result, ok_result, error_result
from confirm_nonce import check, create, clear

SAVE_TYPE_LABEL = {
    "4": "停止", "6": "预约停止", "7": "取消预约终止",
    "8": "暂停加仓", "9": "取消暂停加仓",
}

_BATCH_RULES = {
    "4": ({"1", "2"}, None, None),
    "6": ({"1", "2"}, {"0"}, None),
    "7": ({"1", "2"}, {"1", "2"}, None),
    "8": ({"1", "2"}, None, {"0"}),
    "9": ({"1", "2"}, None, {"1"}),
}


def run(
    token: str,
    bot_ids: str,
    save_type: str,
    agent_id: Optional[str] = None,
) -> dict:
    ids = [x.strip() for x in bot_ids.split(",") if x.strip()]
    if not ids:
        return error_result(title="❌ 参数错误", message="bot_ids 不能为空", rule="不得编造 bot_id")

    action_label = SAVE_TYPE_LABEL.get(save_type, f"未知操作({save_type})")
    statuses, reserves, pause_statuses = _BATCH_RULES.get(save_type, (set(), None, None))
    pre = check_bots(token, ids, statuses, reserves, pause_statuses, agent_id)

    state = check(agent_id or "", "batch", ids, save_type)

    if state != "confirmed":
        if pre["executable_count"] == 0:
            reasons = [f"{b['id']}: {b['reason']}" for b in pre["bots"] if not b["can_execute"]]
            return blocked_result(
                title=f"❌ 所有机器人均不可{action_label}",
                reason="\n".join(reasons),
                rule="所有目标机器人都不可操作，不得尝试绕过",
            )

        blocked_list = [f"{b['id']} ({b['status_label']}): {b['reason']}"
                        for b in pre["bots"] if not b["can_execute"]]
        exec_list = [f"{b['id']} ({b['status_label']})"
                     for b in pre["bots"] if b["can_execute"]]

        detail_lines = [f"操作: 批量{action_label}",
                        f"总数: {len(ids)}, 可执行: {pre['executable_count']}, 阻止: {pre['blocked_count']}"]
        if exec_list:
            detail_lines.append(f"可执行: {', '.join(exec_list)}")
        if blocked_list:
            detail_lines.append(f"已跳过: {'; '.join(blocked_list)}")
        rule = "等待用户确认，不得自行操作"
        if state == "expired":
            detail_lines.append("上一次确认超时，请重新确认")
            rule = "上一次确认超时，等待用户重新确认，不得自行操作"

        create(agent_id or "", "batch", ids, save_type)
        return preview_result(
            title=f"⚠️ 批量{action_label} - 待确认",
            detail_lines=detail_lines,
            rule=rule,
            action=f"批量{action_label}",
            save_type=save_type,
            executable_count=pre["executable_count"],
            blocked_count=pre["blocked_count"],
            bots=pre["bots"],
        )

    exec_ids = filter_executable(pre["bots"])
    if not exec_ids:
        clear(agent_id or "", "batch", ids, save_type)
        return blocked_result(
            title=f"❌ 所有机器人都无法{action_label}",
            reason="执行前校验: 所有机器人均不可操作",
            rule="不得尝试绕过",
        )

    data = api_post(
        "/Trade/batch_do",
        {"usertoken": token, "app_v": "2.0.0", "bot_id": ",".join(exec_ids), "save_type": save_type},
        agent_id,
    )
    clear(agent_id or "", "batch", ids, save_type)

    ok_msg, msg = check_auth(data)
    if not ok_msg:
        return error_result(title=f"❌ 批量{action_label}失败", message=msg, rule="不得自行重试")
    if data.get("status") != 1:
        return error_result(title=f"❌ 批量{action_label}失败",
                            message=data.get("msg", "未知错误"), rule="不得自行重试")

    return ok_result(
        title=f"✅ 批量{action_label}成功",
        detail_lines=[f"执行: {len(exec_ids)} 个", f"跳过: {len(ids) - len(exec_ids)} 个"],
        action=f"批量{action_label}",
        executed=len(exec_ids),
        skipped=len(ids) - len(exec_ids),
        bot_ids=exec_ids,
    )