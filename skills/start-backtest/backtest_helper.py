#!/usr/bin/env python3
"""
QuantClaw 回测助手
简单、可靠的回测脚本，直接使用正确的 API 格式
"""

import json
import sys
import requests
from datetime import datetime, timedelta

API_BASE = "https://www.fourieralpha.com/Mobile"

def backtest(
    token: str,
    strategy_ids: list[str],
    bgn_date: str,
    end_date: str,
    margin_mode: str = "exclusive",
    margin_allocation: list[float] = None,
    init_balance: int = 10000,
) -> dict:
    """
    执行回测
    
    Args:
        token: 用户 token
        strategy_ids: 策略 ID 列表
        bgn_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        margin_mode: 保证金模式 (exclusive/shared)
        margin_allocation: 共享模式分配比例列表（可以超过100%）
        init_balance: 初始保证金（global_margin_limit）
    
    Returns:
        dict: API 响应
    """
    data = {
        "usertoken": token,
        "data_type": "1",
        "strategy_id": ",".join(strategy_ids),
    }
    
    # 日期格式：JSON 数组
    date_lists = [{"bgn_date": bgn_date, "end_date": end_date}]
    data["date_lists"] = json.dumps(date_lists)
    
    # 初始资金
    if init_balance:
        data["init_balance"] = str(init_balance)
    
    # 保证金模式配置
    margin_config = {
        "is_shared_margin": (margin_mode == "shared"),
        "global_margin_limit": init_balance,
    }
    
    # 共享模式：添加每个策略的保证金分配
    # 注意：保证金比例总和可以超过100%
    # 每个策略的保证金金额 = 比例 * 保证金总额 / 100
    # 单个策略保证金不能超过保证金总额
    if margin_mode == "shared" and margin_allocation and len(margin_allocation) == len(strategy_ids):
        strategy_margin_limit = {}
        for sid, alloc in zip(strategy_ids, margin_allocation):
            actual_margin = int(alloc * init_balance / 100)
            # 单个策略保证金不能超过保证金总额
            if actual_margin > init_balance:
                actual_margin = init_balance
            strategy_margin_limit[sid] = str(actual_margin)
        margin_config["strategy_margin_limit"] = strategy_margin_limit
    
    data["margin_mode_config"] = json.dumps(margin_config)
    
    try:
        resp = requests.post(
            f"{API_BASE}/Backtrack/apply_do",
            data=data,
            timeout=60
        )
        resp.raise_for_status()
        result = resp.json()
        return result
    except Exception as e:
        return {"status": 0, "info": str(e)}


def main():
    if len(sys.argv) < 2:
        print("用法: python backtest_helper.py <token> [策略IDs] [选项]")
        print()
        print("选项:")
        print("  --shared                共享保证金模式")
        print("  --allocation 60,40,50   共享模式分配比例（可超过100%）")
        print("  --start 2024-01-01      开始日期")
        print("  --end 2024-12-31        结束日期")
        print("  --balance 10000         初始保证金（默认10000）")
        print()
        print("说明：")
        print("  - 保证金比例总和可以超过100%（如 60%+40%+50%=150%）")
        print("  - 每个策略保证金 = 比例 * 保证金总额 / 100")
        print("  - 单个策略保证金不能超过保证金总额")
        return
    
    token = sys.argv[1]
    
    # 解析参数
    strategy_ids = []
    margin_mode = "exclusive"
    margin_allocation = None
    bgn_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")
    init_balance = 10000
    
    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        
        if arg.startswith("-") or arg.startswith("--"):
            if arg == "--shared":
                margin_mode = "shared"
            elif arg == "--allocation":
                i += 1
                margin_allocation = [float(x) for x in sys.argv[i].split(",")]
            elif arg == "--start":
                i += 1
                bgn_date = sys.argv[i]
            elif arg == "--end":
                i += 1
                end_date = sys.argv[i]
            elif arg == "--balance":
                i += 1
                init_balance = int(sys.argv[i])
        else:
            # 策略 ID
            for sid in arg.split(","):
                strategy_ids.append(sid.strip())
        
        i += 1
    
    if not strategy_ids:
        print("错误: 需要提供策略 ID")
        return
    
    # 执行回测
    result = backtest(
        token=token,
        strategy_ids=strategy_ids,
        bgn_date=bgn_date,
        end_date=end_date,
        margin_mode=margin_mode,
        margin_allocation=margin_allocation,
        init_balance=init_balance,
    )
    
    if result.get("status") == 1:
        back_id = result.get("info", {}).get("back_id")
        print(f"✅ 回测已提交")
        print(f"   回测ID: {back_id}")
        print(f"   策略: {','.join(strategy_ids)}")
        print(f"   时间: {bgn_date} ~ {end_date}")
        print(f"   保证金模式: {'共享' if margin_mode == 'shared' else '独占'}")
        if margin_mode == "shared" and margin_allocation:
            total_alloc = sum(margin_allocation)
            print(f"   分配比例: {','.join([str(x) for x in margin_allocation])} (总和: {total_alloc}%)")
            # 计算各策略保证金
            for sid, alloc in zip(strategy_ids, margin_allocation):
                actual_margin = int(alloc * init_balance / 100)
                print(f"     {sid}: {alloc}% → {actual_margin}")
        if init_balance != 10000:
            print(f"   初始保证金: {init_balance}")
    else:
        print(f"❌ 回测失败: {result.get('info')}")


if __name__ == "__main__":
    main()
