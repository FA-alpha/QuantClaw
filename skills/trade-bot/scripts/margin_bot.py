#!/usr/bin/env python3
"""调整保证金 — /Trade/margin_do（含预检 + 实时数据）"""
import time
from typing import Optional

from api_client import api_post, check_auth
from bot_check import check_bots, filter_executable, STATUS_LABEL
from realtime_info import run as get_realtime

SAVE_TYPE_LABEL = {"6": "增加保证金", "7": "减少保证金"}

# 仅实盘运行中 (status=1)
_MARGIN_RULES = {"6": ({"1"}, None), "7": ({"1"}, None)}

# 实时数据 TTL
REALTIME_TTL = 90


def _fetch_realtime(token: str, bot_id: str, show_type: str, agent_id: str) -> dict:
    """获取实时数据，失败返回空"""
    try:
        rt = get_realtime(token, bot_id, show_type=show_type, agent_id=agent_id)
        if rt.get("status") == "ok":
            return rt
    except Exception:
        pass
    return {"status": "error", "message": "实时数据获取失败"}


def run(
    token: str,
    bot_id: str,
    amt: float,
    save_type: str,
    confirm: bool = False,
    agent_id: Optional[str] = None,
) -> dict:
    """
    增加/减少保证金

    save_type: 6=增加, 7=减少
    amt: 保证金金额

    预览时查询实时数据：
    - 增加保证金: 显示可用余额（show_type=2）
    - 减少保证金: 显示可减少保证金（show_type=3）
    """
    action_label = SAVE_TYPE_LABEL.get(save_type, f"未知操作({save_type})")

    # ── 预检 ──
    statuses, reserves = _MARGIN_RULES.get(save_type, (set(), None))
    pre = check_bots(token, [bot_id], statuses, reserves, agent_id)
    bot_state = pre["bots"][0]

    if not confirm:
        # ── 预览：拉实时数据 ──
        show_type = "2" if save_type == "6" else "3"
        realtime = _fetch_realtime(token, bot_id, show_type, agent_id)

        return {
            "status": "preview",
            "action": action_label,
            "danger_level": "red",
            "bot": bot_state,
            "can_execute": bot_state["can_execute"],
            "realtime": realtime,
            "summary": {
                "机器人 ID": bot_id,
                "操作": action_label,
                "金额": amt,
                "save_type": save_type,
            },
            "warning": f"⚠️ 即将对机器人 {bot_id} 执行「{action_label} {amt}」"
                if bot_state["can_execute"]
                else f"❌ 无法执行: {bot_state['reason']}",
        }

    # ── 执行前再次确认 ──
    executable = filter_executable(pre["bots"])
    if not executable:
        return {"status": "error", "message": f"操作被阻止: {bot_state['reason']}", "bot": bot_state}

    # ── 执行时重新拉实时数据，检查时效 ──
    show_type = "2" if save_type == "6" else "3"
    fresh_realtime = _fetch_realtime(token, bot_id, show_type, agent_id)
    stale_warning = None
    if fresh_realtime.get("status") == "ok":
        ts = fresh_realtime.get("timestamp", 0)
        age = int(time.time()) - ts
        if age > REALTIME_TTL:
            stale_warning = f"⚠️ 实时数据已过去 {age} 秒，余额可能已变化，请重新确认"

    data = api_post(
        "/Trade/margin_do",
        {
            "usertoken": token,
            "app_v": "2.0.0",
            "bot_id": bot_id,
            "amt": amt,
            "save_type": save_type,
        },
        agent_id,
    )
    ok, msg = check_auth(data)
    if not ok:
        return {"status": "error", "message": msg}

    if data.get("status") != 1:
        return {"status": "error", "message": data.get("msg", "未知错误"), "raw": data}

    result = {"status": "ok", "action": action_label, "bot_id": bot_id, "amt": amt}
    if fresh_realtime:
        result["realtime"] = fresh_realtime
    if stale_warning:
        result["stale_warning"] = stale_warning
    return result