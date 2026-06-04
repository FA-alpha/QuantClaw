#!/usr/bin/env python3
"""查询交易机器人详情 — /Trade/info"""
import json
import os
from typing import Optional

from api_client import api_post, check_auth

# 详情缓存目录（临时数据，存 /tmp 下）
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
    if days: parts.append(f"{days}天")
    if hours: parts.append(f"{hours}小时")
    if mins or not parts: parts.append(f"{mins}分钟")
    return "".join(parts)


def run(
    token: str,
    bot_id: str,
    agent_id: Optional[str] = None,
) -> dict:
    """
    查询机器人详情。

    API: /Trade/info

    Returns:
        {"status": "ok"|"error", "detail": {...}}
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
        return {"status": "error", "message": data.get("msg", data.get("info", "未知错误")), "raw": data}

    info = data.get("info", {})

    # 策略规则
    strategy_rule = info.get("strategy_rule", {})
    sr = {
        "coin": strategy_rule.get("coin"),
        "initial_capital": strategy_rule.get("initial_capital"),
        "leverage": strategy_rule.get("multiple_num"),
        "max_grid_size": strategy_rule.get("max_grid_size"),
        "grid_type": strategy_rule.get("grid_type"),
        "direction": strategy_rule.get("direction"),
        "fee_rate": strategy_rule.get("fee_rate"),
        "is_add_amt": strategy_rule.get("is_add_amt"),
        "price_high": strategy_rule.get("price_high"),
        "price_low": strategy_rule.get("price_low"),
        "enable_grid_shift": strategy_rule.get("enable_grid_shift"),
        "enable_start_opened": strategy_rule.get("enable_start_opened"),
        "enable_check_period": strategy_rule.get("enable_check_period"),
        "enable_stop_loss": strategy_rule.get("enable_stop_loss"),
        "enable_take_profit": strategy_rule.get("enable_take_profit"),
    }

    # 交易数据
    trade_info = info.get("trade_info", {})
    ti = {
        "coin": trade_info.get("coin"),
        "create_time": trade_info.get("create_time"),
        "initial_capital": trade_info.get("initial_capital"),
        "grid_num": trade_info.get("grid_num"),
        "grid_avg_time": trade_info.get("grid_avg_time"),
        "add_margin": trade_info.get("add_margin"),
        "take_profit": trade_info.get("take_profit"),
        "fund_radio": trade_info.get("fund_radio"),
        "float_amt": trade_info.get("float_amt"),
        "total_amt": trade_info.get("total_amt"),
        "float_profit": trade_info.get("float_profit"),
        "win_rate": trade_info.get("win_rate"),
        "trade_token": trade_info.get("trade_token", ""),
    }

    # 网格
    grids_info = info.get("grids_info", {})

    # 盈亏图表
    profit_chart = info.get("profit_chart", {})

    # 资金费率累计
    fund_fee = info.get("fund_fee")

    # 保存原始 info 缓存
    os.makedirs(DETAIL_CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(DETAIL_CACHE_DIR, f"{bot_id}.json")
    try:
        with open(cache_path, "w") as f:
            json.dump(info, f, ensure_ascii=False, default=str)
    except Exception:
        pass  # 缓存写入失败不影响主流程

    detail = {
        "bot_id": bot_id,
        "name": info.get("name"),
        "strategy_id": info.get("strategy_id"),
        "strategy_type": info.get("strategy_type"),
        "exchange_name": info.get("exchange_name"),
        "status": info.get("status"),
        "status_label": STATUS_LABEL.get(str(info.get("status")), ""),
        "amt_type": info.get("amt_type"),
        "amt_type_label": AMT_TYPE_LABEL.get(str(info.get("amt_type")), ""),
        "unit": info.get("unit"),
        "run_time": info.get("run_time"),
        "run_time_label": _fmt_runtime(info.get("run_time")),
        "reserve_status": info.get("reserve_status"),
        # 权限 / 按钮
        # 编辑权限（is_edit 字段，0/1）
        "is_edit": info.get("is_edit"),
        "buttons": {
            "margin": info.get("is_margin_btn") == 1,
            "manual": info.get("is_manual_btn") == 1,
            "reserve_stop": info.get("is_reserve_stop_btn") == 1,
            "add_pause": info.get("is_add_pause_btn") == 1,
        },
        "add_pause_status": str(info.get("add_pause_status", "0")),
        "strategy_rule": sr,
        "trade_info": ti,
        "grids": {
            "long": grids_info.get("long"),
            "short": grids_info.get("short"),
            "grids_token": grids_info.get("grids_token"),
        },
        "profit_chart": {
            "max": profit_chart.get("max"),
            "min": profit_chart.get("min"),
            "points": profit_chart.get("lists"),
        },
        "fund_fee_total": fund_fee,
    }

    return {"status": "ok", "detail": detail}
