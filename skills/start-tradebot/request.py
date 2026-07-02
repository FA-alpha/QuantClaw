#!/usr/bin/env python3
"""
QuantClaw 交易机器人请求统一管理模块

设计原则:
1. 标准方法传参
2. 明确的错误处理
3. 详细的代码注释
4. 友好的返回信息
5. 支持CLI方式调用
"""

import requests
import json
import logging
import os
import sys
import typer
from typing import Dict, Any, Optional, List, Union, NamedTuple
from datetime import datetime
from pathlib import Path

# ============================================
# 🔧 全局配置参数
# ============================================
# 是否开启接口请求日志记录
# True - 开启日志，所有接口请求和响应会写入 ~/.quantclaw/logs/{agent_id}/yyyy-mm-dd.log
# False - 关闭日志（默认）
ENABLE_DEBUG_LOG = True

# 接口请求失败时的固定提示词
# 当接口返回 status != 1 时，会在错误信息前显示此提示
API_ERROR_PREFIX = "⚠️ strangeError,接口请求失败，请停止当前操作并告知用户出错环节，等待用户指示。"
# ============================================

def _log_network_request(agent_id: str, api_name: str, request_params: Dict[str, Any], response_data: Optional[Dict[str, Any]] = None):
    """
    记录网络请求和响应日志（内部函数）
    
    :param agent_id: Agent ID
    :param api_name: 接口名称
    :param request_params: 请求参数
    :param response_data: 接口返回的数据
    """
    # 检查全局开关
    if not ENABLE_DEBUG_LOG:
        return

    try:
        # 创建日志目录：~/.quantclaw/logs/{agent_id}/
        log_base_dir = Path.home() / '.quantclaw' / 'logs' / agent_id
        log_base_dir.mkdir(parents=True, exist_ok=True)
        
        # 日志文件名：yyyy-mm-dd.log
        log_filename = datetime.now().strftime('%Y-%m-%d') + '.log'
        log_path = log_base_dir / log_filename
        
        log_content = f"调用:start-tradebot技能[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n"
        log_content += f"接口: {api_name}\n"
        log_content += f"请求参数: {request_params}\n"
        log_content += "---\n"
        if response_data is not None:
            log_content += f"返回参数: {response_data}\n"
        log_content += "\n"
        
        # 写入日志文件
        with open(log_path, 'a', encoding='utf-8') as log_file:
            log_file.write(log_content)
        
        # 打印日志路径（调试用）
        # print(f"🔍 日志已写入: {log_path}")
    except Exception as e:
        print(f"❌ 日志记录失败: {e}")

class TradeRequestError(Exception):
    """自定义异常类，用于标准化错误处理"""
    def __init__(self, message: str, error_code: Optional[str] = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class TradeRequest:
    
    """
    交易接口请求管理器
    
    提供标准化的接口请求方法，确保参数校验和错误处理
    """

    def __init__(self, agent_id: Optional[str] = None):
        """
        初始化请求管理器
        :param agent_id: 当前Agent的ID（可选）
        :raises TradeRequestError: 如果未提供有效的AgentID
        """
        if agent_id is None or not isinstance(agent_id, str) or agent_id.strip() == "":
            raise TradeRequestError(
                "未提供有效的agentid，请先获取agentid并传入",
                "INVALID_AGENT_ID"
            )
        
        # 保存 agent_id 用于日志记录
        self.agent_id = agent_id
        
        # 尝试获取用户令牌，如果失败会在后续请求中抛出错误

        self.token = get_user_token_by_agent_id(agent_id)
        self.base_url = os.getenv("QUANTCLAW_API_BASE", "http://52.53.212.195:7002/Mobile")
        self.logger = logging.getLogger(__name__)

    def _validate_params(self, params: Dict[str, Any]) -> None:
        """
        通用参数校验方法
        
        :param params: 待校验的参数字典
        :raises TradeRequestError: 参数校验失败时抛出
        """
        for key, value in params.items():
            if value is None:
                raise TradeRequestError(f"参数 {key} 不能为空", "PARAM_MISSING")

    def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        统一接口请求方法
        
        :param endpoint: 接口端点
        :param data: 请求参数
        :return: 解析后的接口响应
        :raises TradeRequestError: 请求失败时抛出
        """
        # 通用参数校验
        self._validate_params(data)

        try:
            # 添加用户token
            data['usertoken'] = self.token

            # 添加通用请求参数
            data.update({
                "app_v": "2.0.0",
                "lang": 1
            })

            # 如果开启调试模式，记录网络请求日志
            _log_network_request(self.agent_id, endpoint, data)

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
                # 获取接口返回的所有参数
                error_details = json.dumps(result, ensure_ascii=False, indent=2)
                # 组合完整错误信息（使用全局配置的提示词）
                full_error_msg = f"{API_ERROR_PREFIX}\n\n📋 接口返回详情：\n{error_details}"
                raise TradeRequestError(
                    full_error_msg, 
                    "API_REQUEST_FAILED"
                )

            # 如果开启调试模式，记录响应数据
            _log_network_request(self.agent_id, endpoint, data, result)
            return result

        except requests.RequestException as e:
            raise TradeRequestError(
                f"网络请求异常: {str(e)}", 
                "NETWORK_ERROR"
            )

    def get_exchange_lists(
        self, 
        page: int = 1, 
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        获取交易所账户列表
        
        :param page: 第几页（默认第一页）
        :param limit: 每页几个（默认10个,若获取全部则传-1）
        :return: 交易所账户列表
        """
        try:
            params = {
                "page": page,
                "limit": limit
            }

            return self._make_request("User/exchange_lists", params)
        except TradeRequestError as e:
            self.logger.error(f"获取交易所账户列表失败: {e.message}")
            return {
                "status": "error",
                "message": e.message,
                "error_code": e.error_code
            }

    def get_strategy_lists(
        self, 
        page: int = 1, 
        limit: int = -1,
        search_val: Optional[str] = None,
        show_type: Optional[int] = 1,  # 默认有效策略
        data_grade: Optional[int] = 0   # 默认所有策略
    ) -> Dict[str, Any]:
        """
        获取策略列表
        
        :param page: 第几页（默认第一页）
        :param limit: 每页几个（默认-1,代表查询全部）
        :param search_val: 搜索内容
        :param show_type: 显示类型（1-有效策略 2-历史策略）
        :param data_grade: 数据代次（0-所有策略 1-老策略 2=新策略）
        :return: 策略列表
        """
        try:
            params: Dict[str, Any] = {
                "page": page,
                "limit": limit,
                "show_type": show_type,
                "data_grade": data_grade
            }
            
            # 添加可选参数
            if search_val:
                params["search_val"] = search_val

            return self._make_request("Strategy/lists", params)
        except TradeRequestError as e:
            self.logger.error(f"获取策略列表失败: {e.message}")
            return {
                "status": "error",
                "message": e.message,
                "error_code": e.error_code
            }

    def get_balance(
        self, 
        account_id: str,
        basic_unit: str = "USDT",
        coin: Optional[str] = None,
        strategy_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取账户余额
        
        :param account_id: 交易所账户ID
        :param basic_unit: 币本位/U本位（USD-币本位 USDT-U本位）
        :param coin: 币种
        :param strategy_id: 策略ID，用于判断是现货还是合约
        :return: 账户余额信息
        """
        try:
            params: Dict[str, Any] = {
                "account_id": account_id,
                "basic_unit": basic_unit
            }
            
            # 添加可选参数
            if coin:
                params["coin"] = coin
            if strategy_id:
                params["strategy_id"] = strategy_id

            return self._make_request("Trade/balance_do", params)
        except TradeRequestError as e:
            self.logger.error(f"获取账户余额失败: {e.message}")
            return {
                "status": "error",
                "message": e.message,
                "error_code": e.error_code
            }

    def apply_trade_bot(
        self,
        strategy_id: str,
        strategy_type: int,
        name: str,
        account_id: str,
        trade_type: int = 1,  # 默认模拟盘
        multiple_num: Optional[float] = None,
        basic_unit: str = "USDT",
        margin_mode: str = "cross",
        backtest_date: Optional[str] = None,
        auto_redeem: Optional[bool] = None,
        **specific_params
    ) -> Dict[str, Any]:
        """
        添加交易机器人
        
        :param strategy_id: 策略记录ID
        :param strategy_type: 策略类型
        :param name: 名称
        :param account_id: 交易所账户ID
        :param trade_type: 交易类型（1-模拟盘 2-实盘）
        :param multiple_num: 杠杆倍数
        :param basic_unit: 币本位/U本位（USD-币本位 USDT-U本位）
        :param margin_mode: 逐仓/全仓模式(cross-全仓 isolated-逐仓)
        :param backtest_date: 回测信号开启日期
        :param auto_redeem: 资金不足时是否自动赎回理财
        :param specific_params: 策略特定参数
        :return: 交易机器人创建结果
        """
        try:
            params: Dict[str, Any] = {
                "strategy_id": strategy_id,
                "name": name,
                "account_id": account_id,
                "trade_type": trade_type,
                "basic_unit": basic_unit,
                "margin_mode": margin_mode
            }
            
            # 添加可选参数
            if multiple_num is not None:
                params["multiple_num"] = multiple_num
            if backtest_date:
                params["backtest_date"] = backtest_date
            if auto_redeem is not None:
                params["auto_redeem"] = 1 if auto_redeem else 0
            
            # 根据策略类型添加特定参数
            if strategy_type in [1, 2, 11]:  # 现货/合约马丁
                required_params = ["fst_capital", "each_capital", "max_grid_size"]
                for param in required_params:
                    if param not in specific_params:
                        raise TradeRequestError(f"策略类型{strategy_type}必须提供{param}参数", "MISSING_STRATEGY_PARAMS")
                params.update({
                    "fst_capital": specific_params.get("fst_capital"),
                    "each_capital": specific_params.get("each_capital"),
                    "max_grid_size": specific_params.get("max_grid_size")
                })
            
            elif strategy_type == 3:  # 鲲鹏V1
                if "initial_capital" not in specific_params:
                    raise TradeRequestError(f"策略类型{strategy_type}必须提供initial_capital参数", "MISSING_STRATEGY_PARAMS")
                params["initial_capital"] = specific_params.get("initial_capital")
            
            elif strategy_type == 4:  # 策略类型4
                required_params = ["initial_capital", "trade_buy_type"]
                for param in required_params:
                    if param not in specific_params:
                        raise TradeRequestError(f"策略类型{strategy_type}必须提供{param}参数", "MISSING_STRATEGY_PARAMS")
                params.update({
                    "initial_capital": specific_params.get("initial_capital"),
                    "trade_buy_type": specific_params.get("trade_buy_type")
                })
            
            elif strategy_type == 5:  # 策略类型5
                required_params = ["initial_capital", "each_capital"]
                for param in required_params:
                    if param not in specific_params:
                        raise TradeRequestError(f"策略类型{strategy_type}必须提供{param}参数", "MISSING_STRATEGY_PARAMS")
                params.update({
                    "initial_capital": specific_params.get("initial_capital"),
                    "each_capital": specific_params.get("each_capital")
                })
            
            elif strategy_type == 7:  # 星辰V1
                if "extend" not in specific_params:
                    raise TradeRequestError(f"策略类型{strategy_type}必须提供extend参数", "MISSING_STRATEGY_PARAMS")
                params["extend"] = specific_params.get("extend")
            
            elif strategy_type == 8:  # 策略类型8
                required_params = ["trade_model", "trade_buy_type", "initial_capital"]
                for param in required_params:
                    if param not in specific_params:
                        raise TradeRequestError(f"策略类型{strategy_type}必须提供{param}参数", "MISSING_STRATEGY_PARAMS")
                params.update({
                    "trade_model": specific_params.get("trade_model"),
                    "trade_buy_type": specific_params.get("trade_buy_type"),
                    "initial_capital": specific_params.get("initial_capital")
                })
            elif strategy_type in [25, 28]:
                required_params = ["initial_capital"]
                for param in required_params:
                    if param not in specific_params:
                        raise TradeRequestError(f"策略类型{strategy_type}必须提供{param}参数", "MISSING_STRATEGY_PARAMS")
                params.update({
                    "initial_capital": specific_params.get("initial_capital"),
                })
            else:
                required_params = [""]
            return self._make_request("Trade/apply_do", params)
        except TradeRequestError as e:
            self.logger.error(f"添加交易机器人失败: {e.message}")
            return {
                "status": "error",
                "message": e.message,
                "error_code": e.error_code
            }
    def get_strategy_groups(
        self, 
        agent_id: Optional[str] = None,
        page: int = 1, 
        limit: int = -1,
        search_val: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取策略组列表
        
        :param agent_id: agentid,用于获取用户认证Token
        :param page: 页码，默认第一页
        :param limit: 每页数量，默认10个，全部传-1
        :param search_val: 搜索内容
        :return: 策略组列表
        """
        try:
            # 构造请求参数
            params: Dict[str, Any] = {
                "usertoken": get_user_token_by_agent_id(agent_id) or self.token,
                "page": page,
                "limit": limit,
                "app_v": "2.0.0"
            }
            
            # 添加搜索参数
            if search_val:
                params["search_val"] = search_val

            return self._make_request("Strategy/group_lists", params)
        except TradeRequestError as e:
            self.logger.error(f"获取策略组失败: {e.message}")
            return {
                "status": "error",
                "message": e.message,
                "error_code": e.error_code
            }
    def get_strategy_with_id(
        self, 
        strategy_id: str,
        page: int = 1, 
        limit: int = -1
    ) -> Dict[str, Any]:
        """
        根据传入的策略ID获取对应的策略详情
        
        :param strategy_id: 要查询的策略ID
        :param page: 页码，默认第一页
        :param limit: 每页数量，默认返回全部
        :return: 匹配的策略详情
        """
        try:
            # 获取完整的策略列表
            result = self.get_strategy_lists(
                page=page, 
                limit=limit
            )
            
            # 检查返回状态
            if result.get("status") != 1:
                # 添加全局错误提示词
                error_details = json.dumps(result, ensure_ascii=False, indent=2)
                return {
                    "status": "error",
                    "message": f"{API_ERROR_PREFIX}\n\n📋 接口返回详情：\n{error_details}",
                    "error_code": "API_REQUEST_FAILED"
                }
            
            # 获取策略列表
            all_strategies = result.get("info", [])
            
            # 筛选出匹配的策略
            matched_strategies = [
                strategy for strategy in all_strategies
                if str(strategy.get("id")) == str(strategy_id)
            ]
            
            # 如果没有找到任何匹配的策略，返回错误信息
            if not matched_strategies:
                return {
                    "status": "error",
                    "message": f"未找到指定的策略ID: {strategy_id}",
                    "error_code": "STRATEGY_NOT_FOUND"
                }
            
            # 返回匹配的策略(只返回第一个)
            return {
                "status": 1,
                "info": matched_strategies[0]
            }
        
        except TradeRequestError as e:
            self.logger.error(f"获取策略详情失败: {e.message}")
            return {
                "status": "error",
                "message": e.message,
                "error_code": e.error_code
            }
    ##包装好的,用于根据策略组id,获取该策略组内所有策略的详细信息的方法
    def get_strategy_group_with_groupid(
        self, 
        group_id: str,
        agent_id: str
    ) -> Dict[str, Any]:
        """
        根据策略组ID获取具体的策略组信息
        
        :param group_id: 策略组ID
        :agent_id: 智能体的ID,用于接口内部获取usertoken
        :return: 策略组详情 或 错误信息
        """
        try:
            page = 1
            while page <= 10:  # 最多查询10页
                result = self.get_strategy_groups(
                    agent_id=agent_id,
                    page=page, 
                    limit= -1, 
                    app_v= "2.0.0"
                )

                # 检查返回状态
                if result.get("status") != 1:
                    # 添加全局错误提示词
                    error_details = json.dumps(result, ensure_ascii=False, indent=2)
                    return {
                        "status": "error",
                        "message": f"{API_ERROR_PREFIX}\n\n📋 接口返回详情：\n{error_details}",
                        "error_code": "API_REQUEST_FAILED"
                    }

                # 获取策略组列表
                strategy_groups = result.get("info", [])
                
                # 查找匹配的策略组
                for group in strategy_groups:
                    if str(group.get("id")) == str(group_id):
                        return {
                            "status": 1,
                            "info": group
                        }

                # 检查是否是最后一页
                is_end = result.get("url", {}).get("is_end") == 1
                if is_end:
                    break

                page += 1

            # 未找到策略组
            return {
                "status": "error",
                "message": f"未找到ID为 {group_id} 的策略组",
                "error_code": "GROUP_NOT_FOUND"
            }

        except TradeRequestError as e:
            self.logger.error(f"获取策略组详情失败: {e.message}")
            return {
                "status": "error",
                "message": e.message,
                "error_code": e.error_code
            }
    class StrategyRequirement(NamedTuple):
        """策略分配需求"""
        coin_long_pairs: List[str]
        coin_short_pairs: List[str]
        ai_time_long_types: List[str]
        ai_time_short_types: List[str]
        ai_time_id_mapping: Dict[str, str]
        has_ai_time: bool
    ##检查并分析策略需要哪些参数,传入的可能是策略组id,也可能是多个策略的id数组,之所以是多个策略(策略组的策略的id数组),是因为可能用户将一个原有的策略组减少了策略
    ## ,或者利用回测的策略组的信息的方式去获取原有的一个完整的策略组的策略列表
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
        :raises BacktestRequestError: 参数不合法或获取策略失败时
        """
        # 参数校验
        if (strategy_ids is None and strategy_group_id is None) or \
           (strategy_ids is not None and strategy_group_id is not None):
            raise TradeRequestError(
                "必须且仅能传入 strategy_ids 或 strategy_group_id 其中一个", 
                "INVALID_STRATEGY_PARAMS"
            )

        try:
            # 根据传入参数选择获取策略的方法
            if strategy_ids:
                strategies_info = []
                for sid in strategy_ids:
                    strategy_info = self.get_strategy_with_id(strategy_id=sid)
                    if strategy_info.get("status") == "error":
                        return strategy_info
                    strategies_info.extend(strategy_info.get("info", []))
            
            elif strategy_group_id:
                group_result = self.get_strategy_group_with_groupid(strategy_group_id)
                if group_result.get("status") == "error":
                    return group_result
                
                group_info = group_result.get("info", {})
                strategies_info = group_info.get("strategy_lists", [])

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

        except TradeRequestError as e:
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
            requirement = self.StrategyRequirement(
                coin_long_pairs=requirement_info.get("coin_long_pairs", []),
                coin_short_pairs=requirement_info.get("coin_short_pairs", []),
                ai_time_long_types=requirement_info.get("ai_time_long_types", []),
                ai_time_short_types=requirement_info.get("ai_time_short_types", []),
                ai_time_id_mapping=requirement_info.get("ai_time_id_mapping", {}),
                has_ai_time=requirement_info.get("has_ai_time", False)
            )

            # 检查分配方案完整性
            missing = self.check_allocation_iscomplete(requirement, user_allocation)
            
            # 格式化消息
            message = self.format_missing_params_message(requirement, missing)

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

        except TradeRequestError as e:
            self.logger.error(f"分配方案完整性检查失败: {e.message}")
            return {
                "status": "error",
                "message": e.message,
                "error_code": e.error_code
            }
    def check_allocation_iscomplete(
        self, 
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
        self, 
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
def cli_support():
    """
    为request.py添加命令行接口支持
    使用Typer框架实现
    """
    import json
    import sys

    app = typer.Typer()

    def create_requester(agent_id: str):
        """创建TradeRequest实例"""
        return TradeRequest(agent_id)

    @app.command()
    def get_exchange_lists(
        agent_id: str = typer.Option(..., help="agent_id"),
        page: int = typer.Option(1, help="页码"),
        limit: int = typer.Option(10, help="每页数量")
    ):
        """
        获取交易所账户列表
        
        参数类型:
        - agent_id: str (必填) - agent_id
        - page: int (可选, 默认1) - 页码
        - limit: int (可选, 默认10) - 每页数量
        """
        requester = create_requester(agent_id)
        result = requester.get_exchange_lists(page, limit)
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))

    @app.command()
    def get_strategy_lists(
        agent_id: str = typer.Option(..., help="agent_id"),
        page: int = typer.Option(1, help="页码"),
        limit: int = typer.Option(-1, help="每页数量"),
        search_val: Optional[str] = typer.Option(None, help="搜索内容"),
        show_type: int = typer.Option(1, help="显示类型（1-有效策略 2-历史策略）"),
        data_grade: int = typer.Option(0, help="数据代次（0-所有策略 1-老策略 2=新策略）")
    ):
        """
        获取策略列表
        
        参数类型:
        - agent_id: str (必填) - agent_id
        - page: int (可选, 默认1) - 页码
        - limit: int (可选, 默认-1代表查询全部) - 每页数量
        - search_val: Optional[str] (可选) - 搜索内容
        - show_type: int (可选, 默认1) - 显示类型
        - data_grade: int (可选, 默认0) - 数据代次
        """
        requester = create_requester(agent_id)
        result = requester.get_strategy_lists(
            page=page, 
            limit=limit, 
            search_val=search_val, 
            show_type=show_type, 
            data_grade=data_grade
        )
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))
    
    @app.command()
    def get_strategy_with_id(
        agent_id: str = typer.Option(..., help="agent_id"),
        strategy_id: str = typer.Argument(..., help="策略ID")
    ):
        """
        根据策略ID获取策略详情
        
        参数类型:
        - agent_id: str (必填) - agent_id
        - strategy_id: str (必填) - 策略ID
        """
        requester = create_requester(agent_id)
        result = requester.get_strategy_with_id(strategy_id)
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))
    
    @app.command()
    def get_strategy_groups(
        agent_id: str = typer.Option(..., help="agent_id"),
        page: int = typer.Option(1, help="页码"),
        limit: int = typer.Option(10, help="每页数量"),
        search_val: Optional[str] = typer.Option(None, help="搜索内容")
    ):
        """
        获取策略组列表
        
        参数类型:
        - agent_id: str (必填) - agent_id
        - page: int (可选, 默认1) - 页码
        - limit: int (可选, 默认10) - 每页数量
        - search_val: Optional[str] (可选) - 搜索内容
        """
        requester = create_requester(agent_id)
        result = requester.get_strategy_groups(
            page=page,
            limit=limit,
            search_val=search_val
        )
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))
    
    @app.command()
    def get_strategy_group_with_groupid(
        agent_id: str = typer.Option(..., help="agent_id"),
        group_id: str = typer.Argument(..., help="策略组ID"),
        limit: int = typer.Option(10, help="每页数量")
    ):
        """
        根据策略组ID获取策略组详情
        
        参数类型:
        - agent_id: str (必填) - agent_id
        - group_id: str (必填) - 策略组ID
        - limit: int (可选, 默认10) - 每页数量
        """
        requester = create_requester(agent_id)
        result = requester.get_strategy_group_with_groupid(group_id, limit=limit)
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))

    @app.command()
    def get_balance(
        agent_id: str = typer.Option(..., help="agent_id"),
        account_id: str = typer.Option(..., help="交易所账户ID"),
        basic_unit: str = typer.Option("USDT", help="币本位/U本位"),
        coin: Optional[str] = typer.Option(None, help="币种"),
        strategy_id: Optional[str] = typer.Option(None, help="策略ID")
    ):
        """
        获取账户余额
        
        参数类型:
        - agent_id: str (必填) - agent_id
        - account_id: str (必填) - 交易所账户ID
        - basic_unit: str (可选, 默认USDT) - 币本位/U本位
        - coin: Optional[str] (可选) - 币种
        - strategy_id: Optional[str] (可选) - 策略ID
        """
        requester = create_requester(agent_id)
        result = requester.get_balance(
            account_id=account_id,
            basic_unit=basic_unit,
            coin=coin,
            strategy_id=strategy_id
        )
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))

    @app.command()
    def apply_trade_bot(
        agent_id: str = typer.Option(..., help="agent_id"),
        strategy_id: str = typer.Option(..., help="策略记录ID"),
        strategy_type: int = typer.Option(..., help="策略类型"),
        name: str = typer.Option(..., help="机器人名称"),
        account_id: str = typer.Option(..., help="交易所账户ID"),
        trade_type: int = typer.Option(1, help="交易类型（1-模拟盘 2-实盘）"),
        basic_unit: str = typer.Option("USDT", help="币本位/U本位"),
        margin_mode: str = typer.Option("cross", help="逐仓/全仓模式(cross-全仓 isolated-逐仓)"),
        multiple_num: Optional[float] = typer.Option(None, help="杠杆倍数"),
        backtest_date: Optional[str] = typer.Option(None, help="回测信号开启日期"),
        auto_redeem: bool = typer.Option(False, help="资金不足时是否自动赎回理财"),
        fst_capital: Optional[float] = typer.Option(None, help="初次下单金额"),
        each_capital: Optional[float] = typer.Option(None, help="加仓下单金额"),
        max_grid_size: Optional[int] = typer.Option(None, help="最大加仓次数"),
        initial_capital: Optional[float] = typer.Option(None, help="总投资金额"),
        trade_buy_type: Optional[str] = typer.Option(None, help="买入类型（market/limit）"),
        trade_model: Optional[str] = typer.Option(None, help="交易类型（all/long/short）"),
        extend: Optional[str] = typer.Option(None, help="扩展参数（JSON格式，用于type=7星辰V1）")
    ):
        """
        添加交易机器人
        
        参数类型:
        - agent_id: str (必填) - agent_id
        - strategy_id: str (必填) - 策略记录ID
        - strategy_type: int (必填) - 策略类型
        - name: str (必填) - 机器人名称
        - account_id: str (必填) - 交易所账户ID
        - trade_type: int (可选, 默认1) - 交易类型
        - basic_unit: str (可选, 默认USDT) - 币本位/U本位
        - margin_mode: str (可选, 默认cross全仓) - 仓位模式逐仓/全仓
        - multiple_num: Optional[float] (可选) - 杠杆倍数
        - backtest_date: Optional[str] (可选) - 回测信号开启日期
        - auto_redeem: bool (可选, 默认False) - 资金不足时是否自动赎回理财
        - 特定参数（根据不同策略类型）
        """
        requester = create_requester(agent_id)
        
        # 准备策略特定参数
        specific_params = {}
        if strategy_type in [1, 2, 11]:  # 现货/合约马丁/风霆V4
            if fst_capital is not None:
                specific_params['fst_capital'] = fst_capital
            if each_capital is not None:
                specific_params['each_capital'] = each_capital
            if max_grid_size is not None:
                specific_params['max_grid_size'] = max_grid_size
        
        elif strategy_type == 3:  # 鲲鹏V1
            if initial_capital is not None:
                specific_params['initial_capital'] = initial_capital
        
        elif strategy_type == 4:  # 鲲鹏V1
            if initial_capital is not None:
                specific_params['initial_capital'] = initial_capital
            if trade_buy_type is not None:
                specific_params['trade_buy_type'] = trade_buy_type
        
        elif strategy_type == 5:  # 鲲鹏V3
            if initial_capital is not None:
                specific_params['initial_capital'] = initial_capital
            if each_capital is not None:
                specific_params['each_capital'] = each_capital
        
        elif strategy_type == 7:  # 星辰V1
            if extend is not None:
                try:
                    # 解析 JSON 字符串为字典
                    specific_params['extend'] = json.loads(extend)
                except json.JSONDecodeError:
                    print("❌ extend 参数必须是有效的JSON格式")
                    raise typer.Exit(code=1)
        
        elif strategy_type == 8:  # 鲲鹏V4
            if trade_model is not None:
                specific_params['trade_model'] = trade_model
            if trade_buy_type is not None:
                specific_params['trade_buy_type'] = trade_buy_type
            if initial_capital is not None:
                specific_params['initial_capital'] = initial_capital
        elif strategy_type in [25,28]: #反脆弱V1,V2
            if initial_capital is not None:
                specific_params['initial_capital'] = initial_capital

        result = requester.apply_trade_bot(
            strategy_id=strategy_id,
            strategy_type=strategy_type,
            name=name,
            account_id=account_id,
            trade_type=trade_type,
            basic_unit=basic_unit,
            margin_mode=margin_mode,
            multiple_num=multiple_num,
            backtest_date=backtest_date,
            auto_redeem=auto_redeem,
            **specific_params
        )
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))
    
    @app.command()
    def calc_investment(
        max_grid_size: int = typer.Option(..., help="最大加仓次数"),
        add_amt_multiples: float = typer.Option(1.0, help="加仓倍数（默认1.0）"),
        fst_capital: Optional[float] = typer.Option(None, help="初次下单金额"),
        each_capital: Optional[float] = typer.Option(None, help="加仓下单金额"),
        total_investment: Optional[float] = typer.Option(None, help="总投资金额")
    ):
        """
        智能计算投资金额参数
        
        支持场景：
        1. 提供 fst_capital + each_capital → 计算 total_investment
        2. 提供 total_investment → 计算 fst_capital + each_capital
        3. 提供 total_investment + fst_capital → 计算 each_capital
        4. 提供 total_investment + each_capital → 计算 fst_capital
        
        ⚠️ 当 add_amt_multiples != 1 时，必须提供 each_capital
        """
        try:
            result = calculate_investment_smart(
                fst_capital=fst_capital,
                each_capital=each_capital,
                max_grid_size=max_grid_size,
                add_amt_multiples=add_amt_multiples,
                total_investment=total_investment
            )
            typer.echo(json.dumps(result, indent=2, ensure_ascii=False))
        except ValueError as e:
            typer.echo(json.dumps({'error': str(e)}, indent=2, ensure_ascii=False))
            raise typer.Exit(code=1)
        
    # 运行 Typer CLI
    app()
    

def calculate_investment_smart(
    fst_capital: Optional[float] = None,
    each_capital: Optional[float] = None,
    max_grid_size: Optional[int] = None,
    add_amt_multiples: float = 1.0,
    total_investment: Optional[float] = None
) -> Dict[str, float]:
    """
    智能计算投资金额参数（双向计算）
    
    根据传入参数自动判断计算方向：
    1. 提供 fst_capital, each_capital → 计算 total_investment
    2. 提供 total_investment → 计算 fst_capital, each_capital (假设两者相等)
    3. 提供 total_investment, fst_capital → 计算 each_capital
    4. 提供 total_investment, each_capital → 计算 fst_capital
    
    ⚠️ 当 add_amt_multiples != 1 时，必须提供 fst_capital 和 each_capital
    
    :param fst_capital: 初次下单金额
    :param each_capital: 加仓下单金额（第一次加仓）
    :param max_grid_size: 最大加仓次数
    :param add_amt_multiples: 加仓倍数（默认1.0）
    :param total_investment: 总投资金额
    :return: 包含所有参数的字典
    """
    from decimal import Decimal, getcontext
    
    # 设置精度
    getcontext().prec = 100000
    
    # 参数验证
    if max_grid_size is None or max_grid_size <= 0:
        raise ValueError("max_grid_size 必须大于0")
    
    # ⚠️ 关键限制：当 add_amt_multiples != 1 时，必须提供 each_capital
    # fst_capital 虽然可以传入，但不参与计算（成为无效参数）
    if add_amt_multiples != 1.0:
        if each_capital is None:
            raise ValueError("当 add_amt_multiples != 1 时，必须提供 each_capital（加仓保证金）")
        
        # 只能正向计算 total_investment，fst_capital 不参与计算
        if each_capital > 0:
            # 递增加仓计算（fst_capital 不参与）
            amt_count = Decimal(str(each_capital))
            now_amt = Decimal(str(each_capital))
            
            for i in range(1, int(max_grid_size) + 1):
                if i == 1:
                    amt_count = amt_count + now_amt
                else:
                    now_amt = now_amt * Decimal(str(add_amt_multiples))
                    amt_count = amt_count + now_amt
            
            total_investment = float(amt_count)
        else:
            total_investment = 0.0
        
        return {
            'fst_capital': fst_capital,  # 传入但不参与计算
            'each_capital': each_capital,
            'max_grid_size': max_grid_size,
            'add_amt_multiples': add_amt_multiples,
            'total_investment': total_investment
        }
    
    # 以下是 add_amt_multiples == 1 的场景（支持双向计算）
    
    # 场景1：已知 fst_capital 和 each_capital，计算 total_investment
    if fst_capital is not None and each_capital is not None and total_investment is None:
        if each_capital > 0 and fst_capital > 0:
            # 等额加仓
            a = Decimal(str(fst_capital))
            b = Decimal(str(each_capital))
            c = Decimal(str(int(max_grid_size)))
            total_investment = float(a + (b * c))
        else:
            total_investment = 0.0
        
        return {
            'fst_capital': fst_capital,
            'each_capital': each_capital,
            'max_grid_size': max_grid_size,
            'add_amt_multiples': add_amt_multiples,
            'total_investment': total_investment
        }
    
    # 场景2：已知 total_investment，fst_capital 和 each_capital 都为 None
    # 假设 fst_capital = each_capital，反推金额
    elif total_investment is not None and fst_capital is None and each_capital is None:
        # 等额加仓：total = fst + (each * n)
        # 假设 fst = each，则：total = each * (1 + n)
        each_capital = total_investment / (1 + max_grid_size)
        fst_capital = each_capital
        
        return {
            'fst_capital': fst_capital,
            'each_capital': each_capital,
            'max_grid_size': max_grid_size,
            'add_amt_multiples': add_amt_multiples,
            'total_investment': total_investment
        }
    
    # 场景3：已知 total_investment 和 fst_capital，计算 each_capital
    elif total_investment is not None and fst_capital is not None and each_capital is None:
        # total = fst + (each * n) → each = (total - fst) / n
        each_capital = (total_investment - fst_capital) / max_grid_size
        
        return {
            'fst_capital': fst_capital,
            'each_capital': each_capital,
            'max_grid_size': max_grid_size,
            'add_amt_multiples': add_amt_multiples,
            'total_investment': total_investment
        }
    
    # 场景4：已知 total_investment 和 each_capital，计算 fst_capital
    elif total_investment is not None and each_capital is not None and fst_capital is None:
        # total = fst + (each * n) → fst = total - (each * n)
        fst_capital = total_investment - (each_capital * max_grid_size)
        
        return {
            'fst_capital': fst_capital,
            'each_capital': each_capital,
            'max_grid_size': max_grid_size,
            'add_amt_multiples': add_amt_multiples,
            'total_investment': total_investment
        }
    
    else:
        raise ValueError("参数组合无效，请提供有效的参数组合")


def get_user_token_by_agent_id(agent_id: str) -> Optional[str]:
    """
    根据传入的AgentID获取对应的UserToken
    
    使用方式：
    USERTOKEN=$(cat ~/.quantclaw/users.json | jq -r --arg agent_id "当前机器人agentID" '.users[] | select(.agentId == $agent_id) | .token')
    
    :param agent_id: 机器人的AgentID
    :return: UserToken字符串，如果未找到返回None
    """
    try:
        # 确保使用绝对路径
        users_file_path = os.path.expanduser("~/.quantclaw/users.json")
        
        # 检查文件是否存在
        if not os.path.exists(users_file_path):
            print(f"❌ 用户配置文件不存在: {users_file_path}")
            return None
        
        # 读取并解析JSON文件
        with open(users_file_path, 'r') as f:
            users_data = json.load(f)
        
        # 遍历用户列表查找匹配的AgentID
        for user in users_data.get('users', []):
            if user.get('agentId') == agent_id:
                return user.get('token')
        
        print(f"❌ 未找到AgentID为 {agent_id} 的UserToken")
        return None
    
    except json.JSONDecodeError:
        print(f"❌ JSON解析错误: {users_file_path}")
        return None
    except Exception as e:
        print(f"❌ 获取UserToken时发生错误: {e}")
        return None
    
    
def main():
    """
    主函数，用于测试接口请求
    实际使用时通过引入模块调用
    """
    pass

if __name__ == "__main__":
    cli_support()