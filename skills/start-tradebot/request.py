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
from typing import Dict, Any, Optional, List, Union

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
        
        # 尝试获取用户令牌，如果失败会在后续请求中抛出错误
        self.token = get_user_token_by_agent_id(agent_id)
        self.base_url = "https://www.fourieralpha.com/Mobile"
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
            print("usertoken=")
            print(self.token)
            # 添加用户token
            data['usertoken'] = self.token

            # 添加通用请求参数
            data.update({
                "app_v": "2.0.0",
                "lang": 1
            })

            # 发起请求
            response = requests.post(
                f"{self.base_url}/{endpoint}",
                json=data,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()

            # 检查接口返回状态
            if result.get("status") != 1:
                error_msg = result.get('msg', '未知错误')
                raise TradeRequestError(
                    f"接口请求失败: {error_msg}", 
                    "API_REQUEST_FAILED"
                )

            print(f"返回数据详细信息: {result}")
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
                "basic_unit": basic_unit
            }
            
            # 添加可选参数
            if multiple_num is not None:
                params["multiple_num"] = multiple_num
            if backtest_date:
                params["backtest_date"] = backtest_date
            if auto_redeem is not None:
                params["auto_redeem"] = 1 if auto_redeem else 0
            
            # 根据策略类型添加特定参数
            if strategy_type in [1, 2]:  # 现货/合约马丁
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
                    raise TradeRequestError("策略类型3必须提供initial_capital参数", "MISSING_STRATEGY_PARAMS")
                params["initial_capital"] = specific_params.get("initial_capital")
            
            elif strategy_type == 4:  # 策略类型4
                required_params = ["initial_capital", "trade_buy_type"]
                for param in required_params:
                    if param not in specific_params:
                        raise TradeRequestError(f"策略类型4必须提供{param}参数", "MISSING_STRATEGY_PARAMS")
                params.update({
                    "initial_capital": specific_params.get("initial_capital"),
                    "trade_buy_type": specific_params.get("trade_buy_type")
                })
            
            elif strategy_type == 5:  # 策略类型5
                required_params = ["initial_capital", "each_capital"]
                for param in required_params:
                    if param not in specific_params:
                        raise TradeRequestError(f"策略类型5必须提供{param}参数", "MISSING_STRATEGY_PARAMS")
                params.update({
                    "initial_capital": specific_params.get("initial_capital"),
                    "each_capital": specific_params.get("each_capital")
                })
            
            elif strategy_type == 8:  # 策略类型8
                required_params = ["trade_model", "trade_buy_type"]
                for param in required_params:
                    if param not in specific_params:
                        raise TradeRequestError(f"策略类型8必须提供{param}参数", "MISSING_STRATEGY_PARAMS")
                params.update({
                    "trade_model": specific_params.get("trade_model"),
                    "trade_buy_type": specific_params.get("trade_buy_type")
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

def cli_support():
    """
    为request.py添加命令行接口支持
    使用Typer框架实现
    """
    import json
    import sys

    app = typer.Typer()

    def create_requester(token: str):
        """创建TradeRequest实例"""
        return TradeRequest(token)

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
    def get_balance(
        token: str = typer.Option(..., help="UserToken"),
        account_id: str = typer.Option(..., help="交易所账户ID"),
        basic_unit: str = typer.Option("USDT", help="币本位/U本位"),
        coin: Optional[str] = typer.Option(None, help="币种"),
        strategy_id: Optional[str] = typer.Option(None, help="策略ID")
    ):
        """
        获取账户余额
        
        参数类型:
        - token: str (必填) - UserToken
        - account_id: str (必填) - 交易所账户ID
        - basic_unit: str (可选, 默认USDT) - 币本位/U本位
        - coin: Optional[str] (可选) - 币种
        - strategy_id: Optional[str] (可选) - 策略ID
        """
        requester = create_requester(token)
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
        multiple_num: Optional[float] = typer.Option(None, help="杠杆倍数"),
        backtest_date: Optional[str] = typer.Option(None, help="回测信号开启日期"),
        auto_redeem: bool = typer.Option(False, help="资金不足时是否自动赎回理财"),
        fst_capital: Optional[float] = typer.Option(None, help="初次下单金额"),
        each_capital: Optional[float] = typer.Option(None, help="加仓下单金额"),
        max_grid_size: Optional[int] = typer.Option(None, help="最大加仓次数"),
        initial_capital: Optional[float] = typer.Option(None, help="总投资金额"),
        trade_buy_type: Optional[str] = typer.Option(None, help="买入类型（market/limit）"),
        trade_model: Optional[str] = typer.Option(None, help="交易类型（all/long/short）")
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
        - multiple_num: Optional[float] (可选) - 杠杆倍数
        - backtest_date: Optional[str] (可选) - 回测信号开启日期
        - auto_redeem: bool (可选, 默认False) - 资金不足时是否自动赎回理财
        - 特定参数（根据不同策略类型）
        """
        requester = create_requester(agent_id)
        
        # 准备策略特定参数
        specific_params = {}
        if strategy_type in [1, 2]:  # 现货/合约马丁
            if fst_capital is not None:
                specific_params['fst_capital'] = fst_capital
            if each_capital is not None:
                specific_params['each_capital'] = each_capital
            if max_grid_size is not None:
                specific_params['max_grid_size'] = max_grid_size
        
        elif strategy_type == 3:  # 鲲鹏V1
            if initial_capital is not None:
                specific_params['initial_capital'] = initial_capital
        
        elif strategy_type == 4:  # 策略类型4
            if initial_capital is not None:
                specific_params['initial_capital'] = initial_capital
            if trade_buy_type is not None:
                specific_params['trade_buy_type'] = trade_buy_type
        
        elif strategy_type == 5:  # 策略类型5
            if initial_capital is not None:
                specific_params['initial_capital'] = initial_capital
            if each_capital is not None:
                specific_params['each_capital'] = each_capital
        
        elif strategy_type == 8:  # 策略类型8
            if trade_model is not None:
                specific_params['trade_model'] = trade_model
            if trade_buy_type is not None:
                specific_params['trade_buy_type'] = trade_buy_type
        
        result = requester.apply_trade_bot(
            strategy_id=strategy_id,
            strategy_type=strategy_type,
            name=name,
            account_id=account_id,
            trade_type=trade_type,
            basic_unit=basic_unit,
            multiple_num=multiple_num,
            backtest_date=backtest_date,
            auto_redeem=auto_redeem,
            **specific_params
        )
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))

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