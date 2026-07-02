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
import os
import sys
import typer
from datetime import datetime
from typing import Dict, Any, Optional, List, Union, NamedTuple
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
        
        log_content = f"调用:start-backtest技能[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n"
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

class StrategyRequirement(NamedTuple):
    """策略分配需求"""
    coin_long_pairs: List[str]
    coin_short_pairs: List[str]
    ai_time_long_types: List[str]
    ai_time_short_types: List[str]
    ai_time_id_mapping: Dict[str, str]
    has_ai_time: bool

def check_allocation_iscomplete(
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

    def __init__(self, agent_id: Optional[str] = None):
        """
        初始化请求管理器
        :param agent_id: 当前Agent的ID（可选）
        :raises BacktestRequestError: 如果未提供有效的agent_id
        """
        # 移除原有的 if not token 检查
        # 改为更严格的令牌检查

        if agent_id is None or not isinstance(agent_id, str) or agent_id.strip() == "":
            raise BacktestRequestError(
            "未提供有效的agentid，请先获取agentid并传入",
            "INVALID_TOKEN"
            )
          # 尝试获取用户令牌，如果失败会在后续请求中抛出错误
        self.token = get_user_token_by_agent_id(agent_id)
        self.base_url = os.getenv("QUANTCLAW_API_BASE", "http://52.53.212.195:7002/Mobile")
        self.logger = logging.getLogger(__name__)
        self.agent_id = agent_id

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
            if "usertoken" not in data or not data["usertoken"]:
                data["usertoken"] = self.token
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

            # 如果开启调试模式，记录响应数据
            _log_network_request(self.agent_id, endpoint, data, result)

            # 检查接口返回状态
            if result.get("status") != 1:
                # 获取接口返回的所有参数
                error_details = json.dumps(result, ensure_ascii=False, indent=2)
                # 组合完整错误信息（使用全局配置的提示词）
                full_error_msg = f"{API_ERROR_PREFIX}\n\n📋 接口返回详情：\n{error_details}"
                raise BacktestRequestError(
                    full_error_msg, 
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
        agent_id: Optional[str] = None,
        page: int = 1, 
        limit: int = 10,
        search_val: Optional[str] = None,
        app_v: str = "2.0.0"
    ) -> Dict[str, Any]:
        """
        获取策略组列表
        
        :param agent_id: agentid,用于获取用户认证Token
        :param page: 页码，默认第一页
        :param limit: 每页数量，默认10个，全部传-1
        :param search_val: 搜索内容
        :param app_v: 应用版本号，默认2.0.0
        :return: 策略组列表
        """
        try:
            # 构造请求参数
            params: Dict[str, Any] = {
                "usertoken": get_user_token_by_agent_id(agent_id) or self.token,
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
        app_v: str = "2.0.0"
    ) -> Dict[str, Any]:
        """
        获取策略列表
        
        :param page: 页码，默认第一页
        :param limit: 每页数量，默认10个，返回全部的话传-1
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
                "app_v": app_v,
                "data_grade": 0,
                "show_type": 1
            }
            
            # 添加可选参数
            if search_val:
                params["search_val"] = search_val
            

            return self._make_request("Strategy/lists", params)
        except BacktestRequestError as e:
            self.logger.error(f"获取策略列表失败: {e.message}")
            return {
                "status": "error",
                "message": e.message,
                "error_code": e.error_code
            }
    def get_strategy_with_id(
        self, 
        strategy_id: str,
        page: int = 1, 
        limit: int = -1,
        app_v: str = "2.0.0"
    ) -> Dict[str, Any]:
        """
        根据传入的策略ID获取对应的策略详情
        
        :param strategy_id: 要查询的策略ID
        :param page: 页码，默认第一页
        :param limit: 每页数量，默认返回全部
        :param app_v: 应用版本号，默认2.0.0
        :return: 匹配的策略详情
        """
        try:
            # 获取完整的策略列表
            result = self.get_strategies(
                page=page, 
                limit=limit, 
                app_v=app_v
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
        
        except BacktestRequestError as e:
            self.logger.error(f"获取策略详情失败: {e.message}")
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
            # 转换 strategys_json 中的 ID 为字符串
            strategys_json_str = [
                {**strategy, "id": str(strategy["id"])} 
                for strategy in strategys_json
            ]
            
            # 构造请求参数
            params: Dict[str, Any] = {
                "strategys_json": json.dumps(strategys_json_str),
                "leverage": str(leverage),
                "long_pct": str(long_pct),
                "short_pct": str(short_pct),
                "long_coin_pcts": json.dumps(long_coin_pcts),
                "short_coin_pcts": json.dumps(short_coin_pcts),
                "app_v": app_v
            }
            
            # 可选参数处理
            if long_ai_time_pcts:
                # 确保 ai_time_pcts 只包含 ai_time_id 和 pct
                params["long_ai_time_pcts"] = json.dumps([
                    {
                        "ai_time_id": str(pct.get("ai_time_id", "-")),
                        "pct": pct["pct"]  # 保持原始数值，不转换为字符串
                    } for pct in long_ai_time_pcts
                ])
            
            if short_ai_time_pcts:
                # 确保 ai_time_pcts 只包含 ai_time_id 和 pct
                params["short_ai_time_pcts"] = json.dumps([
                    {
                        "ai_time_id": str(pct.get("ai_time_id", "-")),
                        "pct": pct["pct"]  # 保持原始数值，不转换为字符串
                    } for pct in short_ai_time_pcts
                ])

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
    def _remove_net_value(self, data: Any) -> Any:
        """
        递归删除所有 net_value 参数
        
        :param data: 待处理的数据
        :return: 处理后的数据
        """
        if isinstance(data, dict):
            # 创建新字典，排除 net_value
            return {k: self._remove_net_value(v) for k, v in data.items() if k != 'net_value'}
        elif isinstance(data, list):
            # 处理列表中的每个元素
            return [self._remove_net_value(item) for item in data]
        else:
            # 其他类型直接返回
            return data

    def get_backtest_stat_info(
        self, 
        back_id: str,
        app_v: str = "2.0.0"
    ) -> Dict[str, Any]:
        """
        获取回测统计信息
        
        :param back_id: 回测任务ID
        :param app_v: 应用版本号，默认2.0.0
        :return: 回测统计详情（已删除所有 net_value 参数）
        """
        try:
            if not back_id:
                raise BacktestRequestError("回测任务ID不能为空", "BACKTEST_ID_EMPTY")
            
            response = self._make_request("Backtrack/stat_info", {
                "back_id": back_id,
                "app_v": app_v
            })
            
            # 递归删除所有 net_value 参数
            return self._remove_net_value(response)
        except BacktestRequestError as e:
            self.logger.error(f"获取回测统计信息失败: {e.message}")
            return {
                "status": "error",
                "message": e.message,
                "error_code": e.error_code
            }

    def apply_backtest(
        self,
        agent_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        strategy_ids: Optional[List[str]] = None,
        bgn_date: Optional[str] = None,
        end_date: Optional[str] = None,
        init_balance: Optional[float] = None,
        leverage: Optional[float] = None,
        margin_mode: Optional[str] = None,
        margin_allocation: Optional[str] = None,
        data_type: int = 1,
        app_v: str = "2.0.0"
    ) -> Dict[str, Any]:
        """
        开始回测
        
        :param agent_id: agentid,用于获取用户认证Token
        :param strategy_id: 单个策略ID（兼容旧接口）
        :param strategy_ids: 多个策略ID列表
        :param bgn_date: 回测开始日期（YYYY-MM-DD）
        :param end_date: 回测结束日期（YYYY-MM-DD）
        :param init_balance: 初始资金
        :param leverage: 杠杆倍数
        :param margin_mode: 保证金模式（'exclusive' or 'shared'）
        :param margin_allocation: 保证金分配方案
        :param data_type: 数据类型（默认1）
        :param app_v: 应用版本号，默认2.0.0
        :return: 回测任务提交结果
        """
        try:
            # 处理策略ID
            if strategy_id:
                strategy_ids = [strategy_id]
            if not strategy_ids:
                raise BacktestRequestError("未指定策略ID", "NO_STRATEGY_SPECIFIED")

            # 构造请求参数
            params: Dict[str, Any] = {
                "usertoken": get_user_token_by_agent_id(agent_id) or self.token,
                "strategy_id": ",".join(strategy_ids),  # 逗号分隔的策略ID
                "data_type": str(data_type),
                "app_v": app_v
            }

            # 添加可选参数
            if bgn_date and end_date:
                import json as json_module
                date_lists = [{"bgn_date": bgn_date, "end_date": end_date}]
                params["date_lists"] = json_module.dumps(date_lists)

            if init_balance is not None:
                params["init_balance"] = str(init_balance)

            if leverage is not None:
                params["leverage"] = str(leverage)

            # 处理保证金模式
            if margin_mode:
                # 构造保证金模式配置
                import json as json_module
                margin_config = {
                    "is_shared_margin": (margin_mode == "shared"),
                    "global_margin_limit": init_balance or 10000
                }

                # 如果是共享模式且有保证金分配方案
                if margin_mode == "shared" and margin_allocation:
                    strategy_margin_limit = {}
                    allocations = margin_allocation.split(",")
                    for i, (sid, alloc) in enumerate(zip(strategy_ids, allocations)):
                        try:
                            actual_margin = float(alloc)
                            strategy_margin_limit[sid.strip()] = str(int(actual_margin))
                        except:
                            pass
                    margin_config["strategy_margin_limit"] = strategy_margin_limit

                params["margin_mode_config"] = json_module.dumps(margin_config)

            return self._make_request("Backtrack/apply_do", params)
        except BacktestRequestError as e:
            self.logger.error(f"回测任务提交失败: {e.message}")
            return {
                "status": "error",
                "message": e.message,
                "error_code": e.error_code
            }
    ##包装好的,用于根据策略组id,获取该策略组内所有策略的详细信息的方法
    def get_strategy_group_with_groupid(
        self, 
        group_id: str,
        limit: int = 10,
        app_v: str = "2.0.0"
    ) -> Dict[str, Any]:
        """
        根据策略组ID获取具体的策略组信息
        
        :param group_id: 策略组ID
        :param limit: 每页数量，默认10个
        :param app_v: 应用版本号，默认2.0.0
        :return: 策略组详情 或 错误信息
        """
        try:
            page = 1
            while page <= 10:  # 最多查询10页
                result = self.get_strategy_groups(
                    page=page, 
                    limit=limit, 
                    app_v=app_v
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

        except BacktestRequestError as e:
            self.logger.error(f"获取策略组详情失败: {e.message}")
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
        :raises BacktestRequestError: 参数不合法或获取策略失败时
        """
        # 参数校验
        if (strategy_ids is None and strategy_group_id is None) or \
           (strategy_ids is not None and strategy_group_id is not None):
            raise BacktestRequestError(
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
            missing = check_allocation_iscomplete(requirement, user_allocation)
            
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
        
        # print(f"❌ 未找到AgentID为 {agent_id} 的UserToken")
        return None
    
    except json.JSONDecodeError:
        print(f"❌ JSON解析错误: {users_file_path}")
        return None
    except Exception as e:
        print(f"❌ 获取UserToken时发生错误: {e}")
        return None
    

def cli_support():
    """
    为request.py添加命令行接口支持
    使用Typer框架实现
    """
    import json
    import sys
    from typing import Optional, List, Dict

    app = typer.Typer()

    def create_requester(agent_id: Optional[str] = None):
        """创建BacktestRequest实例"""
        return BacktestRequest(agent_id)

    @app.command()
    def get_strategy_groups(
        agent_id: str = typer.Option(..., help="当前机器人agentID"),
        page: int = typer.Option(1, help="页码"),
        limit: int = typer.Option(10, help="每页数量"),
        search: Optional[str] = typer.Option(None, help="搜索内容")
    ):
        """
        获取策略组列表
        
        参数类型:
        - agent_id: str (必填) - 该agent的id
        - page: int (可选, 默认1) - 页码
        - limit: int (可选, 默认10) - 每页数量
        - search: Optional[str] (可选) - 搜索内容
        
        功能: 查询并返回策略组列表，支持分页和搜索
        """
        requester = create_requester(agent_id)
        result = requester.get_strategy_groups(page=page, limit=limit, search_val=search)
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))

    @app.command()
    def get_strategies(
        agent_id: str = typer.Option(..., help="当前机器人agentID"),
        page: int = typer.Option(1, help="页码"),
        limit: int = typer.Option(10, help="每页数量"),
        search: Optional[str] = typer.Option(None, help="搜索内容")
    ):
        """
        获取策略列表
        
        参数类型:
        - agent_id: str (必填) - 该agent的id
        - page: int (可选, 默认1) - 页码
        - limit: int (可选, 默认10) - 每页数量
        - search: Optional[str] (可选) - 搜索内容
        
        功能: 查询并返回策略列表，支持分页和搜索
        """
        requester = create_requester(agent_id)
        result = requester.get_strategies(page=page, limit=limit, search_val=search)
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))

    @app.command()
    def get_strategy_with_id(
        agent_id: str = typer.Option(..., help="当前机器人agentID"),
        strategy_id: str = typer.Argument(..., help="策略ID")
    ):
        """
        获取指定ID的策略详情
        
        参数类型:
        - agent_id: str (必填) - agent_id
        - strategy_id: str (必填) - 要查询的策略ID
        
        功能: 根据策略ID精确查询策略详细信息
        """
        requester = create_requester(agent_id)
        result = requester.get_strategy_with_id(strategy_id)
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))

    @app.command()
    def get_strategy_group_with_groupid(
        agent_id: str = typer.Option(..., help="当前机器人agentID"),
        group_id: str = typer.Argument(..., help="策略组ID"),
        limit: int = typer.Option(10, help="每页数量")
    ):
        """
        根据策略组ID获取策略组详情
        
        参数类型:
        - agent_id: str (必填) - agent_id
        - group_id: str (必填) - 策略组ID
        - limit: int (可选, 默认10) - 每页数量
        
        功能: 精确查询特定ID的策略组信息
        """
        requester = create_requester(agent_id)
        result = requester.get_strategy_group_with_groupid(group_id, limit=limit)
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))

    @app.command()
    def apply_backtest(
        agent_id: str = typer.Option(..., help="当前机器人agentID"),
        strategy_ids: List[str] = typer.Option(..., help="策略ID列表"),
        bgn_date: Optional[str] = typer.Option(None, help="回测开始日期"),
        end_date: Optional[str] = typer.Option(None, help="回测结束日期"),
        init_balance: Optional[float] = typer.Option(None, help="初始资金"),
        leverage: Optional[float] = typer.Option(None, help="杠杆倍数"),
        margin_mode: Optional[str] = typer.Option(None, help="保证金模式"),
        margin_allocation: Optional[str] = typer.Option(None, help="保证金分配方案")
    ):
        """
        提交回测任务
        
        参数类型:
        - agent_id: str (必填) - agent_id
        - strategy_ids: List[str] (必填) - 策略ID列表
        - bgn_date: Optional[str] (可选) - 回测开始日期
        - end_date: Optional[str] (可选) - 回测结束日期
        - init_balance: Optional[float] (可选) - 初始资金
        - leverage: Optional[float] (可选) - 杠杆倍数
        - margin_mode: Optional[str] (可选) - 保证金模式
        - margin_allocation: Optional[str] (可选) - 保证金分配方案
        
        功能: 提交多策略回测任务
        """
        requester = create_requester(agent_id)
        result = requester.apply_backtest(
            strategy_ids=strategy_ids,
            bgn_date=bgn_date,
            end_date=end_date,
            init_balance=init_balance,
            leverage=leverage,
            margin_mode=margin_mode,
            margin_allocation=margin_allocation
        )
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))

    @app.command()
    def get_backtest_stat_info(
        agent_id: str = typer.Option(..., help="当前机器人agentID"),
        back_id: str = typer.Argument(..., help="回测任务ID")
    ):
        """
        获取回测统计信息
        
        参数类型:
        - agent_id: str (必填) - agent_id
        - back_id: str (必填) - 回测任务ID
        
        功能: 获取指定回测任务的详细统计信息
        """
        requester = create_requester(agent_id)
        result = requester.get_backtest_stat_info(back_id)
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))

    @app.command()
    def check_backtest_status(
        agent_id: str = typer.Option(..., help="当前机器人agentID"),
        back_id: str = typer.Argument(..., help="回测任务ID")
    ):
        """
        检查回测任务状态
        
        参数类型:
        - agent_id: str (必填) - agent_id
        - back_id: str (必填) - 回测任务ID
        
        功能: 查询指定回测任务的当前状态
        """
        requester = create_requester(agent_id)
        result = requester.check_backtest_status(back_id)
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))

    @app.command()
    def get_backtest_list(
        agent_id: str = typer.Option(..., help="当前机器人agentID"),
        page: int = typer.Option(1, help="页码"),
        limit: int = typer.Option(10, help="每页数量"),
        search: Optional[str] = typer.Option(None, help="搜索内容"),
        search_status: Optional[int] = typer.Option(None, help="状态筛选"),
        search_type: Optional[int] = typer.Option(None, help="类型筛选")
    ):
        """
        获取回测列表
        
        参数类型:
        - agent_id: str (必填) - 智能体的id
        - page: int (可选, 默认1) - 页码
        - limit: int (可选, 默认10) - 每页数量
        - search: Optional[str] (可选) - 搜索内容
        - search_status: Optional[int] (可选) - 状态筛选
        - search_type: Optional[int] (可选) - 类型筛选
        
        功能: 查询回测列表，支持多种筛选条件
        """
        requester = create_requester(agent_id)
        result = requester.get_backtest_list(
            page=page, 
            limit=limit, 
            search_val=search, 
            search_status=search_status, 
            search_type=search_type
        )
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))

    @app.command()
    def calc_margin(
        agent_id: str = typer.Option(..., help="当前机器人agentID"),
        strategys_json: str = typer.Option(..., help="策略JSON字符串"),
        leverage: float = typer.Option(..., help="保证金对应杠杆"),
        long_pct: float = typer.Option(..., help="做多保证金占比"),
        short_pct: float = typer.Option(..., help="做空保证金占比"),
        long_coin_pcts_json: str = typer.Option(..., help="做多币种保证金占比JSON"),
        short_coin_pcts_json: str = typer.Option(..., help="做空币种保证金占比JSON"),
        long_ai_time_pcts_json: Optional[str] = typer.Option(None, help="做多AI时间保证金占比JSON"),
        short_ai_time_pcts_json: Optional[str] = typer.Option(None, help="做空AI时间保证金占比JSON")
    ):
        """
        计算策略保证金
        
        参数类型:
        - agent_id: str (必填) - agentid
        - strategys_json: str (必填) - 策略JSON字符串
        - leverage: float (必填) - 保证金对应杠杆
        - long_pct: float (必填) - 做多保证金占比
        - short_pct: float (必填) - 做空保证金占比
        - long_coin_pcts_json: str (必填) - 做多币种保证金占比JSON
        - short_coin_pcts_json: str (必填) - 做空币种保证金占比JSON
        - long_ai_time_pcts_json: Optional[str] (可选) - 做多AI时间保证金占比JSON
        - short_ai_time_pcts_json: Optional[str] (可选) - 做空AI时间保证金占比JSON
        
        功能: 计算多策略回测的保证金分配详情
        """
        requester = create_requester(agent_id)
        
        try:
            strategys = json.loads(strategys_json)
            long_coin_pcts = json.loads(long_coin_pcts_json)
            short_coin_pcts = json.loads(short_coin_pcts_json)
            
            long_ai_time_pcts = json.loads(long_ai_time_pcts_json) if long_ai_time_pcts_json else None
            short_ai_time_pcts = json.loads(short_ai_time_pcts_json) if short_ai_time_pcts_json else None
        except json.JSONDecodeError:
            typer.echo("错误：JSON参数必须是有效的JSON格式")
            sys.exit(1)
        
        result = requester.calc_margin(
            strategys_json=strategys,
            leverage=leverage,
            long_pct=long_pct,
            short_pct=short_pct,
            long_coin_pcts=long_coin_pcts,
            short_coin_pcts=short_coin_pcts,
            long_ai_time_pcts=long_ai_time_pcts,
            short_ai_time_pcts=short_ai_time_pcts
        )
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))

    @app.command()
    def analyze_strategies_for_allocation(
        agent_id: str = typer.Option(..., help="当前机器人agentID"),
        strategy_ids: Optional[List[str]] = typer.Option(None, help="策略ID列表"),
        strategy_group_id: Optional[str] = typer.Option(None, help="策略组ID")
    ):
        """
        分析策略分配需求
        
        参数类型:
        - agent_id: str (必填) - 当前机器人agentID
        - strategy_ids: Optional[List[str]] (可选) - 策略ID列表
        - strategy_group_id: Optional[str] (可选) - 策略组ID
        
        功能: 分析策略的分配需求，用于多策略回测前的准备
        注意: 必须且仅能传入strategy_ids或strategy_group_id其中一个
        """
        requester = create_requester(agent_id)
        result = requester.analyze_strategies_for_allocation(
            strategy_ids=strategy_ids, 
            strategy_group_id=strategy_group_id
        )
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))

    @app.command()
    def check_allocation_completeness(
        agent_id: str = typer.Option(..., help="当前机器人agentID"),
        strategy_ids: Optional[List[str]] = typer.Option(None, help="策略ID列表"),
        strategy_group_id: Optional[str] = typer.Option(None, help="策略组ID"),
        user_allocation_json: Optional[str] = typer.Option(None, help="用户分配方案JSON")
    ):
        """
        检查保证金分配方案完整性
        
        参数类型:
        - agent_id: str (必填) - 当前机器人agentID
        - strategy_ids: Optional[List[str]] (可选) - 策略ID列表
        - strategy_group_id: Optional[str] (可选) - 策略组ID
        - user_allocation_json: Optional[str] (可选) - 用户分配方案JSON字符串
        
        功能: 检查多策略回测的保证金分配方案是否完整
        注意: 必须且仅能传入strategy_ids或strategy_group_id其中一个
        """
        requester = create_requester(agent_id)
        
        user_allocation = {}
        if user_allocation_json:
            try:
                user_allocation = json.loads(user_allocation_json)
            except json.JSONDecodeError:
                typer.echo("错误：user_allocation_json必须是有效的JSON格式")
                sys.exit(1)
        
        result = requester.check_allocation_completeness(
            strategy_ids=strategy_ids, 
            strategy_group_id=strategy_group_id,
            user_allocation=user_allocation
        )
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))

    # 运行 Typer CLI
    app()

def main():
    """
    主函数，用于测试接口请求
    实际使用时通过引入模块调用
    """
    pass

if __name__ == "__main__":
    cli_support()