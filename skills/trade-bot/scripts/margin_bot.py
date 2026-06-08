#!/usr/bin/env python3
"""调整保证金 — /Trade/margin_do（含预检 + 实时数据 + 二次确认）"""
import time
from typing import Optional, Union

from api_client import api_post, check_auth
from bot_check import check_bots, filter_executable
from realtime_info import run as get_realtime
from agent_display import blocked_result, prompt_result, preview_result, ok_result, error_result
from confirm_nonce import check, create, clear

SAVE_TYPE_LABEL = {"6": "增加保证金", "7": "减少保证金"}
REALTIME_TTL = 90
_MARGIN_RULES = {"6": ({"1", "2"}, None), "7": ({"1", "2"}, None)}
TYPE_LABEL_MAP = {"2": "可用余额", "3": "可减少保证金"}


def _fetch_max(token: str, bot_id: str, save_type: str, agent_id: str) -> Union[dict, None]:
    show_type = "2" if save_type == "6" else "3"
    try:
        rt = get_realtime(token, bot_id, show_type=show_type, agent_id=agent_id)
        if rt.get("status") == "ok":
            for it in rt.get("items", []):
                if it.get("type") == show_type and it.get("amt") is not None:
                    return {"value": float(it["amt"]), "timestamp": rt.get("timestamp", 0),
                            "timestamp_label": rt.get("timestamp_label", ""),
                            "type_label": TYPE_LABEL_MAP.get(show_type, "")}
    except Exception:
        pass
    return None


def run(
    token: str,
    bot_id: str,
    amt: Optional[float] = None,
    save_type: str = "6",
    agent_id: Optional[str] = None,
) -> dict:
    action_label = SAVE_TYPE_LABEL.get(save_type, f"未知操作({save_type})")

    statuses, reserves = _MARGIN_RULES.get(save_type, (set(), None))
    pre = check_bots(token, [bot_id], statuses, reserves, agent_id=agent_id)
    bot_state = pre["bots"][0]
    if not bot_state["can_execute"]:
        return blocked_result(
            title=f"❌ 无法{action_label}",
            reason=bot_state["reason"],
            rule="该机器人不可操作，不得尝试绕过",
        )

    max_info = _fetch_max(token, bot_id, save_type, agent_id)
    type_label = TYPE_LABEL_MAP.get("2" if save_type == "6" else "3", "")

    state = check(agent_id or "", "margin", bot_id, save_type, str(amt))

    # 没传金额 → 引导输入
    if amt is None and state != "confirmed":
        if max_info is None:
            return error_result(
                title=f"❌ 无法获取{type_label}",
                message=f"实时数据获取失败，无法查询{type_label}",
                rule="不得编造金额，请告知用户稍后重试",
            )
        return prompt_result(
            title=f"📝 {action_label}",
            prompt_text=f"当前{type_label}: {max_info['value']} ({max_info['timestamp_label']})\n请输入要{action_label}的具体金额",
            rule="必须等待用户输入金额，不得代为决定",
            bot_id=bot_id, action=action_label,
            max_available=max_info["value"], max_label=type_label,
            realtime_ts=max_info["timestamp_label"],
        )

    # 有金额, 未确认 → 校验 + 预览
    if state != "confirmed":
        if max_info is not None and amt > max_info["value"]:
            return blocked_result(
                title=f"⚠️ {action_label}超额",
                reason=f"请求 {amt} 超出{type_label} {max_info['value']}（{max_info['timestamp_label']}）",
                rule="必须等待用户重新输入合法金额，不得自行调小金额",
                user_prompt=f"请输入不超过 {max_info['value']} 的金额",
                requested=amt, max_available=max_info["value"], max_label=type_label,
            )

        detail_lines = [
            f"机器人: {bot_id}",
            f"操作: {action_label}",
            f"金额: {amt}",
            f"{type_label}: {max_info['value']}" if max_info else f"{type_label}: 未知",
        ]
        if state == "expired":
            detail_lines.append(f"{action_label}操作未能执行，确认操作已超时（5分钟），需要用户重新确认")
            rule = f"{action_label}确认超时（5分钟），请重新确认后原样重跑相同命令"
        else:
            rule = "等待用户确认后，原样重跑相同命令即可执行"
        create(agent_id or "", "margin", bot_id, save_type, str(amt))
        return preview_result(
            title=f"⚠️ {action_label} - 待确认",
            detail_lines=detail_lines,
            rule=rule,
            user_prompt=f"确认{action_label} {amt}？回复「确认」或「取消」",
            bot_id=bot_id, action=action_label, amt=amt, save_type=save_type,
            max_available=max_info["value"] if max_info else None, max_label=type_label,
        )

    # 已确认，执行
    executable = filter_executable(pre["bots"])
    if not executable:
        clear(agent_id or "", "margin", bot_id, save_type, str(amt))
        return blocked_result(
            title=f"❌ 无法{action_label}",
            reason=bot_state["reason"],
            rule="该机器人不可操作，不得尝试绕过",
        )

    fresh_max = _fetch_max(token, bot_id, save_type, agent_id)
    stale_warning = None

    if fresh_max is not None:
        age = int(time.time()) - fresh_max["timestamp"]
        if age > REALTIME_TTL:
            stale_warning = f"实时数据已过去 {age} 秒，余额可能已变化"
        if amt > fresh_max["value"]:
            clear(agent_id or "", "margin", bot_id, save_type, str(amt))
            return blocked_result(
                title=f"⚠️ {action_label}超额（执行时校验）",
                reason=f"请求 {amt} 超出当前{type_label} {fresh_max['value']}（{fresh_max['timestamp_label']}）",
                rule="必须等待用户重新输入合法金额",
                user_prompt=f"当前{type_label}: {fresh_max['value']}，请重新输入金额",
                requested=amt, max_available=fresh_max["value"],
            )

    data = api_post(
        "/Trade/margin_do",
        {"usertoken": token, "app_v": "2.0.0", "bot_id": bot_id, "amt": amt, "save_type": save_type},
        agent_id,
    )
    clear(agent_id or "", "margin", bot_id, save_type, str(amt))
    ok_msg, msg = check_auth(data)
    if not ok_msg:
        return error_result(title=f"❌ {action_label}失败", message=msg, rule="不得自行重试，请告知用户错误信息")
    if data.get("status") != 1:
        return error_result(title=f"❌ {action_label}失败",
                            message=data.get("msg", data.get("info", "未知错误")), rule="不得自行重试")

    result_lines = [f"机器人: {bot_id}", f"操作: {action_label}", f"金额: {amt}"]
    if stale_warning:
        result_lines.append(stale_warning)
    return ok_result(
        title=f"✅ {action_label}成功",
        detail_lines=result_lines,
        action=action_label, bot_id=bot_id, amt=amt,
        stale_warning=stale_warning,
    )