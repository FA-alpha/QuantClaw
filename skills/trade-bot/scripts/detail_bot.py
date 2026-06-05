#!/usr/bin/env python3
"""查询交易机器人详情 — /Trade/info，按分组透传，数据驱动"""
import json
import os
from typing import Optional

from api_client import api_post, check_auth

DETAIL_CACHE_DIR = "/tmp/quantclaw/bot_details"

STATUS_LABEL = {
    "0": "未运行", "1": "实盘运行中", "2": "模拟运行",
    "3": "已停止", "4": "模拟已停止",
}
AMT_TYPE_LABEL = {"1": "现货", "2": "合约"}


def _fmt_runtime(seconds) -> str:
    if not seconds:
        return ""
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    mins = rem // 60
    parts = []
    if days:
        parts.append(f"{days}天")
    if hours:
        parts.append(f"{hours}小时")
    if mins or not parts:
        parts.append(f"{mins}分钟")
    return "".join(parts)


def _fetch_cycle_page(token: str, bot_id: str, agent_id: str, page: int = 1, limit: int = 50) -> Optional[list]:
    """strategy_type=7 时通过 /Trade/cycle_page 获取交易记录"""
    data = api_post(
        "/Trade/cycle_page",
        {"usertoken": token, "app_v": "2.0.0", "bot_id": bot_id, "page": page, "limit": limit},
        agent_id,
    )
    ok, msg = check_auth(data)
    if not ok:
        return None
    if data.get("status") != 1:
        return None
    info = data.get("info", {})
    records = info.get("cycle_record", [])
    if not isinstance(records, list):
        return None
    # 附加分页信息
    url = data.get("url", {})
    return {
        "list": records,
        "total": int(url.get("all_count", len(records))),
        "page": page,
        "limit": limit,
    }


def run(
    token: str,
    bot_id: str,
    agent_id: Optional[str] = None,
) -> dict:
    """
    查询机器人详情，返回分组结构，数据驱动。

    API: /Trade/info（strategy_type=7 时额外调 /Trade/cycle_page）

    返回分组（有数据才出现）：
      basic    — 基本信息（名称/状态/运行时长/交易所）
      strategy — strategy_rule 全量透传
      trade    — trade_info 全量透传
      cycle    — grids_info（当周期）全量透传
      amt      — amt_info 全量透传
      records  — cycle_record（strategy_type=7 走 /Trade/cycle_page）
      chart    — profit_chart
      fund_fee — 累计资金费率
      buttons  — 可操作按钮
    """
    data = api_post(
        "/Trade/info",
        {"usertoken": token, "app_v": "2.0.0", "bot_id": bot_id},
        agent_id,
    )
    ok, msg = check_auth(data)
    if not ok:
        return {"status": "error", "message": msg}
    if data.get("status") != 1:
        return {"status": "error", "message": data.get("msg", data.get("info", "未知错误"))}

    info = data.get("info", {})
    strategy_type = str(info.get("strategy_type", ""))

    # ── 缓存原始 info ──
    os.makedirs(DETAIL_CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(DETAIL_CACHE_DIR, f"{bot_id}.json")
    try:
        with open(cache_path, "w") as f:
            json.dump(info, f, ensure_ascii=False, default=str)
    except Exception:
        pass

    # ── 分组构建（有数据才出现） ──
    result: dict = {"status": "ok"}

    # 基本信息
    basic: dict[str, object] = {}
    for k in ("name", "exchange_name", "strategy_id", "strategy_type",
              "amt_type", "unit", "run_time", "status", "reserve_status",
              "add_pause_status", "is_edit"):
        v = info.get(k)
        if v is not None:
            basic[k] = v
    basic["status_label"] = STATUS_LABEL.get(str(info.get("status")), "")
    basic["amt_type_label"] = AMT_TYPE_LABEL.get(str(info.get("amt_type")), "")
    basic["run_time_label"] = _fmt_runtime(info.get("run_time"))
    result["basic"] = basic

    # 策略参数 — 按 schema 分组解析（已知类型代码直出，未知调 API）
    strategy_rule = info.get("strategy_rule")
    if strategy_rule and isinstance(strategy_rule, dict) and strategy_rule:
        from strategy_schema import analyze
        sr_data = dict(strategy_rule)
        sr_data["strategy_type"] = strategy_type
        result["strategy"] = analyze(sr_data, token=token, agent_id=agent_id or "")

    # 交易统计 — 全量透传
    trade_info = info.get("trade_info")
    if trade_info and isinstance(trade_info, dict) and trade_info:
        result["trade"] = dict(trade_info)

    # 当周期 — grids_info
    grids_info = info.get("grids_info")
    if grids_info and isinstance(grids_info, dict) and grids_info:
        result["cycle"] = dict(grids_info)

    # 金额
    amt_info = info.get("amt_info")
    if amt_info and isinstance(amt_info, dict) and amt_info:
        result["amt"] = dict(amt_info)

    # 交易记录 — strategy_type=7 走 /Trade/cycle_page
    if strategy_type == "7":
        records = _fetch_cycle_page(token, bot_id, agent_id)
        if records:
            result["records"] = records
    else:
        cycle_record = info.get("cycle_record")
        if cycle_record and isinstance(cycle_record, list) and cycle_record:
            result["records"] = {"list": cycle_record, "total": len(cycle_record)}

    # 净值曲线
    profit_chart = info.get("profit_chart")
    if profit_chart and isinstance(profit_chart, dict):
        chart: dict = {}
        if "max" in profit_chart:
            chart["max"] = profit_chart["max"]
        if "min" in profit_chart:
            chart["min"] = profit_chart["min"]
        if "lists" in profit_chart:
            chart["points"] = profit_chart["lists"]
        if chart:
            result["chart"] = chart

    # 资金费率
    fund_fee = info.get("fund_fee")
    if fund_fee is not None and fund_fee != "":
        result["fund_fee"] = fund_fee

    # 操作按钮
    buttons = {}
    for key, label in (("is_margin_btn", "margin"), ("is_manual_btn", "manual"),
                       ("is_reserve_stop_btn", "reserve_stop"), ("is_add_pause_btn", "add_pause")):
        if info.get(key) is not None:
            buttons[label] = info[key] == 1
    if buttons:
        result["buttons"] = buttons

    return result
