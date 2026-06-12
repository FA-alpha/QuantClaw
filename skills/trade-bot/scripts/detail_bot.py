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


def _fetch_grid_pending(token: str, bot_id: str, agent_id: str) -> Optional[dict]:
    """strategy_type=7 时通过 /Trade/grid_strategy_pending_list 获取网格挂单"""
    data = api_post(
        "/Trade/grid_strategy_pending_list",
        {"usertoken": token, "bot_id": bot_id},
        agent_id,
    )
    ok, msg = check_auth(data)
    if not ok:
        return None
    if data.get("status") != 1:
        return None
    info = data.get("info", {})
    if not isinstance(info, dict):
        return None
    result: dict = {}
    for key in ("long_buy_list", "long_sell_list", "short_buy_list", "short_sell_list"):
        lst = info.get(key, [])
        if isinstance(lst, list) and lst:
            result[key] = lst
    return result or None


def run(
    token: str,
    bot_id: str,
    agent_id: Optional[str] = None,
) -> dict:
    """
    查询机器人详情，返回分组结构，数据驱动。

    API: /Trade/info（strategy_type=7 时额外调 /Trade/cycle_page 和 /Trade/grid_strategy_pending_list）

    返回分组（有数据才出现）：
      basic    — 基本信息（名称/状态/运行时长/交易所）
      strategy — strategy_rule 全量透传
      trade    — trade_info 全量透传
      cycle    — grids_info（当周期）全量透传
      amt      — amt_info 全量透传
      records  — cycle_record（strategy_type=7 走 /Trade/cycle_page）
      chart    — profit_chart
      grid_pending — 网格挂单（strategy_type=7，多/空挂买卖单）
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
    # 从 strategy_rule 提取杠杆和保证金模式
    sr = info.get("strategy_rule", {})
    if sr:
        mn = sr.get("multiple_num")
        if mn is not None and str(mn) != "-1":  # -1 表示无杠杆
            basic["leverage"] = mn
        mm = sr.get("margin_mode")
        if mm:
            basic["margin_mode"] = str(mm)
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
        # 网格挂单 — strategy_type=7 特有
        grid_pending = _fetch_grid_pending(token, bot_id, agent_id or "")
        if grid_pending:
            result["grid_pending"] = grid_pending
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

    # 操作 — 只有 status=1/2 运行中才展示，条件不满足的不出现
    bot_status = str(info.get("status"))
    is_running = bot_status in ("1", "2")
    is_live = bot_status == "1"
    actions = {}
    if is_running:
        # 停止始终可用
        actions["stop"] = True
        # 可编辑策略参数
        if str(info.get("is_edit")) == "1":
            actions["edit"] = True
        # 预约停止/取消预约 — 按 API 按钮状态判断
        if info.get("is_reserve_stop_btn") == 1:
            if str(info.get("reserve_status")) in ("1", "2"):
                actions["cancel_reserve"] = True
            else:
                actions["reserve_stop"] = True
        # 暂停/取消暂停 — 根据 add_pause_status 决定展示哪个
        if info.get("is_add_pause_btn") == 1:
            aps = str(info.get("add_pause_status", "0"))
            if aps == "0":
                actions["pause_add"] = True
            elif aps == "1":
                actions["resume_add"] = True
    if is_live:
        # 保证金/手动加仓 — 仅实盘运行中且有仓位
        grids_info = info.get("grids_info", {})
        has_holdings = False
        if strategy_type == "7":
            long_info = grids_info.get("long", {}) if isinstance(grids_info, dict) else {}
            short_info = grids_info.get("short", {}) if isinstance(grids_info, dict) else {}
            long_h = float(long_info.get("holdings", 0) or 0)
            short_h = float(short_info.get("holdings", 0) or 0)
            has_holdings = long_h > 0 or short_h > 0
        else:
            h = grids_info.get("holdings", 0) if isinstance(grids_info, dict) else 0
            has_holdings = float(h or 0) > 0
        if info.get("is_margin_btn") == 1 and has_holdings:
            actions["margin"] = True
        if info.get("is_manual_btn") == 1 and has_holdings:
            actions["manual"] = True
    if actions:
        result["actions"] = actions

    # ── 帮助信息 ──
    result["section_help"] = {
        "basic": "基本信息",
        "strategy": "策略参数",
        "trade": "交易统计",
        "cycle": "当周期",
        "amt": "金额信息",
        "records": "交易记录",
        "chart": "净值曲线",
        "grid_pending": "网格挂单",
        "fund_fee": "累计资金费率",
        "actions": "可执行操作",
    }
    result["field_help"] = {
        # basic
        "name": "名称", "exchange_name": "交易所", "strategy_id": "策略ID",
        "strategy_type": "策略类型", "amt_type": "交易品种", "unit": "计价单位",
        "run_time": "运行时长", "status": "状态", "reserve_status": "预约状态",
        "add_pause_status": "加仓暂停", "is_edit": "是否可编辑",
        "status_label": "状态", "amt_type_label": "品种", "run_time_label": "运行时长",
        "leverage": "杠杆倍数", "margin_mode": "保证金模式",
        # cycle (grids_info)
        "avg_price": "均价", "total_cost": "总成本", "holdings": "持仓数量",
        "float_amt": "浮动盈亏", "max_grid_size": "最大网格数", "grids_used": "已用网格",
        "liquidation_price": "清算价格", "real_leverage": "实际杠杆",
        "maintenance_margin": "维持保证金", "now_price": "当前价格",
        "grids_token": "网格标记", "max_cycle_profit": "最大周期利润",
        # records
        "parent_id": "父记录ID", "bgn_time": "开始时间", "trade_time": "交易时间",
        "sell_price": "卖出价", "profit_amt": "盈利金额",
        "auto_grids_used": "自动加仓", "hand_grids_used": "手动加仓",
        "address": "补充信息",
        # trade
        "coin": "币种", "profit_rate": "收益率", "win_rate": "胜率",
        "float_profit": "浮盈", "close_profit": "已平盈亏",
        # chart
        "max": "最高", "min": "最低", "points": "数据点",
        # fund_fee
        "fund_fee": "累计资金费率",
        # actions
        "stop": "停止", "edit": "编辑策略", "reserve_stop": "预约停止",
        "cancel_reserve": "取消预约", "pause_add": "暂停加仓", "resume_add": "恢复加仓",
        "margin": "调整保证金", "manual": "手动加仓",
        # grid_pending (strategy_type=7)
        "long_buy_list": "多头挂买单", "long_sell_list": "多头挂卖单",
        "short_buy_list": "空头挂买单", "short_sell_list": "空头挂卖单",
        "price": "挂单价格", "diff": "距现价", "diff_abs_percent": "价差百分比",
    }

    return result
