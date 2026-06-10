# leverage_bot.py 设计文档

## 📋 功能

查询机器人杠杆率统计。支持按状态、交易所、品种等维度筛选。默认只看运行中。

---

## 🔌 API

**端点**: `POST /TradeStat/leverage_ratio`

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `usertoken` | str | ✅ | 用户 token |
| `search_status` | int | ❌ | 1=实盘 2=模拟 3=已停止；默认不传=全部 |
| `search_val` | str | ❌ | 搜索机器人名称 |
| `search_exchange` | str | ❌ | 交易所 ID，多个逗号分隔 |
| `search_amt_type` | int | ❌ | 1=现货 2=合约；不传=全部 |
| `strategy_type` | int | ❌ | 策略类型 ID；传 0=全部 |
| `account_id` | int | ❌ | 交易所账号 ID；传 0=全部 |
| `search_direction` | str | ❌ | `long`=做多, `short`=做空；不传=全部 |

> ⚠️ 与 `Trade/lists` 的区别：无 `page/limit/sort`（聚合统计）。

### 返回字段

```
amt_info:
  total_amt         总金额

leverage_info:
  nominal_invest_total                名义总投资
  nominal_invest_total_exposure       名义总投资(exposure)
  actual_invest_total                 实际总投资
  used_margin                         已用保证金
  used_margin_pct                     已用保证金占比(%)
  available_margin                    可用保证金
  available_margin_pct                可用保证金占比(%)
  nominal_leverage                    名义杠杆
  real_leverage                       实际杠杆率
  real_leverage_exposure              实际杠杆率方向(long/short)
  dir_exposure                        方向暴露(long/short)
  scale_exposure                      暴露比例

usdt_assets[]:                        各币种明细
  symbol                              币种
  nominal_invest_total                投资总额
  current_position                    当前总仓位
```

---

## 🎛️ 筛选参数

| 用户概念 | CLI 参数 | API 参数 |
|---------|---------|---------|
| 运行状态 | `--status` | `search_status`（默认 running） |
| 交易所 | `--exchange-ids` | `search_exchange` |
| 交易品种 | `--amt-type` | `search_amt_type` |
| 策略类型 | `--strategy-type` | `strategy_type` |
| 账号 | `--account-id` | `account_id` |
| 合约方向 | `--direction` | `search_direction` |
| 名称 | `--search` | `search_val` |
| 币种 | `--coin` | (合并到 search_val) |

---

## 💻 CLI 接口

```bash
# 查看所有运行中机器人的杠杆率
cd skills/trade-bot && python3 scripts/trade_bot.py leverage --agent-id qc-xxx

# 筛选
python3 scripts/trade_bot.py leverage --agent-id qc-xxx --amt-type futures --direction long
python3 scripts/trade_bot.py leverage --agent-id qc-xxx --exchange-ids 1,3
python3 scripts/trade_bot.py leverage --agent-id qc-xxx --status all
```

---

## 📤 输出格式

```json
{
  "status": "ok",
  "total_amt": 50000,
  "leverage": {
    "actual_invest_total": 15000,
    "used_margin": 8000,
    "used_margin_pct": 53.3,
    "available_margin": 7000,
    "available_margin_pct": 46.7,
    "nominal_leverage": 2.0,
    "real_leverage": 1.5,
    "real_leverage_exposure": "long",
    "dir_exposure": "long",
    "scale_exposure": 60
  },
  "assets": [...],
  "filters": {
    "status": "running",
    "exchange_ids": null,
    "amt_type": "all",
    "direction": "all"
  }
}
```

---

## 🚨 Agent 使用规则

1. **无需确认**：`leverage` 是 🟢 只读操作
2. **默认只看运行中**：`--status running`（默认），传 `all` 看全部
3. **筛选参数**：status / exchange-ids / amt-type / strategy-type / account-id / direction / search / coin
4. **典型场景**：
   - "看看杠杆率" → `python3 scripts/trade_bot.py leverage --agent-id qc-xxx`
   - "合约做多的杠杆" → `--amt-type futures --direction long`
   - "币安的杠杆" → 先查 exchange-list → `--exchange-ids <id>`
   - "所有状态的" → `--status all`