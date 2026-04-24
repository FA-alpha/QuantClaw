# 策略类型说明

## 数据来源
- API: /Mobile/Extend/ai_strategy_lists
- 用户提供的策略分类信息

---

## 策略分类

### 马丁策略（Martingale）
所有包含"风霆"字样的策略

**策略列表**：
- 1 - 风霆现货
- 2 - 风霆合约
- 9 - 风霆合约V2
- 10 - 风霆合约V3
- 11 - 风霆V4

---

### 网格策略（Grid）
策略ID=7 及其版本

**策略列表**：
- 7 - 星辰
- 12 - 星辰V2

---

### 趋势策略（Trend）
鲲鹏系列策略

**策略列表**：
- 3 - 鲲鹏V1
- 4 - 鲲鹏V2
- 5 - 鲲鹏V3
- 8 - 鲲鹏V4

---

## 完整列表

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

---

## 使用说明

### 查询策略类型
```bash
python skills/backtest-query/query.py \
  --token xxx \
  --list-strategies
```

### 查询特定类型的回测
```bash
# 马丁策略示例（风霆现货）
python skills/backtest-query/query.py \
  --token xxx \
  --coin BTC \
  --strategy-type 1 \
  --year 2024 \
  --sort 2

# 网格策略示例（星辰）
python skills/backtest-query/query.py \
  --token xxx \
  --coin BTC \
  --strategy-type 7 \
  --year 2024 \
  --sort 2

# 趋势策略示例（鲲鹏V1）
python skills/backtest-query/query.py \
  --token xxx \
  --coin BTC \
  --strategy-type 3 \
  --year 2024 \
  --sort 2
```

---

## 更新日志

- 2024-04-24: 初始版本，记录策略分类（马丁/网格/趋势）
