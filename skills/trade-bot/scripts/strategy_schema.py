#!/usr/bin/env python3
"""
策略参数 Schema — 将三份配置说明转为结构化字段定义

策略类型：
  7      — 星辰（网格）
  1/2/9/11 — 风霆（DCA 加仓）
  3/4/5/8  — 鲲鹏（趋势）
"""
from typing import Any, Optional

# ═══════════════════════════════════════════════════════════════
# 通用字段值映射（enum → 中文）
# ═══════════════════════════════════════════════════════════════

# 字段枚举值 → 中文显示
VALUE_MAP: dict[str, dict] = {
    "direction":         {"long": "做多", "short": "做空"},
    "trade_model":       {"long": "做多", "short": "做空", "all": "多空双开"},
    "grid_type":         {"1": "等差", "2": "等比"},
    "is_add_amt":        {"0": "不复投", "1": "复投"},
    "is_split_add_amt":  {"0": "不复投", "1": "复投"},
    "enable_grid_shift": {"0": "普通网格", "1": "移动网格", "false": "普通网格", "true": "移动网格"},
    "enable_start_opened":       {"0": "关闭", "1": "开启", "false": "关闭", "true": "开启"},
    "enable_base_position_control": {"0": "关闭", "1": "开启"},
    "enable_check_period":       {"0": "关闭", "1": "开启", "false": "关闭", "true": "开启"},
    "enable_stop_loss":          {"0": "关闭", "1": "开启", "false": "关闭", "true": "开启"},
    "enable_take_profit":        {"0": "关闭", "1": "开启", "false": "关闭", "true": "开启"},
    "neutral_strategy":          {"0": "否", "1": "是", "false": "否", "true": "是"},
    "max_loss_type":    {"1": "市价", "2": "限价"},
    "stop_loss_type":   {"1": "收益率", "2": "价格"},
    "take_profit_type": {"1": "关闭", "3": "开启"},
    "period_check_type": {"1": "系数", "2": "ATR"},
    "rsi_signal":       {"0": "关闭", "1": "开启"},
    "rsi_signal_type":  {"below": "向下穿过", "above": "向上穿过", "low": "低于", "high": "高于"},
    "enable_trough_pattern_add":       {"0": "关闭", "1": "开启"},
    "enable_peak_pattern_take_profit": {"0": "关闭", "1": "开启"},
    "profit_type":      {"1": "止盈比例%", "2": "ATR倍数"},
    "split_end_linear_enabled": {"0": "关闭", "1": "开启"},
}

# 字段名 → 中文标签
FIELD_LABEL: dict[str, str] = {
    # ── 通用 ──
    "coin":                  "交易对",
    "direction":             "策略方向",
    "initial_capital":       "投资金额",
    "multiple_num":          "杠杆倍数",
    "max_grid_size":         "最大加仓次数",
    "leverage":              "杠杆倍数",
    "asset_type":            "资产类型",
    "margin_mode":           "保证金模式",

    # ── 星辰 (type=7) ──
    "neutral_strategy":               "中性策略",
    "margin_reserve_ratio":           "预留保证金比例(%)",
    "profit_allocation_margin_ratio": "盈利分配保证金比例(%)",
    "full_reinvestment_threshold":    "全额复投触发值(%)",
    "grid_type":                      "网格模式",
    "grid_percentage":                "网格比例",
    "enable_grid_shift":              "网格类型",
    "enable_start_opened":            "立即建仓",
    "enable_base_position_control":   "底仓仓位控制",
    "init_max_entries":               "底仓最大数量",
    "enable_check_period":            "价格区间调整",
    "grid_period":                    "调整周期(天)",
    "period_check_type":              "区间计算方式",
    "grid_low_ratio":                 "最低价调整系数",
    "grid_high_ratio":                "最高价调整系数",
    "atr_period":                     "ATR周期",
    "atr_time_grain":                 "ATR时间刻度",
    "price_low":                      "最低价",
    "price_high":                     "最高价",
    "is_add_amt":                     "复投",
    "enable_stop_loss":               "止损开关",
    "stop_loss_type":                 "止损类型",
    "stop_loss":                      "止损目标",
    "enable_take_profit":             "止盈开关",
    "take_profit_type":               "止盈类型",
    "take_profit":                    "止盈目标",
    "fee_rate":                       "手续费率",

    # ── 风霆 (type=1/2/9/11) ──
    "fst_capital":            "初次下单保证金",
    "each_capital":           "加仓单保证金",
    "down_pct":               "下跌加仓比例(%)",
    "up_pct":                 "上涨加仓比例(%)",
    "take_profit_type":       "移动止盈",
    "stop_profit_multiple":   "止盈比例倍数",
    "first_take_profit_ratio":"止盈仓位比例(%)",
    "rsi_signal":             "RSI触发",
    "rsi_period":             "RSI周期",
    "rsi_signal_type":        "RSI触发条件",
    "rsi_buy_threshold":      "RSI触发阈值",
    "rsi_time_grain":         "RSI K线周期",
    "add_amt_multiples":      "加仓金额倍数",
    "add_spread_multiples":   "加仓价差倍数",
    "max_loss_type":          "止损类型",
    "max_loss_pct":           "止损目标(%)",
    "enable_trough_pattern_add":       "低点形态加仓",
    "trough_pattern_timeframe":        "低点形态时间刻度",
    "trough_add_spread_multiples":     "低点加仓倍数",
    "enable_peak_pattern_take_profit": "顶点形态止盈",
    "peak_pattern_timeframe":          "顶点形态时间刻度",
    "is_split_add_amt":                "分仓复投",
    "split_trigger_time_period":       "分仓触发天数",
    "split_trigger_pct":               "分仓触发下跌比例(%)",
    "split_sell_pct":                  "分仓止盈目标(%)",
    "version":                         "版本",
    "add_amt_pct":                     "复投比例(%)",
    "ema_slow_period":                 "EMA慢线周期",
    "ema_fast_period":                 "EMA快线周期",
    "ema_long_period":                 "EMA长线周期",
    "ema_time_grain":                  "EMA时间刻度",
    "oppo_add_amt_pct":              "逆趋势复投比例(%)",
    "oppo_fst_capital":              "逆趋势初次下单保证金",
    "oppo_each_capital":             "逆趋势加仓单保证金",
    "oppo_max_grid_size":            "逆趋势最大加仓次数",
    "oppo_down_pct":                 "逆趋势下跌加仓比例(%)",
    "oppo_up_pct":                   "逆趋势止盈目标(%)",
    "oppo_rsi_signal":               "逆趋势RSI触发",
    "oppo_rsi_period":               "逆趋势RSI周期",
    "oppo_rsi_signal_type":          "逆趋势RSI触发条件",
    "oppo_rsi_buy_threshold":        "逆趋势RSI触发阈值",
    "oppo_split_trigger_time_period": "逆趋势分仓触发天数",
    "oppo_split_trigger_pct":         "逆趋势分仓触发上涨比例(%)",
    "oppo_split_sell_pct":            "逆趋势分仓止盈目标(%)",
    "stop_loss_multi":                "最大加仓止损倍数",
    "multiple_num1":                  "EMA全触发杠杆倍数",
    "trend_multiple_num":             "EMA分割线",
    "atr_vol_period":                 "波动率周期",
    "atr_vol_time_grain":             "波动率时间刻度",
    "min_add_pct":                    "最小加仓比例(%)",
    "split_end_pct":                  "分仓结束止盈比例(%)",
    "split_end_linear_enabled":       "线性回撤止盈",
    "split_end_ignore_drawdown":      "忽略回撤阈值(%)",
    "split_end_tp_ratio_at_min":      "最小回撤止盈比例(%)",
    "split_end_tp_ratio_at_max":      "最大回撤止盈比例(%)",
    "split_end_max_drawdown":         "最大回撤阈值(%)",
    "split_end_min_drawdown":         "最小回撤阈值(%)",

    # ── 鲲鹏 (type=3/4/5/8) ──
    "pause_short_counter":     "锤子形态暂停K线周期",
    "macd_fast_period":        "MACD短期",
    "macd_slow_period":        "MACD长期",
    "macd_period":             "MACD信号周期",
    "macd_sell_diff":          "MACD卖出差值",
    "loss_time_period":        "止损判断周期",
    "min_macd":                "开仓MACD最低值",
    "max_long_macd":           "停止多转空MACD最大值",
    "max_medium_term_macd":    "中周期停止开仓MACD最大值",
    "max_long_term_macd":      "长周期停止开仓MACD最大值",
    "bollinger_period":        "布林带周期",
    "bollinger_time_grain":    "布林带时间刻度",
    "min_up_pct":              "做多止盈下限(%)",
    "min_down_pct":            "做空止盈下限(%)",
    "reversal_pct":            "趋势反转比例(%)",
    "kalman_short_len":        "Kalman短周期",
    "kalman_long_len":         "Kalman长周期",
    "kalman_time_grain":       "Kalman时间刻度",
    "trade_model":             "交易类型",
    "tiered_take_profit":      "分层止盈",
    "position_ratio":          "仓位百分比",
    "profit_ratio":            "止盈比例/ATR倍数",
    "profit_type":             "止盈类型",
    "ema_atr_period":          "ATR时间周期",
    "atr_max_loss_muti":       "ATR止损倍数",
    "bollinger_width_period":  "低波动布林周期",
    "bollinger_width_mult":    "交易量衰弱倍数",
    "bollinger_width_threshold":"低波动过滤阈值",

    # ── strategy_rule 中可能出现的其他键 ──
    "fst_capital":             "初次下单金额",
    "grid_num":                "网格数量",
    "base_price":              "基准价",
    "take_profit_status":      "止盈状态",
    "stop_loss_status":        "止损状态",
    "margin_reserve":          "保证金预留",
    "order_count":             "订单数",
    "each_capital":            "单笔金额",
    "strategy_id":             "策略ID",
    "strategy_type":           "策略类型",
}

# ═══════════════════════════════════════════════════════════════
# 分组定义（按条件组织）
# ═══════════════════════════════════════════════════════════════

def _label(value: Any, key: str) -> str:
    """值 → 中文展示"""
    vm = VALUE_MAP.get(key, {})
    return vm.get(str(value), str(value))


def _build_field(key: str, raw_value: Any) -> dict:
    """构建单个字段 {key, label, value}"""
    return {
        "key": key,
        "label": FIELD_LABEL.get(key, key),
        "value": _label(raw_value, key),
        "_raw": raw_value,
    }


def _bool_val(data: dict, key: str) -> Optional[bool]:
    """读取布尔字段（兼容 0/1, true/false, True/False）"""
    v = data.get(key)
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    s = str(v).lower()
    if s in ("1", "true"):
        return True
    if s in ("0", "false"):
        return False
    return None


def analyze(data: dict, token: str = "", agent_id: str = "") -> dict:
    """
    分析 strategy_rule 返回分组化结果。

    已知类型（星辰/风霆/鲲鹏）→ 代码直出分组
    未知类型 → 调 /Strategy/field_info 动态获取字段定义后匹配

    Returns:
        {"_type": "风霆V4.3", "_type_id": "11",
         "groups": [{"name": "基础设置", "fields": [...]}, ...]}
    """
    st = str(data.get("strategy_type", ""))
    version = str(data.get("version", ""))
    groups: list[dict] = []

    # ── 策略类型标签 ──
    type_labels: dict[str, str] = {
        "1": "风霆", "2": "风霆(合约马丁)", "3": "鲲鹏V1", "4": "鲲鹏V2",
        "5": "鲲鹏V3", "7": "星辰", "8": "鲲鹏V4", "9": "风霆(形态)",
        "11": "风霆V4",
    }
    type_label = type_labels.get(st, f"策略类型{st}")
    if version:
        type_label += f" v{version}"

    # ── 已知类型走代码分组 ──
    if st in ("1", "2", "3", "4", "5", "7", "8", "9", "11"):
        groups = _analyze_known(data, st, version)
    # ── 未知类型调 API ──
    elif token and st:
        groups = _analyze_from_api(data, st, version, token, agent_id)
    else:
        # 无 token，裸透传
        groups = _raw_fallback(data)

    return {
        "_type": type_label,
        "_type_id": st,
        "groups": groups,
    }


def _raw_fallback(data: dict) -> list[dict]:
    """无 token 时的裸透传"""
    fields = [_build_field(k, v) for k, v in data.items() if k != "strategy_type"]
    return [{"name": "策略参数", "fields": fields}]

def _analyze_known(data: dict, st: str, version: str) -> list[dict]:
    """已知类型（星辰/风霆/鲲鹏）的代码分组"""
    groups: list[dict] = []
    used: set[str] = set()

    def _add_group(name: str, keys: list[str]):
        fields = [_build_field(k, data[k]) for k in keys if k in data]
        if fields:
            groups.append({"name": name, "fields": fields})
        used.update(k for k in keys if k in data)

    # ═══════════════════════════════════════════
    # 星辰 (type=7)
    # ═══════════════════════════════════════════
    if st == "7":
        _add_group("基础设置", [
            "coin", "direction", "neutral_strategy", "initial_capital",
            "multiple_num", "max_grid_size", "fee_rate",
        ])
        _add_group("资金管理", [
            "margin_reserve_ratio", "profit_allocation_margin_ratio",
            "full_reinvestment_threshold",
        ])

        enable_shift = _bool_val(data, "enable_grid_shift")

        if enable_shift is True:
            _add_group("移动网格", [
                "enable_grid_shift", "grid_type", "grid_percentage",
            ])
        else:
            # 普通网格 或 中性策略
            _add_group("网格设置", [
                "enable_grid_shift", "grid_type", "grid_percentage",
                "enable_start_opened",
            ])
            if _bool_val(data, "enable_start_opened"):
                if _bool_val(data, "enable_base_position_control"):
                    _add_group("底仓控制", ["enable_base_position_control", "init_max_entries"])

            _add_group("价格区间", ["enable_check_period"])
            if _bool_val(data, "enable_check_period"):
                pct = str(data.get("period_check_type", ""))
                if pct == "2":
                    _add_group("ATR参数", [
                        "period_check_type", "grid_period",
                        "atr_period", "atr_time_grain",
                        "grid_low_ratio", "grid_high_ratio",
                    ])
                else:
                    _add_group("区间参数", [
                        "period_check_type", "grid_period",
                        "grid_low_ratio", "grid_high_ratio",
                    ])
            else:
                _add_group("固定价格", ["price_low", "price_high"])

        _add_group("复投", ["is_add_amt"])

        # 止损
        _add_group("止损", ["max_loss_type", "max_loss_pct"])
        if _bool_val(data, "enable_stop_loss"):
            _add_group("止损开关", [
                "enable_stop_loss", "stop_loss_type", "stop_loss",
            ])

        # 止盈
        if _bool_val(data, "enable_take_profit"):
            _add_group("止盈参数", [
                "enable_take_profit", "take_profit_type", "take_profit",
            ])
        else:
            _add_group("止盈", ["enable_take_profit"])

    # ═══════════════════════════════════════════
    # 风霆 (type=1/2/9/11)
    # ═══════════════════════════════════════════
    elif st in ("1", "2", "9", "11"):
        _add_group("基础设置", [
            "coin", "direction", "initial_capital", "multiple_num",
        ])
        _add_group("加仓参数", [
            "fst_capital", "each_capital", "max_grid_size",
            "down_pct", "up_pct",
        ])

        # 移动止盈
        tp_type = str(data.get("take_profit_type", ""))
        if tp_type == "3":
            _add_group("移动止盈", [
                "take_profit_type", "stop_profit_multiple",
                "first_take_profit_ratio",
            ])

        # RSI
        if _bool_val(data, "rsi_signal") or str(data.get("rsi_signal", "")) == "1":
            _add_group("RSI信号", [
                "rsi_signal", "rsi_period", "rsi_time_grain",
                "rsi_signal_type", "rsi_buy_threshold",
            ])
        else:
            _add_group("RSI信号", ["rsi_signal"])

        _add_group("加仓倍数与复投", [
            "add_amt_multiples", "add_spread_multiples", "is_add_amt",
        ])
        _add_group("止损", ["max_loss_type", "max_loss_pct"])

        # type=9 特有
        if st == "9":
            if _bool_val(data, "enable_trough_pattern_add"):
                _add_group("低点形态", [
                    "enable_trough_pattern_add",
                    "trough_pattern_timeframe",
                    "trough_add_spread_multiples",
                ])
            else:
                _add_group("低点形态", ["enable_trough_pattern_add"])

            if _bool_val(data, "rsi_signal") and _bool_val(data, "enable_peak_pattern_take_profit"):
                _add_group("顶点形态", [
                    "enable_peak_pattern_take_profit",
                    "peak_pattern_timeframe",
                ])
            elif _bool_val(data, "rsi_signal"):
                _add_group("顶点形态", ["enable_peak_pattern_take_profit"])

        # type=11 版本相关
        if st == "11":
            _add_group("分仓设置", [
                "is_split_add_amt", "split_trigger_time_period",
                "split_trigger_pct", "split_sell_pct",
            ])

            ver = version.replace("V", "").replace("v", "")

            if ver == "4.0":
                _add_group("V4.0参数", ["version", "add_amt_pct"])

            elif ver == "4.1":
                _add_group("牛熊分隔线", [
                    "version", "ema_slow_period", "ema_time_grain",
                ])
                _add_group("顺趋势", ["add_amt_pct", "oppo_add_amt_pct"])
                _add_group("逆趋势策略", [
                    "oppo_fst_capital", "oppo_each_capital",
                    "oppo_max_grid_size", "oppo_down_pct", "oppo_up_pct",
                ])
                # 逆趋势RSI
                oppo_rsi = str(data.get("oppo_rsi_signal", ""))
                if oppo_rsi == "1":
                    _add_group("逆趋势RSI", [
                        "oppo_rsi_signal", "oppo_rsi_period",
                        "oppo_rsi_signal_type", "oppo_rsi_buy_threshold",
                    ])
                _add_group("逆趋势分仓", [
                    "oppo_split_trigger_time_period",
                    "oppo_split_trigger_pct", "oppo_split_sell_pct",
                ])

            elif ver in ("4.2", "4.3"):
                base_keys = ["version", "add_amt_pct", "stop_loss_multi",
                             "ema_time_grain", "multiple_num1"]
                if ver == "4.3":
                    extra = ["atr_vol_period", "atr_vol_time_grain", "min_add_pct"]
                else:
                    extra = []
                _add_group(f"V{ver}参数", base_keys + extra)

                # EMA分割线（trend_multiple_num 数组）
                tmn = data.get("trend_multiple_num")
                if isinstance(tmn, list) and tmn:
                    # 作为单独的数组字段透传
                    pass  # 会在收尾阶段被加入

                if ver == "4.3":
                    _add_group("分仓结束设置", [
                        "split_end_pct", "split_end_linear_enabled",
                        "split_end_ignore_drawdown",
                        "split_end_tp_ratio_at_min", "split_end_tp_ratio_at_max",
                        "split_end_max_drawdown", "split_end_min_drawdown",
                    ])

    # ═══════════════════════════════════════════
    # 鲲鹏 (type=3/4/5/8)
    # ═══════════════════════════════════════════
    elif st in ("3", "4", "5", "8"):
        if st == "8":
            _add_group("基础设置", [
                "coin", "trade_model", "initial_capital", "multiple_num",
            ])
            _add_group("布林带", ["bollinger_period", "bollinger_time_grain"])
            _add_group("Kalman", [
                "kalman_short_len", "kalman_long_len", "kalman_time_grain",
            ])
            _add_group("止盈", ["up_pct", "down_pct"])

            ver = version.replace("V", "").replace("v", "")
            # 分层止盈透传（tiered_take_profit）
            if ver == "4.2":
                _add_group("ATR", [
                    "version", "ema_atr_period", "ema_fast_period",
                    "atr_max_loss_muti",
                ])
            elif ver == "4.3":
                _add_group("低波动过滤", [
                    "version", "bollinger_width_period",
                    "bollinger_width_mult", "bollinger_width_threshold",
                ])
                _add_group("ATR", [
                    "ema_atr_period", "ema_fast_period", "atr_max_loss_muti",
                ])
            else:
                _add_group("版本", ["version"])
            _add_group("止损", ["max_loss_type", "max_loss_pct"])
        else:
            # type=3/4/5
            _add_group("基础设置", [
                "coin", "initial_capital", "multiple_num",
            ])
            _add_group("EMA", [
                "ema_slow_period", "ema_fast_period", "ema_long_period",
                "ema_time_grain",
            ])
            if st in ("3", "4"):
                _add_group("做多/做空止盈", [
                    "up_pct", "down_pct", "pause_short_counter",
                ])
            if st in ("4", "5"):
                _add_group("MACD", [
                    "macd_fast_period", "macd_slow_period", "macd_period",
                    "macd_sell_diff", "loss_time_period",
                ])
            if st == "5":
                _add_group("MACD过滤", [
                    "min_macd", "max_long_macd",
                    "max_medium_term_macd", "max_long_term_macd",
                ])
                _add_group("布林带", ["bollinger_period", "bollinger_time_grain"])
                if "min_up_pct" in data:
                    _add_group("V3.1止盈", [
                        "up_pct", "min_up_pct", "down_pct", "min_down_pct",
                    ])
            _add_group("反转", ["reversal_pct"])
            _add_group("止损", ["max_loss_type", "max_loss_pct"])

    # 收尾：未分组的字段统一丢到「其他」
    remaining = {}
    for k, v in data.items():
        if k not in used and k not in ("strategy_type",):
            if isinstance(v, list):
                remaining[k] = v
            else:
                remaining[k] = v
    if remaining:
        fields = [_build_field(k, v) for k, v in remaining.items()]
        groups.append({"name": "其他参数", "fields": fields})

    return groups


def _analyze_from_api(data: dict, st: str, version: str,
                      token: str, agent_id: str) -> list[dict]:
    """
    未知策略类型 → 调 /Strategy/field_info 获取字段定义，匹配值后分组返回。
    """
    from api_client import api_post
    params: dict = {"strategy_type": st, "usertoken": token}
    sid = data.get("strategy_id", "")
    if sid:
        params["strategy_id"] = sid
    if version:
        params["strategy_version"] = version

    resp = api_post("/Strategy/field_info", params, agent_id)
    if resp.get("status") != 1:
        return _raw_fallback(data)

    schema_groups = resp.get("info", [])
    if not isinstance(schema_groups, list) or not schema_groups:
        return _raw_fallback(data)

    groups: list[dict] = []
    used: set[str] = set()

    # 递归展开字段定义，收集 variable→label 映射 + 枚举映射
    def _walk_fields(field_list: list, label_map: dict, enum_map: dict):
        for fdef in field_list:
            var = fdef.get("variable", "")
            if not var:
                continue
            label_map[var] = fdef.get("name", var)
            opts = fdef.get("options")
            if opts and isinstance(opts, list):
                enum_map[var] = {str(o["value"]): o.get("name", str(o["value"])) for o in opts}
            muls = fdef.get("multiples", [])
            for m in (muls if isinstance(muls, list) else []):
                _walk_fields(m.get("fields", []), label_map, enum_map)

    for sg in schema_groups:
        group_name = sg.get("name", "策略参数")
        label_map: dict[str, str] = {}
        enum_map: dict[str, dict] = {}
        _walk_fields(sg.get("field_lists", []), label_map, enum_map)

        fields = []
        for var, label in label_map.items():
            if var in data:
                raw = data[var]
                ev = enum_map.get(var, {})
                display = ev.get(str(raw), str(raw)) if ev else _label(raw, var)
                fields.append({
                    "key": var,
                    "label": label,
                    "value": display,
                    "_raw": raw,
                })
                used.add(var)
        if fields:
            groups.append({"name": group_name, "fields": fields})

    remaining = {}
    for k, v in data.items():
        if k not in used and k not in ("strategy_type",):
            remaining[k] = v
    if remaining:
        fields = [_build_field(k, v) for k, v in remaining.items()]
        groups.append({"name": "其他参数", "fields": fields})

    return groups