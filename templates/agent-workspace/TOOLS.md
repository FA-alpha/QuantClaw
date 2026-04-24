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

## 策略类型速查表

| ID | 名称 | 策略类型 |
|----|------|---------|
| 1  | 风霆现货 | 马丁策略 |
| 2  | 风霆合约 | 马丁策略 |
| 3  | 鲲鹏V1 | 趋势策略 |
| 4  | 鲲鹏V2 | 趋势策略 |
| 5  | 鲲鹏V3 | 趋势策略 |
| 7  | 星辰 | 网格策略 |
| 8  | 鲲鹏V4 | 趋势策略 |
| 9  | 风霆合约V2 | 马丁策略 |
| 10 | 风霆合约V3 | 马丁策略 |
| 11 | 风霆V4 | 马丁策略 |
| 12 | 星辰V2 | 网格策略 |

**记忆规则**：
- 风霆 → 马丁策略
- 星辰 (ID=7/12) → 网格策略
- 鲲鹏 → 趋势策略

详细说明：`memory/strategy_types.md`

---

Add whatever helps you do your job. This is your cheat sheet.
