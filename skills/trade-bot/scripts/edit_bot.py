#!/usr/bin/env python3
"""
策略编辑（修改交易机器人策略参数）
API: /Trade/strategy_update_do

流程：
  1. 先从缓存的详情文件中读取 info（由 detail_bot.py 写入）
  2. 如果缓存不存在，再请求 /Trade/info 获取
  3. 检查状态（只有 status=1,2 运行中才能编辑）
  4. 检查 is_edit 字段
  5. 根据 strategy_type 区分编辑方式
"""
import json
import os
from typing import Optional

from api_client import api_post, check_auth, check_status


# ── 详情缓存目录（与 detail_bot.py 保持一致） ──
DETAIL_CACHE_DIR = os.path.expanduser("~/.quantclaw/cache/bot_details")

# ── 可编辑的状态（只有运行中 / 模拟运行可编辑） ──
EDITABLE_STATUSES = {"1", "2"}

# ── strategy_type=2 特有的参数键 ──
# 策略类型 2 的 strategy_rule 结构与其他类型不同
ST2_RULE_KEYS = {
    # 基础参数
    "coin", "multiple_num", "initial_capital",
    "basic_unit", "margin_mode",
    # 策略类型2 特有
    "direction",  # 可能不支持方向
    # 通用但 strategy_type=2 可能有不同含义
    "enable_grid_shift",
    "max_grid_size", "grid_type",
    "is_add_amt", "fee_rate",
    "enable_start_opened", "enable_check_period",
    "enable_stop_loss", "enable_take_profit",
    "price_high", "price_low",
    "profit_allocation_margin_ratio",
    "full_reinvestment_threshold",
    "margin_reserve_ratio",
}


def load_cached_detail(bot_id: str) -> Optional[dict]:
    """从缓存的详情文件读取 info，返回 None 表示缓存不存在"""
    cache_path = os.path.join(DETAIL_CACHE_DIR, f"{bot_id}.json")
    if not os.path.exists(cache_path):
        return None
    try:
        with open(cache_path) as f:
            return json.load(f)
    except Exception:
        return None


def fetch_info(token: str, bot_id: str, agent_id: Optional[str] = None) -> dict:
    """
    调用 /Trade/info 获取机器人详情，返回 {"ok": bool, "info": dict|None, "error": str}
    """
    data = api_post(
        "/Trade/info",
        {"usertoken": token, "app_v": "2.0.0", "bot_id": bot_id},
        agent_id,
    )
    ok, msg = check_auth(data)
    if not ok:
        return {"ok": False, "error": msg}

    if not check_status(data):
        return {"ok": False, "error": data.get("msg", data.get("info", "未知错误"))}

    return {"ok": True, "info": data.get("info", {})}


def check_editable(info: dict) -> dict:
    """
    检查机器人是否可编辑。

    Returns:
        {
            "editable": bool,
            "reason": str,           # 不可编辑的原因
            "is_edit": int,          # 接口返回的 is_edit
            "status": str,           # 机器人状态
            "strategy_type": str,    # 策略类型
        }
    """
    status = str(info.get("status", ""))
    is_edit = info.get("is_edit")
    strategy_type = str(info.get("strategy_type", ""))

    if status not in EDITABLE_STATUSES:
        return {
            "editable": False,
            "reason": f"机器人状态为 {status}（{'运行中' if status == '1' else '已停止'}），只有运行中的机器人才能编辑",
            "is_edit": is_edit,
            "status": status,
            "strategy_type": strategy_type,
        }

    if is_edit != 1:
        return {
            "editable": False,
            "reason": f"is_edit={is_edit}，当前不支持编辑",
            "is_edit": is_edit,
            "status": status,
            "strategy_type": strategy_type,
        }

    return {
        "editable": True,
        "reason": "",
        "is_edit": is_edit,
        "status": status,
        "strategy_type": strategy_type,
    }


def get_strategy_rule_for_edit(info: dict) -> dict:
    """
    从 info 中提取用于编辑的 strategy_rule。

    strategy_type=2 与其他类型的处理不同：
    - strategy_type=2: 仅返回策略2支持的字段
    - 其他类型: 返回完整的 strategy_rule（暂不做裁剪，后续细化）
    """
    strategy_type = str(info.get("strategy_type", ""))
    strategy_rule = info.get("strategy_rule", {})

    if strategy_type == "2":
        # 策略类型2：仅保留支持的键
        return {k: v for k, v in strategy_rule.items() if k in ST2_RULE_KEYS}

    # 其他类型：返回完整 strategy_rule
    return dict(strategy_rule)


def run(
    token: str,
    bot_id: str,
    agent_id: Optional[str] = None,
) -> dict:
    """
    预览编辑（基础方法）。

    1. 先尝试读缓存详情，没有则请求 API
    2. 检查 is_edit + status
    3. 返回可编辑参数预览

    Returns:
        {
            "status": "preview" | "error",
            "bot_id": str,
            "editable_check": {...},
            "strategy_rule": {...},    # 当前策略参数（按 strategy_type 裁剪后）
            "raw_rule": {...},         # 原始完整 strategy_rule（供参考）
        }
    """
    # ── 第1步：获取 info ──
    info = load_cached_detail(bot_id)

    if info is None:
        # 缓存不存在，请求 API
        result = fetch_info(token, bot_id, agent_id)
        if not result["ok"]:
            return {"status": "error", "message": result["error"]}
        info = result["info"]

    # ── 第2步：可编辑检查 ──
    check = check_editable(info)

    # ── 第3步：提取策略参数 ──
    raw_rule = info.get("strategy_rule", {})
    editable_rule = get_strategy_rule_for_edit(info)
    strategy_type = str(info.get("strategy_type", ""))

    return {
        "status": "preview",
        "bot_id": bot_id,
        "name": info.get("name", ""),
        "editable_check": check,
        "strategy_type": strategy_type,
        "strategy_type_label": _strategy_type_label(strategy_type),
        # 当前可编辑参数
        "strategy_rule": editable_rule,
        # 原始完整参数（供参考对比）
        "raw_rule": raw_rule,
    }


def _strategy_type_label(st: str) -> str:
    """策略类型转可读标签"""
    labels = {
        "1": "风霆",
        "2": "策略类型2",
        "3": "鲲鹏v1",
        "7": "网格",
        "11": "趋势",
    }
    return labels.get(st, f"未知({st})")