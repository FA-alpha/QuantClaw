# 高级查询（特定策略类型）

## 适用场景

- 用户明确指定了策略类型（风霆/鲲鹏/网格等）
- 需要找该策略类型的"最佳"策略
- 需要对不确定参数进行多次尝试

## 典型问题

- "BTC做多风霆v4比较好的策略"
- "BTC做多风霆v4的组合"
- "ETH网格策略的组合"
- "给我推荐几个鲲鹏策略"

---

## 🎯 核心思路

当用户指定了策略类型但要求"比较好的"或"组合"时：

1. **识别确定参数**：币种、方向、策略类型名称
2. **查询策略列表**：确定 strategy_type 和可用版本
3. **多参数尝试**：年份、排序、版本等不确定参数
4. **合并结果**：去重、综合评分、分组展示
5. **创建组合**：选出优秀策略并创建组合

---

## 📊 参数识别

### 三层参数

| 层次 | 说明 | 示例 |
|-----|-----|-----|
| 用户明确的 | 直接来自用户描述 | BTC, 做多, 风霆v4 |
| API确定的 | 需查询才知道 | strategy_type=?, version=? |
| 完全不确定的 | 未指定且有多种可能 | 年份, 排序, search_pct |

### 用户："BTC做多风霆v4的组合"

```
第1层 - 用户明确:
  ✅ 币种 = BTC
  ✅ 方向 = 做多
  ✅ 策略名称 = 风霆v4

第2层 - API确定:
  ❓ strategy_type = ?（查询 --list-strategies）
  ❓ version = ?（可能有多个版本）
      ↓ 查询后发现
  ✅ strategy_type = 11
  ❓ version = 4.0, 4.1, 4.2（有3个！）

第3层 - 完全不确定:
  ❓ 年份 (2024? 2023?)
  ❓ 排序 (收益率? 夏普率?)
```

---

## 🔄 处理流程

### 步骤 1：查询策略列表

```bash
python query.py --token xxx --list-strategies
```

确定：
- strategy_type ID
- 有哪些版本

### 步骤 2：灵活决策

发现多个版本时：
- **选项A**：每个版本都查（全面）
- **选项B**：只查最新版本（快速）
- **选项C**：查最新 + 旧版本（平衡）✅ 推荐

### 步骤 3：多维度查询

```bash
# 不确定参数的组合

for version in [最新, 旧版本]:
  for year in [2024, 2023]:
    for sort in [2, 3]:  # 收益率、夏普率
      python query.py --token xxx \
        --coin BTC \
        --strategy-type 11 \
        --version {version} \
        --direction long \
        --year {year} \
        --sort {sort} \
        --limit 5
```

### 步骤 4：合并结果

1. **去重**：根据 `strategy_token`
2. **综合评分**：`sharpe * 0.4 + year_rate * 0.3 - max_loss * 0.3`
3. **分组展示**：按年份/指标分组

### 步骤 5：创建组合

```bash
python query.py --token xxx \
  --create-group \
  --group-name "BTC做多风霆v4组合" \
  --strategy-tokens "st_xxx,st_yyy,st_zzz"
```

---

## 🎯 实例：风霆v4组合

### 完整流程

```bash
# 1. 查策略列表
python query.py --token xxx --list-strategies | grep 风霆
# 输出：[11] 风霆V4 (v4.0, v4.1, v4.2)

# 2. 多参数查询
# 2024年 × 收益率 × v4.2
python query.py --token xxx \
  --coin BTC --strategy-type 11 --version 4.2 \
  --direction long --year 2024 --sort 2 --limit 5

# 2024年 × 夏普率 × v4.2
python query.py --token xxx \
  --coin BTC --strategy-type 11 --version 4.2 \
  --direction long --year 2024 --sort 3 --limit 5

# 2023年 × 收益率 × v4.0（历史验证）
python query.py --token xxx \
  --coin BTC --strategy-type 11 --version 4.0 \
  --direction long --year 2023 --sort 2 --limit 5

# 3. 合并去重，选出3-5个

# 4. 创建组合
python query.py --token xxx \
  --create-group \
  --group-name "BTC做多风霆v4组合" \
  --strategy-tokens "st_a,st_b,st_c"
```

---

## 📊 结果展示建议

```
为您找到 BTC 做多风霆v4 策略的优选结果：

【2024年 - 按收益率】
1. 策略A | 年化 45% | 夏普 2.1 | 回撤 12%
2. 策略B | 年化 38% | 夏普 2.5 | 回撤 8%

【2024年 - 按夏普率】
1. 策略C | 年化 32% | 夏普 2.8 | 回撤 6%

【2023年 - 历史验证】
1. 策略B | 年化 35% | 夏普 2.3 | 回撤 9%

💡 综合推荐：
- 激进型：策略A（高收益）
- 稳健型：策略C（高夏普低回撤）
- 经验证：策略B（连续两年表现优秀）
```

---

## 🔍 用户需求模糊时的通用策略

### 参数探索原则

| 不确定维度 | 探索策略 |
|-----------|---------|
| 时间范围 | 尝试多个年份（2024、2023），验证稳定性 |
| 评价标准 | 尝试多种排序（收益率、夏普率），覆盖不同偏好 |
| 策略版本 | 如有多版本，都查询比较 |
| 参数配置 | 如 search_pct，尝试常用值 |

### 查询数量建议

- 单次查询：`--limit 5~10`
- 查询轮数：2~4 轮（时间×排序的组合）
- 总结果数：20~30 条，去重后 10~15 条

---

## ⚙️ 与智能推荐的区别

| 场景 | 使用工具 | 说明 |
|------|---------|------|
| 用户指定了策略类型 | `query.py` 多次查询 + `create-group` | 在该策略类型内选优 |
| 用户未指定策略类型 | `smart_recommend.py` | 跨策略类型智能推荐 |

**判断标准**：用户是否明确提到策略名称（风霆/鲲鹏/星辰/网格/马丁/趋势）

---

## ⚠️ 注意事项

1. **先探索后决策**：先调用 API 了解实际情况，再决定查询策略
2. **灵活组合**：根据实际返回的版本数量调整查询计划
3. **避免过度查询**：单个参数维度不超过 3 个值
4. **结果分组**：按年份、指标分组展示，便于比较
5. **说明理由**：推荐时给出具体理由（高收益/低风险/稳定性）
