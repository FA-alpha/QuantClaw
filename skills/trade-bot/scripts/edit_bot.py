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
from agent_display import (
    blocked_result, prompt_result, preview_result,
    ok_result, error_result,
)


# ── 详情缓存目录（临时数据，与 detail_bot.py 保持一致） ──
DETAIL_CACHE_DIR = "/tmp/quantclaw/bot_details"

# ── 可编辑的状态（只有运行中 / 模拟运行可编辑） ──
EDITABLE_STATUSES = {"1", "2"}

# ═══════════════════════════════════════════════════════════════
# 字段 Schema: 定义每个可编辑字段的类型、标签、可选项
# Agent 据此渲染用户友好的编辑界面（开关/数字输入/下拉选择）
# ═══════════════════════════════════════════════════════════════

# ── strategy_type=2 编辑字段定义（基于前端 JS 逻辑） ──
# field_type: "number" | "switch" | "select"
# condition: 条件表达式，如 "amt_type=2" 表示仅合约时生效
# options:   下拉/开关的可选值 {value: label}
# children: 子字段映射 {parent_value: [child_keys]}
ST2_FIELD_SCHEMA = {
    "max_grid_size": {
        "type": "number", "label": "最大加仓次数", "hint": "整数",
    },
    "up_pct": {
        "type": "number", "label": "上涨N%买入/卖出", "hint": "百分比数值",
    },
    "down_pct": {
        "type": "number", "label": "下跌N%买入/卖出", "hint": "百分比数值",
    },
    "fst_capital": {
        "type": "number", "label": "初次下单金额", "hint": "USDT",
    },
    "each_capital": {
        "type": "number", "label": "加仓下单金额", "hint": "USDT",
    },
    "multiple_num": {
        "type": "number", "label": "杠杆倍数", "condition": "amt_type=2",
        "hint": "仅合约",
    },
    "max_loss_pct": {
        "type": "number", "label": "最大止损比例", "hint": "百分比",
    },
    "max_loss_type": {
        "type": "select", "label": "最大止损类型",
        "options": {"1": "市价", "2": "限价"},
    },
    "add_amt_multiples": {
        "type": "number", "label": "加仓金额倍数", "hint": "倍数",
    },
    "add_spread_multiples": {
        "type": "number", "label": "加仓价差倍数", "hint": "倍数",
    },
    "is_add_amt": {
        "type": "switch", "label": "是否复投",
        "options": {"0": "否", "1": "是"},
    },
    # ── RSI 相关（仅 rsi_signal=1 时显示） ──
    "rsi_signal": {
        "type": "switch", "label": "RSI信号",
        "options": {"0": "关闭", "1": "开启"},
        "children": {"1": ["rsi_period", "rsi_time_grain", "rsi_buy_threshold", "rsi_signal_type"]},
    },
    "rsi_period": {
        "type": "number", "label": "RSI周期", "condition": "rsi_signal=1",
        "hint": "如 14",
    },
    "rsi_time_grain": {
        "type": "select", "label": "RSI时间颗粒度", "condition": "rsi_signal=1",
        "options": {
            "1min": "1分钟", "5min": "5分钟", "15min": "15分钟",
            "30min": "30分钟", "1h": "1小时", "4h": "4小时",
            "1d": "1天", "1w": "1周",
        },
    },
    "rsi_buy_threshold": {
        "type": "number", "label": "RSI买点阈值", "condition": "rsi_signal=1",
        "hint": "如 30",
    },
    "rsi_signal_type": {
        "type": "select", "label": "RSI计算方式", "condition": "rsi_signal=1",
        "options": {
            "below": "向下穿过", "above": "向上穿过",
            "low": "低于", "high": "高于",
        },
    },
    # ── 止盈相关 ──
    "take_profit_type": {
        "type": "switch", "label": "移动止盈",
        "options": {"1": "关闭", "3": "开启"},
        "children": {"3": ["stop_profit_multiple", "first_take_profit_ratio"]},
    },
    "stop_profit_multiple": {
        "type": "number", "label": "止盈比例倍数", "condition": "take_profit_type=3",
        "hint": "倍数",
    },
    "first_take_profit_ratio": {
        "type": "number", "label": "止盈仓位比例", "condition": "take_profit_type=3",
        "hint": "%",
    },
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

    - strategy_type=2: 按 ST2_FIELD_SCHEMA 裁剪
    - 其他类型: 返回完整 strategy_rule（暂不做裁剪）
    """
    strategy_type = str(info.get("strategy_type", ""))
    strategy_rule = info.get("strategy_rule", {})

    if strategy_type == "2":
        return {k: strategy_rule.get(k) for k in ST2_FIELD_SCHEMA if k in strategy_rule}

    return dict(strategy_rule)


def fetch_trade_field_info(
    token: str,
    strategy_id: str,
    strategy_type: str,
    strategy_version: str,
    robot_id: str,
    agent_id: Optional[str] = None,
) -> dict:
    """
    获取策略类型 != 2 的可编辑字段定义。

    API: /Strategy/trade_field_info

    Returns:
        {"ok": bool, "info": list|None, "error": str}

    info 结构（数组，按分组）：
        [
          {
            "name": "基础设置",
            "field_lists": [
              {"name":"杠杆倍数","variable":"multiple_num","dvalue":3,
               "type":"input","options":null},
              {"name":"方向","variable":"direction","dvalue":"long",
               "type":"select","options":[{"name":"做多","value":"long"},
                                            {"name":"做空","value":"short"}]},
              ...
            ]
          },
          ...
        ]
        也可能包含 multiples 多维数组字段
    """
    data = api_post(
        "/Strategy/trade_field_info",
        {
            "usertoken": token,
            "app_v": "2.0.0",
            "strategy_id": strategy_id,
            "strategy_type": strategy_type,
            "strategy_version": strategy_version,
            "robot_id": robot_id,
        },
        agent_id,
    )
    ok, msg = check_auth(data)
    if not ok:
        return {"ok": False, "error": msg}

    if not check_status(data):
        return {"ok": False, "error": data.get("msg", data.get("info", "未知错误"))}

    return {"ok": True, "info": data.get("info", [])}


def _api_type_to_field_type(api_type: str) -> str:
    """将 trade_field_info 的 type 映射为统一的 field type"""
    mapping = {
        "input": "number",
        "input_fixed": "fixed",  # 固定值，不能修改
        "select": "select",
        "multiple": "multiple",  # 可添加多组
    }
    return mapping.get(api_type, api_type)


def build_field_list_from_api(trade_fields: list, strategy_rule: dict) -> list:
    """
    将 /Strategy/trade_field_info 返回的数据转为统一的字段列表格式。

    Args:
        trade_fields: API 返回的 info 数组（按分组）
        strategy_rule: 当前策略参数（从缓存 info 取）

    Returns:
        [
          {
            "group": "基础设置",
            "fields": [
              {"key":"multiple_num","label":"杠杆倍数","type":"number",
               "value":3,"dvalue":3,"options":null,"editable":true},
              {"key":"direction","label":"方向","type":"select",
               "value":"long","dvalue":"long",
               "options":{"long":"做多","short":"做空"},"editable":true},
              {"key":"coin","label":"币种","type":"fixed",
               "value":"SOL","dvalue":null,"editable":false},
              ...
            ]
          },
          ...
        ]
    """
    groups = []

    for group in trade_fields:
        group_name = group.get("name", "")
        field_lists = group.get("field_lists", [])
        multiples = group.get("multiples", [])

        fields = []

        for f in field_lists:
            variable = f.get("variable", "")
            api_type = f.get("type", "input")
            field_type = _api_type_to_field_type(api_type)
            dvalue = f.get("dvalue")

            # options 格式转换: [{name,value}] → {value:name}
            raw_options = f.get("options")
            options = None
            if raw_options and isinstance(raw_options, list):
                options = {o["value"]: o["name"] for o in raw_options if "value" in o}

            # value 全部来自 API dvalue，不看 strategy_rule
            value = dvalue
            # 多维数组字段：从嵌套 multiples.dvalue 拼默认行
            if api_type == "multiple":
                value = []
                nested_multiples = f.get("multiples", [])
                for nm in nested_multiples:
                    nm_fields = nm.get("fields", [])
                    if nm_fields:
                        default_row = {mf["variable"]: mf.get("dvalue") for mf in nm_fields if mf.get("variable")}
                        value.append(default_row)
            field = {
                "key": variable,
                "label": f.get("name", variable),
                "type": field_type,
                "dvalue": dvalue,
                "value": value,
                "options": options,
                "editable": api_type != "input_fixed",
            }
            fields.append(field)

        # 多维数组字段：只读现有数据，不支持增删
        for m in multiples:
            m_field_name = m.get("name", "")  # 数组在 rule 中的 key，如 tiered_take_profit
            m_field_variable = m.get("variable", m_field_name)
            m_sub_fields = m.get("fields", [])

            # 从 strategy_rule 获取数组数据（可能为对象格式需转数组）
            rows = _normalize_array_value(strategy_rule.get(m_field_variable, []))
            if not isinstance(rows, list):
                rows = []

            # 每个数组元素作为一个嵌套字段组
            for idx, row in enumerate(rows):
                row_fields = []
                for mf in m_sub_fields:
                    variable = mf.get("variable", "")
                    row_fields.append({
                        "key": variable,
                        "label": mf.get("name", variable),
                        "type": "number",
                        "dvalue": mf.get("dvalue"),
                        "value": row.get(variable, mf.get("dvalue")),
                        "options": None,
                        "editable": mf.get("type") != "input_fixed",
                    })
                fields.append({
                    "_kind": "multiples_row",
                    "array_key": m_field_variable,
                    "row_index": idx,
                    "label": f"{m_field_name}[{idx + 1}]",
                    "fields": row_fields,
                })

        groups.append({"group": group_name, "fields": fields})

    return groups


def build_field_list(info: dict) -> list:
    strategy_type = str(info.get("strategy_type", ""))
    strategy_rule = info.get("strategy_rule", {})
    amt_type = str(info.get("amt_type", ""))

    if strategy_type != "2":
        # 非 st2: 返回扁平字段列表（无 schema）
        return [
            {"key": k, "label": PARAM_LABELS.get(k, k),
             "type": "unknown", "value": v}
            for k, v in strategy_rule.items()
        ]

    # strategy_type=2: 按 schema 构建
    fields = []
    rsi_enabled = str(strategy_rule.get("rsi_signal")) == "1"
    is_contract = amt_type == "2"
    tp_type = str(strategy_rule.get("take_profit_type", ""))

    for key, schema in ST2_FIELD_SCHEMA.items():
        # 条件检查
        condition = schema.get("condition", "")
        skip = False
        condition_detail = ""

        if condition == "amt_type=2" and not is_contract:
            skip = True
            condition_detail = "仅合约可用"
        elif condition == "rsi_signal=1" and not rsi_enabled:
            skip = True
            condition_detail = "RSI未开启"
        elif condition == "take_profit_type=3" and tp_type != "3":
            skip = True
            condition_detail = "止盈类型非3"

        # 子字段条件
        for parent_key, child_keys in schema.get("children", {}).items():
            if key in child_keys and str(strategy_rule.get(parent_key)) != parent_key:
                skip = True
                condition_detail = f"依赖 {parent_key}={parent_key}"
                break

        field = {
            "key": key,
            "label": schema["label"],
            "type": schema["type"],
            "value": strategy_rule.get(key),
            "options": schema.get("options"),
            "hint": schema.get("hint", ""),
        }
        if skip:
            field["hidden"] = True
            field["hidden_reason"] = condition_detail
        fields.append(field)

    return fields


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
            return error_result(
                title="❌ 获取机器人信息失败",
                message=result["error"],
                rule="不得自行重试或编造数据",
            )
        info = result["info"]

    # ── 第2步：可编辑检查 ──
    check = check_editable(info)
    strategy_type = str(info.get("strategy_type", ""))

    # ── 第3步：获取可编辑字段 ──
    strategy_rule = info.get("strategy_rule", {})

    if strategy_type == "2":
        # strategy_type=2: 硬编码 schema
        editable_rule = get_strategy_rule_for_edit(info)
        fields = build_field_list(info)
        field_groups = None  # st2 不需要按分组展示
    else:
        # strategy_type != 2: 调用 trade_field_info 获取动态字段
        strategy_id = str(info.get("strategy_id", ""))
        strategy_version = info.get("version", strategy_rule.get("version", ""))
        tf_result = fetch_trade_field_info(
            token, strategy_id, strategy_type, strategy_version, bot_id, agent_id,
        )
        if tf_result["ok"]:
            field_groups = build_field_list_from_api(tf_result["info"], strategy_rule)
            fields = None  # 非 st2 用 field_groups 替代 fields
        else:
            # 降级：用 strategy_rule 的原始 key 做扁平列表
            field_groups = None
            fields = [
                {"key": k, "label": PARAM_LABELS.get(k, k),
                 "type": "unknown", "value": v}
                for k, v in strategy_rule.items()
            ]
        editable_rule = strategy_rule

    return {
        "status": "preview",
        "bot_id": bot_id,
        "name": info.get("name", ""),
        "amt_type": str(info.get("amt_type", "")),
        "strategy_id": info.get("strategy_id", ""),
        "version": strategy_rule.get("version", ""),
        "editable_check": check,
        "strategy_type": strategy_type,
        "strategy_type_label": _strategy_type_label(strategy_type),
        # 结构化字段列表（Agent 据此渲染编辑界面）
        # - strategy_type=2: fields (扁平列表)
        # - 其他: field_groups (按分组，含 label/type/options)
        "fields": fields,
        "field_groups": field_groups,
        # 当前可编辑参数
        "strategy_rule": editable_rule,
        # 原始完整参数（供参考对比）
        "raw_rule": strategy_rule,
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
    执行策略编辑 — strategy_type=2 走 /Trade/strategy_update_do

    非 st2 走 /Strategy/trade_update_do（save_type=2 修改）
    """
    if strategy_type == "2":
        return _do_strategy_update(token, bot_id, strategy_type, new_rule, update_type, agent_id)
    else:
        return _do_trade_update(token, bot_id, strategy_type, new_rule, agent_id)


def _do_strategy_update(
    token: str,
    bot_id: str,
    strategy_type: str,
    new_rule: dict,
    update_type: int = 1,
    agent_id: Optional[str] = None,
) -> dict:
    """调用 /Trade/strategy_update_do（strategy_type=2）"""
    data = api_post(
        "/Trade/strategy_update_do",
        {
            "usertoken": token,
            "app_v": "2.0.0",
            "bot_id": bot_id,
            "update_type": update_type,
            "strategy_type": strategy_type,
            "rule": json.dumps(new_rule, ensure_ascii=False),
        },
        agent_id,
    )
    ok, msg = check_auth(data)
    if not ok:
        return {"status": "error", "message": msg}

    if not check_status(data):
        return {"status": "error", "message": data.get("msg", data.get("info", "未知错误")), "raw": data}

    return {"status": "ok", "data": data}


def _normalize_for_submission(rule: dict) -> dict:
    """
    提交前规范化：多维数组对象格式 {'1':{...}, '2':{...}} → 数组 [{...}, {...}]
    strategy_rule 中多维数字字段用数字字符串为 key 存为对象，
    但 /Strategy/trade_update_do 期望接收数组。
    """
    result = {}
    for key, val in rule.items():
        if _is_int_key_dict(val):
            sorted_items = sorted(val.items(), key=lambda kv: int(kv[0]))
            result[key] = [v for _, v in sorted_items]
        else:
            result[key] = val
    return result


def _is_int_key_dict(val) -> bool:
    """判断值是否为以数字字符串为 key 的非空 dict"""
    return isinstance(val, dict) and val and all(_is_int_key(k) for k in val)


def _is_int_key(s: str) -> bool:
    """判断字符串是否可解析为非负整数"""
    try:
        return int(s) >= 0
    except (ValueError, TypeError):
        return False


def _normalize_array_value(val):
    """多维数组对象 → 数组；非多维数组原样返回"""
    if _is_int_key_dict(val):
        sorted_items = sorted(val.items(), key=lambda kv: int(kv[0]))
        return [v for _, v in sorted_items]
    return val


def _collect_non_editable_keys(trade_fields: list) -> set:
    """收集所有 input_fixed 的字段 key（含嵌套 multiples 内子字段）"""
    keys: set = set()
    for group in trade_fields:
        for f in group.get("field_lists", []):
            if f.get("type") == "input_fixed":
                keys.add(f.get("variable", ""))
            # 嵌套 multiples 中也可能有 input_fixed
            for nm in f.get("multiples", []):
                for mf in nm.get("fields", []):
                    if mf.get("type") == "input_fixed":
                        keys.add(mf.get("variable", ""))
        for m in group.get("multiples", []):
            for mf in m.get("fields", []):
                if mf.get("type") == "input_fixed":
                    keys.add(mf.get("variable", ""))
    return keys


def _do_trade_update(
    token: str,
    bot_id: str,
    strategy_type: str,
    new_rule: dict,
    agent_id: Optional[str] = None,
) -> dict:
    """调用 /Strategy/trade_update_do（strategy_type != 2，save_type=2 修改）"""
    info = load_cached_detail(bot_id)
    strategy_id = ""
    if info:
        strategy_id = str(info.get("strategy_id", ""))

    data = api_post(
        "/Strategy/trade_update_do",
        {
            "usertoken": token,
            "app_v": "2.0.0",
            "save_type": "2",  # 修改
            "strategy_id": strategy_id,
            "strategy_type": strategy_type,
            "robot_id": bot_id,
            "rule": json.dumps(_normalize_for_submission(new_rule), ensure_ascii=False),
        },
        agent_id,
    )
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
            return error_result(
            title="❌ 获取机器人信息失败",
            message=result["error"],
            rule="不得自行重试",
        )
        info = result["info"]

    check = check_editable(info)
    if not check["editable"]:
        return blocked_result(
            title="❌ 该机器人不可编辑",
            reason=check["reason"],
            rule="该机器人当前不可编辑，不得尝试绕过",
            editable_check=check,
        )

    current_rule = get_strategy_rule_for_edit(info)

    # 不可编辑字段 key 集合（含嵌套 multiples 内子字段）
    non_editable_fields: set = set()
    if check["strategy_type"] != "2":
        strategy_id = str(info.get("strategy_id", ""))
        strategy_version = str(info.get("version", info.get("strategy_rule", {}).get("version", "")))
        tf_result = fetch_trade_field_info(
            token, strategy_id, check["strategy_type"], strategy_version, bot_id, agent_id,
        )
        if tf_result.get("ok"):
            non_editable_fields = _collect_non_editable_keys(tf_result["info"])
            # 从 API 字段构建完整当前值：优先 strategy_rule，其次 API dvalue
            api_current = {}
            for group in tf_result["info"]:
                for f in group.get("field_lists", []):
                    key = f.get("variable", "")
                    if not key:
                        continue
                    raw = current_rule.get(key)
                    if f.get("type") == "multiple":
                        # type=multiple: strategy_rule 有数据用数据，无数据从嵌套 multiples.dvalue 拼默认行
                        raw = _normalize_array_value(raw) if raw else []
                        if not raw:
                            for nm in f.get("multiples", []):
                                nm_fields = nm.get("fields", [])
                                if nm_fields:
                                    raw.append({mf["variable"]: mf.get("dvalue") for mf in nm_fields if mf.get("variable")})
                        api_current[key] = raw
                    else:
                        api_current[key] = raw if raw is not None else f.get("dvalue")
                for m in group.get("multiples", []):
                    key = m.get("variable", "")
                    if not key:
                        continue
                    raw = current_rule.get(key)
                    raw = _normalize_array_value(raw) if raw else []
                    # 无数据时从 multiples.fields.dvalue 拼默认行
                    if not raw:
                        for mf in m.get("fields", []):
                            default_row = {}
                            for sf in mf.get("fields", []):
                                if sf.get("variable"):
                                    default_row[sf["variable"]] = sf.get("dvalue")
                            if default_row:
                                raw.append(default_row)
                    api_current[key] = raw
            current_rule = api_current

    # 拦截用户修改不可编辑的字段
    blocked_fields = [k for k in proposed if k in non_editable_fields]
    if blocked_fields:
        return blocked_result(
            title="❌ 以下字段不可编辑",
            reason=f"{', '.join(blocked_fields)} 为固定参数，API 不支持修改",
            rule="这些字段为策略固定参数，不得尝试修改",
            blocked_fields=blocked_fields,
        )

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
            return error_result(
                title="❌ 获取机器人信息失败",
                message=result["error"],
                rule="不得自行重试",
            )
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