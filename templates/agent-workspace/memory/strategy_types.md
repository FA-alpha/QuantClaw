# 策略类型分类规则

## 重要说明

**策略类型列表是动态的**，具体有哪些策略需要通过 API 获取：

```bash
python skills/backtest-query/query.py --token xxx --list-strategies
```

本文档**只记录分类规则**，不列举具体策略 ID。

---

## 分类规则

### 马丁策略（Martingale）
**识别方法**：策略名称包含"**风霆**"字样

**特征**：
- 名称示例：风霆现货、风霆合约、风霆合约V2、风霆V4 等
- 所有版本都属于马丁策略

---

### 网格策略（Grid）
**识别方法**：**只有 strategy_type=7**

**特征**：
- 只有 ID=7 的策略是网格策略
- 其他策略即使名称相似也不是网格策略

---

### 趋势策略（Trend）
**识别方法**：策略名称包含"**鲲鹏**"字样

**特征**：
- 名称示例：鲲鹏V1、鲲鹏V2、鲲鹏V3、鲲鹏V4 等
- 所有版本都属于趋势策略

---

## 使用流程

### 1. 获取策略列表
```bash
python skills/backtest-query/query.py \
  --token xxx \
  --list-strategies
```

**返回示例**：
```
AI 回测策略:
  [1] 风霆现货 (id: 1)      → 马丁策略
      - 风霆现货 v1.0 (版本: 1.0, 杠杆: 1)
  [7] 星辰 (id: 7)          → 网格策略
      - 星辰 v1.0 (版本: 1.0, 杠杆: 1)
  [3] 鲲鹏V1 (id: 3)        → 趋势策略
      - 鲲鹏V1 v1.0 (版本: 1.0, 杠杆: 1)
```

### 2. 判断策略类型
- 名称含"风霆" → 马丁策略
- strategy_type=7 → 网格策略（唯一）
- 其他所有策略 → 趋势策略

### 3. 查询特定策略的回测
```bash
# 使用 strategy_type 查询
python skills/backtest-query/query.py \
  --token xxx \
  --coin BTC \
  --strategy-type <ID> \
  --year 2024 \
  --sort 2
```

---

## 更新日志

- 2024-04-24: 初始版本，记录策略分类规则（通过名称识别）
