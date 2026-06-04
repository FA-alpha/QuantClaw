#!/usr/bin/env python3
"""手动加仓/取消加仓 — /Trade/scale_do（含预检 + 实时数据）"""
import time
from typing import Optional

from api_client import api_post, check_auth
from bot_check import check_bots, filter_executable, STATUS_LABEL
from realtime_info import run as get_realtime

SAVE_TYPE_LABEL = {"8": "手动加仓", "9": "取消加仓"}

# 仅实盘运行中 (status=1)
_SCALE_RULES = {"8": ({"1"}, None), "9": ({"1"}, None)}

# 实时数据有效期（秒），超时后执行时需重新确认
REALTIME_TTL = 90


def _fetch_realtime(token: str, bot_id: str, agent_id: str) -> dict:
    """获取实时数据（币价+余额），失败返回空"""
    try:
        rt = get_realtime(token, bot_id, show_type="1,2", agent_id=agent_id)
        if rt.get("status") == "ok":
            return rt
    except Exception:
        pass
    return {"status": "error", "message": "实时数据获取失败"}


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

    预览时附带实时币价+可用余额辅助决策。
    执行时重新拉取实时数据，标记是否过期。
    """
    action_label = SAVE_TYPE_LABEL.get(save_type, f"未知操作({save_type})")

    # ── 预检 ──
    statuses, reserves = _SCALE_RULES.get(save_type, (set(), None))
    pre = check_bots(token, [bot_id], statuses, reserves, agent_id)
    bot_state = pre["bots"][0]

    if not confirm:
        # ── 预览：拉实时数据 ──
        realtime = _fetch_realtime(token, bot_id, agent_id) if save_type == "8" else None

        summary = {
            "机器人 ID": bot_id,
            "操作": action_label,
            "save_type": save_type,
        }
        if save_type == "8":
            summary["price"] = price
            summary["amt"] = amt

        return {
            "status": "preview",
            "action": action_label,
            "danger_level": "yellow",
            "bot": bot_state,
            "can_execute": bot_state["can_execute"],
            "realtime": realtime,  # 实时数据（币价+余额）
            "summary": summary,
            "warning": f"⚠️ 即将对机器人 {bot_id} 执行「{action_label}」"
                if bot_state["can_execute"]
                else f"❌ 无法执行: {bot_state['reason']}",
        }

    # ── 执行前再次确认 ──
    executable = filter_executable(pre["bots"])
    if not executable:
        return {"status": "error", "message": f"操作被阻止: {bot_state['reason']}", "bot": bot_state}

    # ── 执行时重新拉实时数据，检查时效 ──
    fresh_realtime = None
    stale_warning = None
    if save_type == "8":
        fresh_realtime = _fetch_realtime(token, bot_id, agent_id)
        if fresh_realtime.get("status") == "ok":
            ts = fresh_realtime.get("timestamp", 0)
            age = int(time.time()) - ts
            if age > REALTIME_TTL:
                stale_warning = f"⚠️ 实时数据已过去 {age} 秒，价格可能已变化，请重新确认"

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

    result = {"status": "ok", "action": action_label, "bot_id": bot_id}
    if fresh_realtime:
        result["realtime"] = fresh_realtime
    if stale_warning:
        result["stale_warning"] = stale_warning
    return result