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


# ── 参数标签映射（中文可读名） ──
PARAM_LABELS = {
    "coin": "币种",
    "multiple_num": "杠杆倍数",
    "max_grid_size": "最大网格数",
    "grid_type": "网格类型",
    "grid_percentage": "网格间距",
    "direction": "方向",
    "initial_capital": "初始资金",
    "fee_rate": "手续费率",
    "is_add_amt": "自动加仓",
    "price_high": "价格上限",
    "price_low": "价格下限",
    "enable_grid_shift": "移动网格",
    "enable_start_opened": "开盘立即启动",
    "enable_check_period": "周期检查",
    "enable_stop_loss": "止损",
    "enable_take_profit": "止盈",
    "profit_allocation_margin_ratio": "利润分配保证金比例",
    "full_reinvestment_threshold": "完全再投资阈值",
    "margin_reserve_ratio": "保证金预留比例",
    "margin_mode": "保证金模式",
    "basic_unit": "计价单位",
}


def diff_changes(current_rule: dict, proposed: dict) -> dict:
    """
    对比当前策略参数和用户提议的修改，生成变更明细。

    Args:
        current_rule: 当前策略参数
        proposed: 用户想修改的字段 {key: new_value}

    Returns:
        {
            "changed": [{key, old, new, label}, ...],
            "unchanged": [{key, value, label}, ...],
            "unknown": [key, ...],
        }
    """
    changed = []
    unchanged = []
    unknown = []

    for key, new_val in proposed.items():
        if key not in current_rule:
            unknown.append(key)
            continue

        old_val = current_rule[key]
        label = PARAM_LABELS.get(key, key)

        if _normalize_value(old_val) != _normalize_value(new_val):
            changed.append({
                "key": key,
                "label": label,
                "old": old_val,
                "new": new_val,
            })
        else:
            unchanged.append({
                "key": key,
                "label": label,
                "value": old_val,
            })

    return {
        "changed": changed,
        "unchanged": unchanged,
        "unknown": unknown,
    }


def _normalize_value(v) -> str:
    """统一值类型做比较"""
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def do_edit(
    token: str,
    bot_id: str,
    strategy_type: str,
    new_rule: dict,
    update_type: int = 1,
    agent_id: Optional[str] = None,
) -> dict:
    """
    执行策略编辑 — 调用 /Trade/strategy_update_do

    Args:
        token: 用户 token
        bot_id: 机器人 ID
        strategy_type: 策略类型
        new_rule: 完整的 strategy_rule（合并修改后）
        update_type: 1=永久, 2=仅当前周期
        agent_id: Agent ID
    """
    url_params = {
        "usertoken": token,
        "app_v": "2.0.0",
        "bot_id": bot_id,
        "update_type": update_type,
        "strategy_type": strategy_type,
        "rule": json.dumps(new_rule, ensure_ascii=False),
    }

    data = api_post("/Trade/strategy_update_do", url_params, agent_id)
    ok, msg = check_auth(data)
    if not ok:
        return {"status": "error", "message": msg}

    if not check_status(data):
        return {"status": "error", "message": data.get("msg", data.get("info", "未知错误")), "raw": data}

    return {"status": "ok", "data": data}


def run_diff(
    token: str,
    bot_id: str,
    proposed: dict,
    agent_id: Optional[str] = None,
) -> dict:
    """
    差异对比 — 第②步：用户说"把杠杆改成3x"时调用。

    对比当前参数和提议修改，展示变更明细，不执行。
    """
    info = load_cached_detail(bot_id)
    if info is None:
        result = fetch_info(token, bot_id, agent_id)
        if not result["ok"]:
            return {"status": "error", "message": result["error"]}
        info = result["info"]

    check = check_editable(info)
    if not check["editable"]:
        return {
            "status": "error",
            "message": check["reason"],
            "editable_check": check,
        }

    current_rule = get_strategy_rule_for_edit(info)
    diff = diff_changes(current_rule, proposed)

    merged = dict(current_rule)
    for item in diff["changed"]:
        merged[item["key"]] = item["new"]

    return {
        "status": "diff",
        "bot_id": bot_id,
        "name": info.get("name", ""),
        "strategy_type": check["strategy_type"],
        "strategy_type_label": _strategy_type_label(check["strategy_type"]),
        "diff": diff,
        "merged_rule": merged,
    }


def run_execute(
    token: str,
    bot_id: str,
    merged_rule: dict,
    update_type: int = 1,
    agent_id: Optional[str] = None,
) -> dict:
    """
    执行编辑 — 第③步：用户二次确认后调用。
    """
    info = load_cached_detail(bot_id)
    if info is None:
        result = fetch_info(token, bot_id, agent_id)
        if not result["ok"]:
            return {"status": "error", "message": result["error"]}
        info = result["info"]

    strategy_type = str(info.get("strategy_type", ""))

    return do_edit(
        token=token,
        bot_id=bot_id,
        strategy_type=strategy_type,
        new_rule=merged_rule,
        update_type=update_type,
        agent_id=agent_id,
    )