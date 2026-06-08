#!/usr/bin/env python3
"""手动加仓/取消加仓 — /Trade/scale_do（含预检 + 实时数据 + 二次确认）"""
import time
from typing import Optional

from api_client import api_post, check_auth
from bot_check import check_bots, filter_executable
from realtime_info import run as get_realtime
from agent_display import blocked_result, prompt_result, preview_result, ok_result, error_result
from confirm_nonce import check, create, clear

SAVE_TYPE_LABEL = {"8": "手动加仓", "9": "取消加仓"}
_SCALE_RULES = {"8": ({"1", "2"}, None), "9": ({"1", "2"}, None)}
REALTIME_TTL = 90


def _fetch_realtime(token: str, bot_id: str, show_type: str, agent_id: str) -> dict:
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
    save_type: str,
    price: Optional[float] = None,
    amt: Optional[float] = None,
    order_id: Optional[str] = None,
    agent_id: Optional[str] = None,
) -> dict:
    action_label = SAVE_TYPE_LABEL.get(save_type, f"未知操作({save_type})")

    statuses, reserves = _SCALE_RULES.get(save_type, (set(), None))
    pre = check_bots(token, [bot_id], statuses, reserves, agent_id=agent_id)
    bot_state = pre["bots"][0]
    if not bot_state["can_execute"]:
        return blocked_result(
            title=f"❌ 无法{action_label}",
            reason=bot_state["reason"],
            rule="该机器人不可操作，不得尝试绕过",
        )

    # ── 取消加仓 ──
    if save_type == "9":
        state = check(agent_id or "", "scale", bot_id, save_type, order_id)
        if state != "confirmed":
            if not order_id:
                return prompt_result(
                    title=f"📝 {action_label}",
                    prompt_text="请输入要取消的网格订单ID (order_id)",
                    rule="必须等待用户提供 order_id，不得编造",
                )
            detail_lines = [f"机器人: {bot_id}", f"操作: {action_label}", f"订单ID: {order_id}"]
            if state == "expired":
                detail_lines.append(f"{action_label}操作未能执行，确认操作已超时（5分钟），需要用户重新确认")
                rule = f"{action_label}确认超时（5分钟），请重新确认后原样重跑相同命令"
            else:
                rule = "等待用户确认后，原样重跑相同命令即可执行"
            create(agent_id or "", "scale", bot_id, save_type, order_id)
            return preview_result(
                title=f"⚠️ {action_label} - 待确认",
                detail_lines=detail_lines,
                rule=rule,
                bot_id=bot_id, action=action_label, order_id=order_id,
            )

        executable = filter_executable(pre["bots"])
        if not executable:
            clear(agent_id or "", "scale", bot_id, save_type, order_id)
            return blocked_result(title=f"❌ 无法{action_label}", reason=bot_state["reason"],
                                  rule="该机器人不可操作")
        params = {"usertoken": token, "app_v": "2.0.0", "bot_id": bot_id, "save_type": save_type, "order_id": order_id}
        data = api_post("/Trade/scale_do", params, agent_id)
        clear(agent_id or "", "scale", bot_id, save_type, order_id)
        ok_msg, msg = check_auth(data)
        if not ok_msg:
            return error_result(title=f"❌ {action_label}失败", message=msg, rule="不得自行重试")
        if data.get("status") != 1:
            return error_result(title=f"❌ {action_label}失败",
                                message=data.get("msg", "未知错误"), rule="不得自行重试")
        return ok_result(title=f"✅ {action_label}成功",
                         detail_lines=[f"机器人: {bot_id}", f"订单: {order_id}"],
                         bot_id=bot_id)

    # ── 手动加仓(save_type=8) ──
    realtime = _fetch_realtime(token, bot_id, "1,2", agent_id)
    state = check(agent_id or "", "scale", bot_id, save_type, str(price), str(amt))

    if state != "confirmed":
        if price is None or amt is None:
            lines = [f"机器人: {bot_id}", f"操作: {action_label}"]
            if realtime.get("status") == "ok":
                ts = realtime.get("timestamp_label", "")
                for it in realtime.get("items", []):
                    lines.append(f"{it['type_label']}: {it['amt']} ({ts})")
            lines.append("")
            lines.append("请输入加仓价格和金额，例如: --price 78 --amt 100")
            return prompt_result(
                title=f"📝 {action_label}",
                prompt_text="\n".join(lines),
                rule="必须等待用户输入价格和金额，不得编造",
                bot_id=bot_id,
                realtime=realtime if realtime.get("status") == "ok" else None,
            )

        detail_lines = [f"机器人: {bot_id}", f"操作: {action_label}",
                        f"加仓价格: {price}", f"加仓金额: {amt}"]
        if realtime.get("status") == "ok":
            ts = realtime.get("timestamp_label", "")
            for it in realtime.get("items", []):
                detail_lines.append(f"{it['type_label']}: {it['amt']} ({ts})")
        if state == "expired":
            detail_lines.append(f"{action_label}操作未能执行，确认操作已超时（5分钟），需要用户重新确认")
            rule = f"{action_label}确认超时（5分钟），请重新确认后原样重跑相同命令"
        else:
            rule = "等待用户确认后，原样重跑相同命令即可执行"
        create(agent_id or "", "scale", bot_id, save_type, str(price), str(amt))
        return preview_result(
            title=f"⚠️ {action_label} - 待确认",
            detail_lines=detail_lines,
            rule=rule,
            bot_id=bot_id, action=action_label,
            price=price, amt=amt,
            realtime=realtime if realtime.get("status") == "ok" else None,
        )

    executable = filter_executable(pre["bots"])
    if not executable:
        clear(agent_id or "", "scale", bot_id, save_type, str(price), str(amt))
        return blocked_result(title=f"❌ 无法{action_label}", reason=bot_state["reason"],
                              rule="该机器人不可操作")

    if price is None or amt is None:
        clear(agent_id or "", "scale", bot_id, save_type, str(price), str(amt))
        return error_result(title=f"❌ {action_label}失败",
                            message="缺少 price 或 amt 参数", rule="不得自行编造参数")

    fresh_realtime = _fetch_realtime(token, bot_id, "1,2", agent_id)
    stale_warning = None
    if fresh_realtime.get("status") == "ok":
        age = int(time.time()) - fresh_realtime.get("timestamp", 0)
        if age > REALTIME_TTL:
            stale_warning = f"实时数据已过去 {age} 秒，价格可能已变化"

    data = api_post("/Trade/scale_do", {
        "usertoken": token, "app_v": "2.0.0", "bot_id": bot_id,
        "save_type": save_type, "price": price, "amt": amt,
    }, agent_id)
    clear(agent_id or "", "scale", bot_id, save_type, str(price), str(amt))
    ok_msg, msg = check_auth(data)
    if not ok_msg:
        return error_result(title=f"❌ {action_label}失败", message=msg, rule="不得自行重试")
    if data.get("status") != 1:
        return error_result(title=f"❌ {action_label}失败",
                            message=data.get("msg", "未知错误"), rule="不得自行重试")

    result_lines = [f"机器人: {bot_id}", f"价格: {price}", f"金额: {amt}"]
    if stale_warning:
        result_lines.append(stale_warning)
    return ok_result(
        title=f"✅ {action_label}成功",
        detail_lines=result_lines,
        bot_id=bot_id, action=action_label,
        stale_warning=stale_warning,
    )