#!/usr/bin/env python3
"""调整保证金 — /Trade/margin_do（含预检 + 实时数据校验）"""
import time
from typing import Optional, Union

from api_client import api_post, check_auth
from bot_check import check_bots, filter_executable, STATUS_LABEL
from realtime_info import run as get_realtime

SAVE_TYPE_LABEL = {"6": "增加保证金", "7": "减少保证金"}
REALTIME_TTL = 90
_MARGIN_RULES = {"6": ({"1"}, None), "7": ({"1"}, None)}

TYPE_LABEL_MAP = {"2": "可用余额", "3": "可减少保证金"}


def _fetch_max(token: str, bot_id: str, save_type: str, agent_id: str) -> Union[float, None]:
    """拉实时数据，取最大可用/可减金额。失败返 None"""
    show_type = "2" if save_type == "6" else "3"
    try:
        rt = get_realtime(token, bot_id, show_type=show_type, agent_id=agent_id)
        if rt.get("status") == "ok":
            items = rt.get("items", [])
            for it in items:
                if it.get("type") == show_type:
                    amt_val = it.get("amt")
                    if amt_val is not None:
                        return {"value": float(amt_val), "timestamp": rt.get("timestamp", 0),
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
    confirm: bool = False,
    agent_id: Optional[str] = None,
) -> dict:
    """
    增加/减少保证金

    amt 为 None 时: 仅查询最大可用金额，引导用户输入
    amt 有值时:
      - 未超出 → 正常预览 → 确认 → 执行
      - 超出   → 返回超额错误 + max_available

    save_type: 6=增加, 7=减少
    """
    action_label = SAVE_TYPE_LABEL.get(save_type, f"未知操作({save_type})")

    # ── 预检 ──
    statuses, reserves = _MARGIN_RULES.get(save_type, (set(), None))
    pre = check_bots(token, [bot_id], statuses, reserves, agent_id)
    bot_state = pre["bots"][0]
    if not bot_state["can_execute"]:
        return {
            "status": "error",
            "message": bot_state["reason"],
            "bot": bot_state,
        }

    # ── 拉实时数据 ──
    max_info = _fetch_max(token, bot_id, save_type, agent_id)

    type_label = TYPE_LABEL_MAP.get("2" if save_type == "6" else "3", "")

    # ── 模式1: 没传金额 → 展示最大可用, 引导输入 ──
    if amt is None and not confirm:
        if max_info is None:
            return {
                "status": "error",
                "message": f"无法获取{type_label}数据",
                "bot": bot_state,
            }
        return {
            "status": "prompt",
            "action": action_label,
            "bot": bot_state,
            "max_available": max_info["value"],
            "max_label": type_label,
            "realtime_ts": max_info["timestamp_label"],
            "prompt": f"当前{type_label}: {max_info['value']}，请输入要操作的具体金额",
            "example": f"--amt {max_info['value']}  # 全额操作",
        }

    # ── 模式2: 有金额, 非 confirm → 校验额度 ──
    if not confirm:
        if max_info is not None and amt > max_info["value"]:
            return {
                "status": "exceeded",
                "action": action_label,
                "bot": bot_state,
                "requested": amt,
                "max_available": max_info["value"],
                "max_label": type_label,
                "realtime_ts": max_info["timestamp_label"],
                "message": f"请求金额 {amt} 超出最大可操作金额 {max_info['value']}（{type_label}）",
            }

        return {
            "status": "preview",
            "action": action_label,
            "danger_level": "red",
            "bot": bot_state,
            "can_execute": True,
            "max_available": max_info["value"] if max_info else None,
            "max_label": type_label,
            "realtime_ts": max_info["timestamp_label"] if max_info else None,
            "summary": {"机器人 ID": bot_id, "操作": action_label, "金额": amt, "save_type": save_type},
            "warning": f"⚠️ 即将对机器人 {bot_id} 执行「{action_label} {amt}」",
        }

    # ── 模式3: confirm 执行 ──
    executable = filter_executable(pre["bots"])
    if not executable:
        return {"status": "error", "message": f"操作被阻止: {bot_state['reason']}", "bot": bot_state}

    # 执行前重新拉实时数据校验
    fresh_max = _fetch_max(token, bot_id, save_type, agent_id)
    stale_warning = None

    if fresh_max is not None:
        age = int(time.time()) - fresh_max["timestamp"]
        if age > REALTIME_TTL:
            stale_warning = f"⚠️ 实时数据已过去 {age} 秒，余额可能已变化"
        if amt > fresh_max["value"]:
            return {
                "status": "exceeded",
                "action": action_label,
                "requested": amt,
                "max_available": fresh_max["value"],
                "max_label": type_label,
                "realtime_ts": fresh_max["timestamp_label"],
                "message": f"执行时重新校验: 请求金额 {amt} 超出当前{type_label} {fresh_max['value']}",
            }

    data = api_post(
        "/Trade/margin_do",
        {"usertoken": token, "app_v": "2.0.0", "bot_id": bot_id, "amt": amt, "save_type": save_type},
        agent_id,
    )
    ok, msg = check_auth(data)
    if not ok:
        return {"status": "error", "message": msg}
    if data.get("status") != 1:
        return {"status": "error", "message": data.get("msg", "未知错误"), "raw": data}

    result = {"status": "ok", "action": action_label, "bot_id": bot_id, "amt": amt}
    if fresh_max:
        result["realtime"] = {"timestamp_label": fresh_max["timestamp_label"], type_label: fresh_max["value"]}
    if stale_warning:
        result["stale_warning"] = stale_warning
    return result
