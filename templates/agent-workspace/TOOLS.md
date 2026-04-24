# TOOLS.md - Local Notes

Skills define *how* tools work. This file is for *your* specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:
- Preferred data sources
- API endpoints
- Custom indicators
- Strategy templates
- Anything environment-specific

## Examples

```markdown
### Data Sources
- Binance API - Primary market data
- CoinGecko - Price aggregation

### Custom Indicators
- RSI_EMA_Combo - RSI + EMA crossover signal

### Strategy Templates
- Grid Trading - Multi-level buy/sell orders
- DCA - Dollar cost averaging setup
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

## 策略分类规则（通过名称识别）

**⚠️ 策略 ID 列表是动态的，使用前先查询 API**

```bash
python skills/backtest-query/query.py --token xxx --list-strategies
```

### 分类规则

| 识别条件 | 策略类型 |
|---------|---------|
| 名称含"风霆" | 马丁策略 |
| strategy_type=7 | 网格策略（唯一） |
| 其他所有 | 趋势策略 |

**使用方法**：
1. 先获取策略列表
2. 根据规则判断策略类型
3. 使用 strategy_type ID 进行查询

详细说明：`memory/strategy_types.md`

---

Add whatever helps you do your job. This is your cheat sheet.
