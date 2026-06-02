#!/usr/bin/env python3
import json
import logging
import requests
from request import TradeRequest

# 开启详细日志
logging.basicConfig(level=logging.DEBUG)

def test_get_strategies():
    # 使用你提供的信息
    agent_id = "qc-4fc82b26aecb"
    
    try:
        # 创建 TradeRequest 实例
        trade_request = TradeRequest(agent_id=agent_id)
        
        # 调用 get_strategy_lists 方法
        result = trade_request.get_strategy_lists(
            page=1, 
            limit=-1,
            search_val=""
        )
        
        # 打印返回的完整结果
        print("\n返回结果类型:", type(result))
        print("完整返回结果:", json.dumps(result, indent=2, ensure_ascii=False))
        
        # 如果是字典，打印其中的列表
        if isinstance(result, dict):
            strategies = result.get('info', [])
            print("\n策略列表长度:", len(strategies))
            print("策略列表:", json.dumps(strategies, indent=2, ensure_ascii=False))
            
            # 打印更多详细信息
            print("\n额外返回信息:")
            print("status:", result.get('status'))
            print("url:", result.get('url'))
    
    except Exception as e:
        print("发生错误:", e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_get_strategies()