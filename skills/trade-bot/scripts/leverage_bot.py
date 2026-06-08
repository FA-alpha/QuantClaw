#!/usr/bin/env python3
"""查询运行中机器人的杠杆率统计"""
from typing import Optional

from api_client import api_post, check_auth
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))

STATUS_MAP = {"running": "1", "sim": "2", "stopped": "3", "deleted": "-1"}
AMT_TYPE_MAP = {"spot": "1", "futures": "2"}


def _build_search_status(status: str) -> Optional[str]:
    if not status or status == "all":
        return None
    return ",".join(STATUS_MAP[s] for s in status.split(",") if s in STATUS_MAP)


def run(
    token: str,
    status: str = "running",
    exchange_ids: Optional[str] = None,
    amt_type: Optional[str] = None,
    strategy_type: Optional[int] = None,
    account_id: Optional[int] = None,
    direction: Optional[str] = None,
    search: Optional[str] = None,
    coin: Optional[str] = None,
    agent_id: Optional[str] = None,
) -> dict:
    """查询杠杆率统计（仅运行中的机器人）"""
    params = {
        "app_v": "2.0.0",
        "lang": 1,
    }

    # 筛选参数
    s_status = _build_search_status(status)
    if s_status is not None:
        params["search_status"] = s_status
    if exchange_ids:
        params["search_exchange"] = exchange_ids
    if amt_type and amt_type != "all":
        params["search_amt_type"] = AMT_TYPE_MAP.get(amt_type)
    if strategy_type is not None:
        params["strategy_type"] = strategy_type
    if account_id is not None:
        params["account_id"] = account_id
    if direction and direction != "all":
        params["search_direction"] = direction

    # search_val
    parts = []
    if search:
        parts.append(search)
    if coin:
        parts.append(coin)
    if parts:
        params["search_val"] = " ".join(parts)

    params["usertoken"] = token

    data = api_post("/TradeStat/leverage_ratio", params, agent_id)
    ok, msg = check_auth(data)
    if not ok:
        return {"status": "error", "message": msg}

    if data.get("status") != 1:
        return {"status": "error", "message": data.get("msg", "未知错误")}

    info = data.get("info", {})
    amt_info = info.get("amt_info", {}) or {}
    leverage_info = info.get("leverage_info", {}) or {}
    usdt_assets_raw = info.get("usdt_assets") or []
    usd_assets_raw = info.get("usd_assets") or []
    # symbol_stat 可能为 null
    symbol_stat_raw = leverage_info.get("symbol_stat") or []

    def _filter_assets(raw):
        """过滤掉 symbol 为空的无效条目"""
        if not raw:
            return []
        return [
            {
                "symbol": a.get("symbol"),
                "nominal_invest_total": a.get("nominal_invest_total"),
                "current_position": a.get("current_position"),
                "real_leverage": a.get("real_leverage"),
                "direction": a.get("direction"),
            }
            for a in raw
            if a.get("symbol")
        ]

    return {
        "status": "ok",
        "updated_at": datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S"),
        "section_help": {
            "total_assets": "总资产",
            "leverage": "杠杆率概览",
            "usdt_assets": "U本位资产标的",
            "usd_assets": "币本位资产标的",
            "symbol_stat": "币种统计",
        },
        "field_help": {
            "total_amt": "总金额",
            "nominal_invest_total": "名义总投资",
            "nominal_invest_total_exposure": "名义总投资（long-多 short-空）",
            "actual_invest_total": "实际总投资",
            "used_margin": "已用保证金",
            "used_margin_pct": "已用保证金占比",
            "available_margin": "可用保证金",
            "available_margin_pct": "可用保证金占比",
            "nominal_leverage": "名义杠杆",
            "real_leverage": "实际杠杆率",
            "real_leverage_exposure": "实际杠杆率方向（long-多 short-空）",
            "dir_exposure": "方向暴露（long-多 short-空）",
            "scale_exposure": "暴露比例",
            "symbol": "币种",
            "current_position": "当前总仓位",
            "direction": "方向（long-多 short-空）",
            "coin": "币种",
            "nominal_total_cash": "名义总投资",
            "initial_capital": "初始本金",
            "net_value": "当前净值",
            "overtake_amt": "超额金额",
        },
        "total_assets": {
            "total_amt": amt_info.get("total_amt"),
        },
        "leverage": {
            "nominal_invest_total": leverage_info.get("nominal_invest_total"),
            "nominal_invest_total_exposure": leverage_info.get("nominal_invest_total_exposure"),
            "actual_invest_total": leverage_info.get("actual_invest_total"),
            "used_margin": leverage_info.get("used_margin"),
            "used_margin_pct": leverage_info.get("used_margin_pct"),
            "available_margin": leverage_info.get("available_margin"),
            "available_margin_pct": leverage_info.get("available_margin_pct"),
            "nominal_leverage": leverage_info.get("nominal_leverage"),
            "real_leverage": leverage_info.get("real_leverage"),
            "real_leverage_exposure": leverage_info.get("real_leverage_exposure"),
            "dir_exposure": leverage_info.get("dir_exposure"),
            "scale_exposure": leverage_info.get("scale_exposure"),
        },
        "usdt_assets": _filter_assets(usdt_assets_raw),
        "usd_assets": _filter_assets(usd_assets_raw),
        "symbol_stat": [
            {
                "coin": s.get("coin"),
                "nominal_total_cash": s.get("nominal_total_cash"),
                "actual_invest_total": s.get("actual_invest_total"),
                "initial_capital": s.get("initial_capital"),
                "overtake_amt": s.get("overtake_amt"),
                "net_value": s.get("net_value"),
            }
            for s in symbol_stat_raw
        ] if symbol_stat_raw else [],
        "filters": {
            "status": status,
            "exchange_ids": exchange_ids,
            "amt_type": amt_type or "all",
            "strategy_type": strategy_type or "all",
            "account_id": account_id or "all",
            "direction": direction or "all",
            "search": search,
            "coin": coin,
        },
    }