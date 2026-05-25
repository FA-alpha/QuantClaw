import sys
import os
sys.path.append('/home/ubuntu/QuantClaw/skills/start-backtest')

from request import BacktestRequest, enable_network_debug_log

def test_calc_margin():
    # 获取用户 Token
    token = input("请输入用户 Token: ")
    
    # 设置调试日志（使用测试的 AgentID）
    enable_network_debug_log(agent_id="888999")
    
    # 构造测试参数
    strategys_json = [
        {"id": 4929, "direction": "long", "multiple_num": 3, "ai_time_id": "-6", "coin": "DOGE"},
        {"id": 50594, "direction": "short", "multiple_num": 3, "ai_time_id": "-6", "coin": "BCH"}
    ]
    
    # 初始化请求管理器
    requester = BacktestRequest(token, agent_id="888999")
    
    # 执行 calc_margin 方法
    result = requester.calc_margin(
        strategys_json=strategys_json,
        leverage=1.5,
        long_pct=90,
        short_pct=20,
        long_coin_pcts=[{"coin": "DOGE", "pct": 50}, {"coin": "BCH", "pct": 50}],
        short_coin_pcts=[{"coin": "BCH", "pct": 50}, {"coin": "DOGE", "pct": 50}]
    )
    
    print("=== Margin Calculation Result ===")
    print(result)

if __name__ == "__main__":
    test_calc_margin()