import sys
sys.path.append('/home/ubuntu/QuantClaw/skills/start-backtest')

from request import BacktestRequest
import json
import urllib.parse

def test_calc_margin():
    # 从用户输入获取 token
    token = input("请输入用户 Token: ")
    
    # 构造测试参数
    strategys_json = [
        {"id": 4929, "direction": "long", "multiple_num": 3, "ai_time_id": "-6", "coin": "DOGE"},
        {"id": 50594, "direction": "short", "multiple_num": 3, "ai_time_id": "-6", "coin": "BCH"},
        {"id": 50652, "direction": "short", "multiple_num": 3, "ai_time_id": "-6", "coin": "DOGE"},
        {"id": 50781, "direction": "long", "multiple_num": 3, "ai_time_id": "-4", "coin": "BCH"}
    ]
    
    leverage = 1.5
    long_pct = 90
    short_pct = 20
    
    long_coin_pcts = [
        {"coin": "DOGE", "pct": 50},
        {"coin": "BCH", "pct": 50}
    ]
    
    short_coin_pcts = [
        {"coin": "BCH", "pct": 50},
        {"coin": "DOGE", "pct": 50}
    ]
    
    long_ai_time_pcts = [
        {"ai_time_id": "-6", "pct": 50},
        {"ai_time_id": "-4", "pct": 50}
    ]
    
    short_ai_time_pcts = [
        {"ai_time_id": "-6", "pct": 100}
    ]
    
    # 初始化请求管理器
    requester = BacktestRequest(token)
    
    # 开启调试日志（可选）
    requester.DebugConfig.set_debug_mode(True)
    
    # 执行 calc_margin 方法
    result = requester.calc_margin(
        strategys_json=strategys_json,
        leverage=leverage,
        long_pct=long_pct,
        short_pct=short_pct,
        long_coin_pcts=long_coin_pcts,
        short_coin_pcts=short_coin_pcts,
        long_ai_time_pcts=long_ai_time_pcts,
        short_ai_time_pcts=short_ai_time_pcts
    )
    
    # 打印结果
    print("=== Margin Calculation Result ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    test_calc_margin()