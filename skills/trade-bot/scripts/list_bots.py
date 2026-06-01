#!/usr/bin/env python3
"""查询交易机器人列表"""
import sys
import os
import requests
from typing import Optional

# 日志模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scripts', 'logging'))
from api_logger import log_http_request, log_error

BASE_URL = "https://www.fourieralpha.com/Mobile"

# 筛选映射表
STATUS_MAP = {"running": "1", "sim": "2", "stopped": "3", "deleted": "-1"}
AMT_TYPE_MAP = {"spot": "1", "futures": "2"}
SORT_MAP = {
    "latest": 1,
    "profit": 2,
    "runtime": 3,
    "capital": 4,
    "nav": 5,
    "stop-time": 6,
}
STATUS_LABEL = {
    "0": "未运行",
    "1": "实盘运行中",
    "2": "模拟运行",
    "3": "已停止",
    "4": "模拟已停止",
}
AMT_TYPE_LABEL = {"1": "现货", "2": "合约"}


def _build_search_status(status: str) -> Optional[str]:
    """状态名 → API 状态值；all/空 → 不传"""
    if not status or status == "all":
        return None
    return ",".join(STATUS_MAP[s] for s in status.split(",") if s in STATUS_MAP)


def _build_search_val(search: Optional[str], coin: Optional[str]) -> Optional[str]:
    """合并名称搜索和币种搜索"""
    if search and coin:
        return f"{search} {coin}"
    return search or coin


def _fmt_runtime(seconds) -> str:
    """秒 → 人类可读"""
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
    status: str = "running",
    exchange_ids: Optional[str] = None,
    amt_type: Optional[str] = None,
    strategy_type: Optional[int] = None,
    account_id: Optional[int] = None,
    direction: Optional[str] = None,
    search: Optional[str] = None,
    coin: Optional[str] = None,
    sort: str = "latest",
    order: str = "desc",
    page: int = 1,
    limit: int = 10,
    agent_id: Optional[str] = None,
) -> dict:
    """
    查询交易机器人列表。

    Returns:
        {"status": "ok"|"error", "total": int, "page": int,
         "limit": int, "bots": [...], "filters": {...}}
    """
    # 构建 API 参数
    params = {
        "page": page,
        "limit": limit,
        "sort_type": SORT_MAP.get(sort, 1),
        "sort_desc_type": 1 if order == "desc" else 2,
        "app_v": "2.0.0",
        "lang": 1,
    }

    # 筛选参数（None = 不传）
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
    s_val = _build_search_val(search, coin)
    if s_val:
        params["search_val"] = s_val

    # usertoken 独立字段
    params["usertoken"] = token

    url = f"{BASE_URL}/Trade/lists"

    try:
        resp = requests.post(url, data=params, timeout=30)
        data = resp.json()
        log_http_request(url, params, response=data, agent_id=agent_id)

        if data.get("status") != 1:
            msg = data.get("msg", "未知错误")
            return {"status": "error", "message": msg, "raw": data}

        # 提取数据
        bots_raw = data.get("info", [])
        all_count = int(data.get("url", {}).get("all_count", len(bots_raw)))

        # 增强字段
        bots = []
        for b in bots_raw:
            bots.append({
                "id": b.get("id"),
                "name": b.get("name"),
                "account_name": b.get("account_name"),
                "exchange_name": b.get("exchange_name"),
                "amt_type": b.get("amt_type"),
                "amt_type_label": AMT_TYPE_LABEL.get(str(b.get("amt_type")), ""),
                "strategy_name": b.get("strategy_name"),
                "status": b.get("status"),
                "status_label": STATUS_LABEL.get(str(b.get("status")), ""),
                "profit_rate": b.get("profit_rate"),
                "net_value": b.get("net_value"),
                "initial_capital": b.get("initial_capital"),
                "run_time": b.get("run_time"),
                "run_time_label": _fmt_runtime(b.get("run_time")),
                "reserve_status": b.get("reserve_status"),
                "trade_status": b.get("trade_status"),
                "basic_unit": b.get("basic_unit"),
                "create_time": b.get("create_time"),
                "is_info": b.get("is_info"),
            })

        return {
            "status": "ok",
            "total": all_count,
            "page": page,
            "limit": limit,
            "filters": {
                "status": status,
                "exchange_ids": exchange_ids,
                "amt_type": amt_type or "all",
                "strategy_type": strategy_type or "all",
                "account_id": account_id or "all",
                "direction": direction or "all",
                "search": search,
                "coin": coin,
                "sort": sort,
                "order": order,
            },
            "bots": bots,
        }

    except requests.RequestException as e:
        log_error(str(e), exception=e, context={"url": url}, agent_id=agent_id)
        return {"status": "error", "message": f"网络请求异常: {str(e)}"}
    except Exception as e:
        log_error(str(e), exception=e, context={"url": url}, agent_id=agent_id)
        return {"status": "error", "message": f"脚本异常: {str(e)}"}