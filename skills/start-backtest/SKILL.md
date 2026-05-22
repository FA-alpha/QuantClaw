# 回测启动与监控技能 - 策略组回测参数管理

## 🔍 回测参数分析接口（--check-allocation）

### 📊 接口功能
提供策略组或多策略回测时的参数需求分析，帮助Agent确定以下关键信息：

1. **回测包含的策略**
   - 策略ID列表
   - 每个策略的基本信息（币种、方向）

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