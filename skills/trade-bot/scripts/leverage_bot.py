#!/usr/bin/env python3
"""查询运行中机器人的杠杆率统计"""
import requests
from typing import Optional

from qc_log import log_http_request, log_error

BASE_URL = "https://www.fourieralpha.com/Mobile"

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

    url = f"{BASE_URL}/TradeStat/leverage_ratio"

    try:
        resp = requests.post(url, data=params, timeout=30)
        data = resp.json()
        log_http_request(url, params, response=data, agent_id=agent_id)

        if data.get("status") != 1:
            msg = data.get("msg", "未知错误")
            return {"status": "error", "message": msg}

        info = data.get("info", {})
        amt_info = info.get("amt_info", {})
        leverage_info = info.get("leverage_info", {})
        usdt_assets = info.get("usdt_assets", [])

        return {
            "status": "ok",
            "total_amt": amt_info.get("total_amt"),
            "leverage": {
                "actual_invest_total": leverage_info.get("actual_invest_total"),
                "nominal_invest_total": leverage_info.get("nominal_invest_total"),
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
            "assets": [
                {
                    "symbol": a.get("symbol"),
                    "nominal_invest_total": a.get("nominal_invest_total"),
                    "current_position": a.get("current_position"),
                }
                for a in usdt_assets
            ] if usdt_assets else [],
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

    except requests.RequestException as e:
        log_error(str(e), exception=e, context={"url": url}, agent_id=agent_id)
        return {"status": "error", "message": f"网络请求异常: {str(e)}"}
    except Exception as e:
        log_error(str(e), exception=e, context={"url": url}, agent_id=agent_id)
        return {"status": "error", "message": f"脚本异常: {str(e)}"}