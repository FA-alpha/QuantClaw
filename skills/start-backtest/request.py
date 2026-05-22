#!/usr/bin/env python3
"""
QuantClaw 回测接口请求统一管理模块

设计原则:
1. 标准方法传参
2. 明确的错误处理
3. 详细的代码注释
4. 友好的返回信息
"""

import requests
import json
import logging
from typing import Dict, Any, Optional, List, Union, NamedTuple

class StrategyRequirement(NamedTuple):
    """策略分配需求"""
    coin_long_pairs: List[str]
    coin_short_pairs: List[str]
    ai_time_long_types: List[str]
    ai_time_short_types: List[str]
    ai_time_id_mapping: Dict[str, str]
    has_ai_time: bool

def check_allocation_completeness(
    requirement: StrategyRequirement, 
    user_allocation: Dict[str, Any]
) -> Dict[str, List[str]]:
    """
    检查分配方案完整性
    
    :param requirement: 策略需求
    :param user_allocation: 用户提供的分配方案
    :return: 缺失参数列表
    """
    missing = {
        "coin_long_allocation": [],
        "coin_short_allocation": [],
        "ai_time_long_allocation": [],
        "ai_time_short_allocation": []
    }

    # 检查做多币种分配
    user_coin_long_alloc = user_allocation.get("coin_long_allocation", {})
    for coin in requirement.coin_long_pairs:
        if coin not in user_coin_long_alloc:
            missing["coin_long_allocation"].append(coin)

    # 检查做空币种分配  
    user_coin_short_alloc = user_allocation.get("coin_short_allocation", {})
    for coin in requirement.coin_short_pairs:
        if coin not in user_coin_short_alloc:
            missing["coin_short_allocation"].append(coin)

    # 检查AI时间做多分配
    if requirement.has_ai_time:
        user_ai_time_long_alloc = user_allocation.get("ai_time_long_allocation", {})
        for ai_time in requirement.ai_time_long_types:
            if ai_time not in user_ai_time_long_alloc:
                missing["ai_time_long_allocation"].append(ai_time)

        # 检查AI时间做空分配
        user_ai_time_short_alloc = user_allocation.get("ai_time_short_allocation", {})
        for ai_time in requirement.ai_time_short_types:
            if ai_time not in user_ai_time_short_alloc:
                missing["ai_time_short_allocation"].append(ai_time)

    return {k: v for k, v in missing.items() if v}

def format_missing_params_message(
    requirement: StrategyRequirement, 
    missing: Dict[str, List[str]]
) -> str:
    """
    格式化缺失参数消息
    
    :param requirement: 策略需求
    :param missing: 缺失参数列表
    :return: 格式化的消息
    """
    if not missing:
        return "✅ 分配方案完整"

    message_parts = []
    if missing.get("coin_long_allocation"):
        message_parts.append(f"❌ 做多币种分配缺失: {', '.join(missing['coin_long_allocation'])}")
    
    if missing.get("coin_short_allocation"):
        message_parts.append(f"❌ 做空币种分配缺失: {', '.join(missing['coin_short_allocation'])}")
    
    if missing.get("ai_time_long_allocation"):
        message_parts.append(f"❌ AI时间做多分配缺失: {', '.join(missing['ai_time_long_allocation'])}")
    
    if missing.get("ai_time_short_allocation"):
        message_parts.append(f"❌ AI时间做空分配缺失: {', '.join(missing['ai_time_short_allocation'])}")

    return " | ".join(message_parts)

class BacktestRequestError(Exception):
    """自定义异常类，用于标准化错误处理"""
    def __init__(self, message: str, error_code: Optional[str] = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class BacktestRequest:
    """
    回测接口请求管理器
    
    提供标准化的接口请求方法，确保参数校验和错误处理
    """

    def __init__(self, token: str):
        """
        初始化请求管理器
        
        :param token: 用户认证令牌
        """
        if not token or not isinstance(token, str):
            raise BacktestRequestError("无效的用户令牌", "INVALID_TOKEN")
        
        self.token = token
        self.base_url = "https://www.fourieralpha.com/Mobile"
        self.logger = logging.getLogger(__name__)
        self._cache = {}

    def _validate_params(self, params: Dict[str, Any]) -> None:
        """
        通用参数校验方法
        
        :param params: 待校验的参数字典
        :raises BacktestRequestError: 参数校验失败时抛出
        """
        for key, value in params.items():
            if value is None:
                raise BacktestRequestError(f"参数 {key} 不能为空", "PARAM_MISSING")

    def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        统一接口请求方法
        
        :param endpoint: 接口端点
        :param data: 请求参数
        :return: 解析后的接口响应
        :raises BacktestRequestError: 请求失败时抛出
        """
        # 通用参数校验
        self._validate_params(data)

        try:
            # 添加通用请求参数
            data.update({
                "usertoken": self.token,
                "app_v": "2.0.0",
                "lang": 1
            })

            # 发起请求
            response = requests.post(
                f"{self.base_url}/{endpoint}",
                data=data,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()

            # 检查接口返回状态
            if result.get("status") != 1:
                error_msg = result.get('msg', '未知错误')
                raise BacktestRequestError(
                    f"接口请求失败: {error_msg}", 
                    "API_REQUEST_FAILED"
                )

            return result

        except requests.RequestException as e:
            raise BacktestRequestError(
                f"网络请求异常: {str(e)}", 
                "NETWORK_ERROR"
            )

    def get_strategy_groups(
        self, 
        usertoken: Optional[str] = None,
        page: int = 1, 
        limit: int = 10,
        search_val: Optional[str] = None,
        app_v: str = "2.0.0"
    ) -> Dict[str, Any]:
        """
        获取策略组列表
        
        :param usertoken: 用户认证Token
        :param page: 页码，默认第一页
        :param limit: 每页数量，默认10个，全部传-1
        :param search_val: 搜索内容
        :param app_v: 应用版本号，默认2.0.0
        :return: 策略组列表
        """
        try:
            # 构造请求参数
            params: Dict[str, Any] = {
                "usertoken": usertoken or self.token,
                "page": page,
                "limit": limit,
                "app_v": app_v
            }
            
            # 添加搜索参数
            if search_val:
                params["search_val"] = search_val

            return self._make_request("Strategy/group_lists", params)
        except BacktestRequestError as e:
            self.logger.error(f"获取策略组失败: {e.message}")
            return {
                "status": "error",
                "message": e.message,
                "error_code": e.error_code
            }

    def get_strategies(
        self, 
        page: int = 1, 
        limit: int = 10,
        search_val: Optional[str] = None,
        show_type: Optional[int] = 1,
        data_grade: Optional[int] = 0,
        app_v: str = "2.0.0"
    ) -> Dict[str, Any]:
        """
        获取策略列表
        
        :param page: 页码，默认第一页
        :param limit: 每页数量，默认10个，全部传-1
        :param search_val: 搜索内容
        :param show_type: 显示类型（1-有效策略 2-历史策略）
        :param data_grade: 数据代次（0-所有策略 1-老策略 2=新策略）
        :param app_v: 应用版本号，默认2.0.0
        :return: 策略列表
        """
        try:
            # 构造请求参数
            params: Dict[str, Any] = {
                "page": page,
                "limit": limit,
                "app_v": app_v
            }
            
            # 添加可选参数
            if search_val:
                params["search_val"] = search_val
            if show_type is not None:
                params["show_type"] = show_type
            if data_grade is not None:
                params["data_grade"] = data_grade

            return self._make_request("Strategy/lists", params)
        except BacktestRequestError as e:
            self.logger.error(f"获取策略列表失败: {e.message}")
            return {
                "status": "error",
                "message": e.message,
                "error_code": e.error_code
            }

    # 计算策略保证金
    def calc_margin(
        self, 
        strategys_json: List[Dict[str, Any]],
        leverage: float,
        long_pct: float, 
        short_pct: float, 
        long_coin_pcts: List[Dict[str, Any]],
        short_coin_pcts: List[Dict[str, Any]],
        long_ai_time_pcts: Optional[List[Dict[str, Any]]] = None,
        short_ai_time_pcts: Optional[List[Dict[str, Any]]] = None,
        app_v: str = "2.0.0"
    ) -> Dict[str, Any]:
        """
        计算策略保证金
        
        :param strategys_json: 策略列表，格式：[{"id": 策略ID, "multiple_num": 倍数, "direction": 方向, "ai_time_id": AI时间ID, "coin": 币种}]
        :param leverage: 保证金对应杠杆
        :param long_pct: 做多保证金占比
        :param short_pct: 做空保证金占比
        :param long_coin_pcts: 做多币种保证金占比，格式：[{"coin": 币种, "pct": 占比}]
        :param short_coin_pcts: 做空币种保证金占比，格式：[{"coin": 币种, "pct": 占比}]
        :param long_ai_time_pcts: 做多AI回测时间类型占比（可选）
        :param short_ai_time_pcts: 做空AI回测时间类型占比（可选）
        :param app_v: 应用版本号，默认2.0.0
        :return: 保证金分配详情
        """
        try:
            # 构造请求参数
            params: Dict[str, Any] = {
                "strategys_json": strategys_json,
                "leverage": leverage,
                "long_pct": long_pct,
                "short_pct": short_pct,
                "long_coin_pcts": long_coin_pcts,
                "short_coin_pcts": short_coin_pcts,
                "app_v": app_v
            }
            
            # 可选参数
            if long_ai_time_pcts:
                params["long_ai_time_pcts"] = long_ai_time_pcts
            if short_ai_time_pcts:
                params["short_ai_time_pcts"] = short_ai_time_pcts

            return self._make_request("Strategy/calc_margin", params)
        except BacktestRequestError as e:
            self.logger.error(f"保证金分配计算失败: {e.message}")
            return {
                "status": "error",
                "message": e.message,
                "error_code": e.error_code
            }

    # 获取回测列表
    def get_backtest_list(
        self, 
        page: int = 1, 
        limit: int = 10,
        search_val: Optional[str] = None,
        search_status: Optional[int] = None,
        search_type: Optional[int] = None,
        app_v: str = "2.0.0"
    ) -> Dict[str, Any]:
        """
        获取回测列表
        
        :param page: 页码，默认第一页
        :param limit: 每页数量，默认10个，全部传-1
        :param search_val: 搜索内容
        :param search_status: 状态筛选
        :param search_type: 类型筛选
        :param app_v: 应用版本号，默认2.0.0
        :return: 回测列表
        """
        try:
            # 构造请求参数
            params: Dict[str, Any] = {
                "page": page,
                "limit": limit,
                "app_v": app_v
            }
            
            # 添加可选参数
            if search_val:
                params["search_val"] = search_val
            if search_status is not None:
                params["search_status"] = search_status
            if search_type is not None:
                params["search_type"] = search_type

            return self._make_request("Backtrack/lists", params)
        except BacktestRequestError as e:
            self.logger.error(f"获取回测列表失败: {e.message}")
            return {
                "status": "error",
                "message": e.message,
                "error_code": e.error_code
            }

    # 检查回测状态
    def check_backtest_status(
        self, 
        back_id: str,
        app_v: str = "2.0.0"
    ) -> Dict[str, Any]:
        """
        检查回测状态
        
        :param back_id: 回测任务ID
        :param app_v: 应用版本号，默认2.0.0
        :return: 回测状态信息
        """
        try:
            if not back_id:
                raise BacktestRequestError("回测任务ID不能为空", "BACKTEST_ID_EMPTY")
            
            return self._make_request("Backtrack/check_status", {
                "back_id": back_id,
                "app_v": app_v
            })
        except BacktestRequestError as e:
            self.logger.error(f"检查回测状态失败: {e.message}")
            return {
                "status": "error",
                "message": e.message,
                "error_code": e.error_code
            }

    # 获取回测统计信息
    def get_backtest_stat_info(
        self, 
        back_id: str,
        app_v: str = "2.0.0"
    ) -> Dict[str, Any]:
        """
        获取回测统计信息
        
        :param back_id: 回测任务ID
        :param app_v: 应用版本号，默认2.0.0
        :return: 回测统计详情
        """
        try:
            if not back_id:
                raise BacktestRequestError("回测任务ID不能为空", "BACKTEST_ID_EMPTY")
            
            return self._make_request("Backtrack/stat_info", {
                "back_id": back_id,
                "app_v": app_v
            })
        except BacktestRequestError as e:
            self.logger.error(f"获取回测统计信息失败: {e.message}")
            return {
                "status": "error",
                "message": e.message,
                "error_code": e.error_code
            }

    def analyze_strategies_for_allocation(
        self, 
        strategy_ids: Optional[List[str]] = None,
        strategy_group_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分析策略分配需求
        
        :param strategy_ids: 策略ID列表
        :param strategy_group_id: 策略组ID
        :return: 分析结果
        """
        try:
            # 如果没有传入策略ID，尝试通过策略组获取
            if not strategy_ids and strategy_group_id:
                group_result = self.get_strategies(strategy_group_id=strategy_group_id)
                if group_result.get("status") == "error":
                    return group_result
                strategy_ids = [str(strategy["id"]) for strategy in group_result.get("info", [])]

            if not strategy_ids:
                raise BacktestRequestError("未指定策略ID或策略组", "NO_STRATEGY_SPECIFIED")

            # 获取每个策略的详细信息
            strategies_info = []
            for sid in strategy_ids:
                strategy_info = self.get_strategies(search_val=sid)
                if strategy_info.get("status") == "error":
                    return strategy_info
                strategies_info.extend(strategy_info.get("info", []))

            # 解析策略需求
            coin_long_pairs = set()
            coin_short_pairs = set()
            ai_time_long_types = set()
            ai_time_short_types = set()
            ai_time_id_mapping = {}

            for strategy in strategies_info:
                # 币种分析
                coin = strategy.get("coin")
                direction = strategy.get("direction")
                ai_time_id = strategy.get("ai_time_id")
                ai_time_name = strategy.get("ai_time_name")

                if direction == "long" and coin:
                    coin_long_pairs.add(coin)
                elif direction == "short" and coin:
                    coin_short_pairs.add(coin)

                # AI时间分析
                if ai_time_id and ai_time_name:
                    if direction == "long":
                        ai_time_long_types.add(ai_time_name)
                    else:
                        ai_time_short_types.add(ai_time_name)
                    ai_time_id_mapping[ai_time_name] = ai_time_id

            result = {
                "coin_long_pairs": list(coin_long_pairs),
                "coin_short_pairs": list(coin_short_pairs),
                "ai_time_long_types": list(ai_time_long_types),
                "ai_time_short_types": list(ai_time_short_types),
                "ai_time_id_mapping": ai_time_id_mapping,
                "has_ai_time": bool(ai_time_long_types or ai_time_short_types)
            }

            return {
                "status": 1,
                "info": result
            }

        except BacktestRequestError as e:
            self.logger.error(f"策略分析失败: {e.message}")
            return {
                "status": "error",
                "message": e.message,
                "error_code": e.error_code
            }

    def check_allocation_completeness(
        self, 
        strategy_ids: Optional[List[str]] = None,
        strategy_group_id: Optional[str] = None, 
        user_allocation: Dict[str, Any] = {}
    ) -> Dict[str, Any]:
        """
        检查保证金分配方案完整性
        
        :param strategy_ids: 策略ID列表
        :param strategy_group_id: 策略组ID
        :param user_allocation: 用户提供的分配方案
        :return: 完整性检查结果
        """
        try:
            # 分析策略需求
            requirement_result = self.analyze_strategies_for_allocation(
                strategy_ids, 
                strategy_group_id
            )

            if requirement_result.get("status") == "error":
                return requirement_result

            requirement_info = requirement_result.get("info", {})
            requirement = StrategyRequirement(
                coin_long_pairs=requirement_info.get("coin_long_pairs", []),
                coin_short_pairs=requirement_info.get("coin_short_pairs", []),
                ai_time_long_types=requirement_info.get("ai_time_long_types", []),
                ai_time_short_types=requirement_info.get("ai_time_short_types", []),
                ai_time_id_mapping=requirement_info.get("ai_time_id_mapping", {}),
                has_ai_time=requirement_info.get("has_ai_time", False)
            )

            # 检查分配方案完整性
            missing = check_allocation_completeness(requirement, user_allocation)
            
            # 格式化消息
            message = format_missing_params_message(requirement, missing)

            # 构造返回结果
            result = {
                "requirement": {
                    "coin_long_pairs": requirement.coin_long_pairs,
                    "coin_short_pairs": requirement.coin_short_pairs,
                    "ai_time_long_types": requirement.ai_time_long_types,
                    "ai_time_short_types": requirement.ai_time_short_types,
                    "ai_time_id_mapping": requirement.ai_time_id_mapping,
                    "has_ai_time": requirement.has_ai_time
                },
                "missing": missing,
                "is_complete": not any(missing.values()),
                "message": message
            }

            return {
                "status": 1,
                "info": result
            }

        except BacktestRequestError as e:
            self.logger.error(f"分配方案完整性检查失败: {e.message}")
            return {
                "status": "error",
                "message": e.message,
                "error_code": e.error_code
            }

def main():
    """
    主函数，用于测试接口请求
    实际使用时通过引入模块调用
    """
    token = input("请输入用户 Token: ")
    requester = BacktestRequest(token)
    
    # 示例：获取策略组列表
    try:
        groups = requester.get_strategy_groups(search_val="风霆V4")
        print(json.dumps(groups, indent=2, ensure_ascii=False))

        # 示例：获取策略列表
        strategies = requester.get_strategies(search_val="风霆V4")
        print(json.dumps(strategies, indent=2, ensure_ascii=False))
    except BacktestRequestError as e:
        print(f"发生错误: {e.message}")

if __name__ == "__main__":
    main()