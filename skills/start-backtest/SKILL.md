# 启动回测 - 策略组/多策略回测参数管理

## 🔍 回测参数分析接口（--check-allocation）

### 📊 接口功能
提供策略组或多策略回测时的参数需求分析，帮助Agent确定以下关键信息：

1. **回测包含的策略**
   - 策略ID列表
   - 每个策略的基本信息（币种、方向、AI时间）

2. **保证金分配需求**
   - 需要分配的币种（做多/做空）
   - 是否需要AI时间参数
   - AI时间类型映射

### 🚨 调用示例

#### 策略组回测参数分析
```bash
python backtest_monitor.py \
  --check-allocation \
  --strategy-group-id "策略组ID" \
  --token <token>
```

#### 多策略回测参数分析
```bash
python backtest_monitor.py \
  --check-allocation \
  --strategy-ids "策略ID1,策略ID2,策略ID3" \
  --token <token>
```

### 🔑 返回参数详解

#### 返回结果示例：
```json
{
  "requirement": {
    "coin_long_pairs": ["BTC", "DOGE"],
    "coin_short_pairs": ["SOL", "BTC"],
    "ai_time_long_types": ["2025年震荡", "最近1年"],
    "ai_time_short_types": ["2025年趋势"],
    "ai_time_id_mapping": {
      "2025年震荡": "-6",
      "最近1年": "365",
      "2025年趋势": "-12"
    },
    "has_ai_time": true
  },
  "missing": {
    "coin_long_allocation": true,
    "coin_short_allocation": true,
    "ai_time_long_allocation": true,
    "ai_time_short_allocation": true
  },
  "is_complete": false,
  "strategies": [
    {
      "id": "4637",
      "name": "BTC震荡做多策略",
      "coin": "BTC",
      "direction": "做多",
      "ai_time_name": "2025年震荡",
      "ai_time_id": "-6"
    },
    {
      "id": "4638", 
      "name": "DOGE突破策略",
      "coin": "DOGE", 
      "direction": "做多",
      "ai_time_name": "最近1年",
      "ai_time_id": "365"
    }
  ]
}
```

### 🎯 参数定义

#### 币种分配需求 
- `coin_long_pairs`：需要分配的做多币种列表
- `coin_short_pairs`：需要分配的做空币种列表

#### AI时间分配需求
- `ai_time_long_types`：需要分配的做多AI时间类型列表
- `ai_time_short_types`：需要分配的做空AI时间类型列表
- `ai_time_id_mapping`：AI时间类型到ID的映射
- `has_ai_time`：是否包含AI时间参数

### 🚨 重要规则

1. 只有策略组和多策略共享保证金模式才需要分配参数
2. 单策略回测不支持保证金分配
3. 分配比例总和最多100%，可以小于100%

### 🔍 使用建议

- 优先使用 `--strategy-group-id`
- 当无法获取策略组ID时，使用 `--strategy-ids`
- 总是携带 `--token` 参数

## 💡 Agent处理流程

1. 调用 `--check-allocation` 获取参数需求
2. 分析返回的 `is_complete` 状态
3. 如果未完成，询问用户进行参数分配
4. 使用 `start.py` 的 `--calc-margin` 计算分配方案

## 🚨 策略组/多策略回测规则

### 📋 支持的场景

**1. 单个策略组回测**
- 可以删除部分策略
- 不能新增组外策略

**2. 多个独立策略回测**
- 可以组合不同的独立策略
- 不能跨策略组选择策略

**3. 保证金模式**
- 独占模式：每个策略独立使用保证金
- 共享模式：策略共享保证金池，需要分配参数

### 🔧 参数分配原则

**共享保证金模式参数分配**
- 支持任意比例分配
- 可配置币种做多/做空占比
- 可配置AI时间类型占比

**分配规则示例**
```bash
# 币种分配
--coin-long-allocation '{"BTC": 40, "DOGE": 30, "SOL": 30}'
--coin-short-allocation '{"BTC": 50, "SOL": 50}'

# AI时间分配
--ai-time-long-allocation '{"2025年震荡": 60, "最近1年": 40}'
--ai-time-short-allocation '{"2025年趋势": 100}'
```

## 🚨 注意事项

- 每次回测都是独立任务
- 不复用历史参数
- 必须在当前对话中询问所有必要参数

## 📋 完整示例

**策略组回测**
```bash
# 步骤1：分析参数需求
python backtest_monitor.py \
  --check-allocation \
  --strategy-group-id "131" \
  --token "$TOKEN"

# 步骤2：计算保证金
python start.py \
  --calc-margin \
  --strategy-ids "1,2,3,4" \
  --coin-long-allocation '{"BTC": 30, "DOGE": 30}' \
  --coin-short-allocation '{"BCH": 80, "DOGE": 20}' \
  --total-balance 10000 \
  --leverage 1.5

# 步骤3：执行回测
python start.py \
  --apply \
  --strategy-ids "1,2,3,4" \
  --margin-mode shared \
  --margin-allocation "3000,2000,3000,2000"
```

## 🚫 禁止的行为

- 不要自动补充默认值
- 不要猜测未明确的参数
- 不要跨对话复用参数
- 不要在回测完成后主动询问结果

## 📈 返回格式

```
✅ 回测已提交
   回测ID: xxxx
   策略: xxx/xxx/xxxx xxxx-做多
   时间范围: YYYY-MM-DD ~ YYYY-MM-DD
   保证金模式: xx

**回测已开始执行，请等待完成。**
```

## 🔀 版本历史

- 2026-05-22: 优化策略组回测参数分析接口
- 2026-05-21: 增加多策略分配规则