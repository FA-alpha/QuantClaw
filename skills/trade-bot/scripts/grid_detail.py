#!/usr/bin/env python3
"""查询周期挂单明细 — /Trade/grid_lists"""
from typing import Optional

from api_client import api_post, check_auth

TYPE_LABEL = {"BUY": "买入", "SELL": "卖出"}
STATUS_LABEL = {"filled": "已成交", "active": "等待成交"}


def run(
    token: str,
    bot_id: str,
    grid_id: str,
    agent_id: Optional[str] = None,
) -> dict:
    data = api_post(
        "/Trade/grid_lists",
        {"usertoken": token, "app_v": "2.0.0", "bot_id": bot_id, "grid_id": grid_id},
        agent_id,
    )
    ok, msg = check_auth(data)
    if not ok:
        return {"status": "error", "message": msg}
    if data.get("status") != 1:
        return {"status": "error", "message": data.get("msg", data.get("info", "未知错误"))}

    raw = data.get("info", [])
    orders = []
    for item in (raw if isinstance(raw, list) else []):
        t = str(item.get("type", ""))
        s = str(item.get("status", ""))
        orders.append({
            "id": item.get("id"),
            "order_id": item.get("order_id"),
            "coin": item.get("coin"),
            "type": t,
            "type_label": TYPE_LABEL.get(t, t),
            "title": item.get("title"),
            "status": s,
            "status_label": STATUS_LABEL.get(s, s),
            "price": item.get("price"),
            "revenue": item.get("revenue"),
            "quantify": item.get("quantify"),
            "fee": item.get("fee"),
            "trade_time": item.get("trade_time"),
        })

    return {
        "status": "ok",
        "grid_id": grid_id,
        "total": len(orders),
        "orders": orders,
        "field_help": {
            "id": "记录ID",
            "order_id": "订单ID",
            "coin": "币种",
            "type": "类型（BUY-买入 SELL-卖出）",
            "title": "标题",
            "status": "状态（filled-已成交 active-等待成交）",
            "price": "成交/委托价格",
            "revenue": "成交金额",
            "quantify": "数量",
            "fee": "手续费",
            "trade_time": "成交/委托时间",
        },
    }
