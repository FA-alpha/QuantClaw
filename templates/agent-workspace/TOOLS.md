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

## 回测数据查询（backtest-query）

### 缓存机制 ✅

**币种列表、策略类型、时间ID 已自动缓存到内存中**

- 首次查询时自动获取并缓存
- 所有用户共享同一份缓存（全局数据）
- 无需手动查询，直接使用即可

### 策略分类规则

| 识别条件 | 策略类型 | 示例 |
|---------|---------|------|
| 名称含"风霆" | 马丁策略 | 风霆马丁 |
| strategy_type=7 | 网格策略（唯一） | 天阙网格 |
| 其他所有 | 趋势策略 | 鲲鹏趋势 |

### 使用流程

```
用户提问 → Agent 读取缓存 → 构造查询 → 返回结果
```

**注意**：
- 缓存在 Gateway 运行期间持久存在
- 如需刷新数据，重启 Gateway 或调用清除缓存方法
- 详细配置见：`skills/backtest-query/defaults.py`

---

Add whatever helps you do your job. This is your cheat sheet.
