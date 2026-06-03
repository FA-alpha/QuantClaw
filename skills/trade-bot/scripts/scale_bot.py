#!/usr/bin/env python3
"""手动加仓/取消加仓 — /Trade/scale_do（含预检 /Trade/batch_check_status）"""
from typing import Optional

from api_client import api_post, check_auth
from bot_check import check_bots, filter_executable, STATUS_LABEL

SAVE_TYPE_LABEL = {"8": "手动加仓", "9": "取消加仓"}

# 仅实盘运行中 (status=1)
_SCALE_RULES = {"8": ({"1"}, None), "9": ({"1"}, None)}


def run(
    token: str,
    bot_id: str,
    save_type: str,
    price: Optional[float] = None,
    amt: Optional[float] = None,
    order_id: Optional[str] = None,
    confirm: bool = False,
    agent_id: Optional[str] = None,
) -> dict:
    """
    手动加仓 / 取消加仓

    save_type=8 必传: price, amt
    save_type=9 必传: order_id

    Returns:
        {"status": "preview"|"ok"|"error", ...}
    """
    action_label = SAVE_TYPE_LABEL.get(save_type, f"未知操作({save_type})")

    # ── 预检 ──
    statuses, reserves = _SCALE_RULES.get(save_type, (set(), None))
    pre = check_bots(token, [bot_id], statuses, reserves, agent_id)
    bot_state = pre["bots"][0]

    if not confirm:
        return {
            "status": "preview",
            "action": action_label,
            "danger_level": "yellow",
            "bot": bot_state,
            "can_execute": bot_state["can_execute"],
            "summary": {
                "机器人 ID": bot_id,
                "操作": action_label,
                "save_type": save_type,
                **({"price": price, "amt": amt} if save_type == "8" else {"order_id": order_id}),
            },
            "warning": f"⚠️ 即将对机器人 {bot_id} 执行「{action_label}」"
                if bot_state["can_execute"]
                else f"❌ 无法执行: {bot_state['reason']}",
        }

    # ── 执行前再次确认 ──
    executable = filter_executable(pre["bots"])
    if not executable:
        return {"status": "error", "message": f"操作被阻止: {bot_state['reason']}", "bot": bot_state}

    params = {
        "usertoken": token,
        "app_v": "2.0.0",
        "bot_id": bot_id,
        "save_type": save_type,
    }
    if save_type == "8":
        if price is None or amt is None:
            return {"status": "error", "message": "手动加仓需要 price 和 amt 参数"}
        params["price"] = price
        params["amt"] = amt
    elif save_type == "9":
        if not order_id:
            return {"status": "error", "message": "取消加仓需要 order_id 参数"}
        params["order_id"] = order_id

    data = api_post("/Trade/scale_do", params, agent_id)
    ok, msg = check_auth(data)
    if not ok:
        return {"status": "error", "message": msg}

    if data.get("status") != 1:
        return {"status": "error", "message": data.get("msg", "未知错误"), "raw": data}

    return {"status": "ok", "action": action_label, "bot_id": bot_id}
