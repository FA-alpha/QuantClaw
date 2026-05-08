# 智能推荐 v2 - 完整维度说明

## 📊 所有支持的维度

智能推荐 v2 支持 **8 个查询维度**，每个维度都可以指定多个值进行循环查询。

---

## 🔢 维度列表

| 维度 | 参数名 | 说明 | 示例值 |
|------|--------|------|--------|
| **币种** | `coins` | 交易币种 | `BTC`, `ETH`, `SOL` |
| **策略类型** | `strategy_types` | 策略算法类型 | `11`(马丁), `7`(网格), `1`(趋势) |
| **方向** | `directions` | 做多/做空 | `long`, `short` |
| **时间周期** | `ai_time_ids` | 回测时间范围 | `5`(1年), `6`(2年), `7`(3年) |
| **策略版本** | `versions` | 策略算法版本号 | `1`, `2`, `3` |
| **杠杆倍数** | `leverages` | 合约杠杆 | `3`, `5`, `10`, `20` |
| **网格比例** | `grid_pcts` | 网格策略的仓位比例 | `80`, `100`, `120` |
| **扩展参数** | `search_extends` | 策略特定扩展配置 | （策略相关） |

---

## 🎯 维度使用规则

### 规则1：单个值 → 固定参数

```bash
--coins "BTC"  # 只查询 BTC
```

**行为**：传给接口 `search_coin=BTC`，返回 BTC 的所有数据

---

### 规则2：多个值 → 循环维度

```bash
--coins "BTC,ETH"  # 查询 BTC 和 ETH
```

**行为**：
1. 查询 `search_coin=BTC`
2. 查询 `search_coin=ETH`

---

### 规则3：未指定 → 查询全量

```bash
# 不传 --coins 参数
```

**行为**：不传 `search_coin` 参数，接口返回所有币种的数据

---

## 💡 维度组合示例

### 示例1：单维度循环

```bash
--coins "BTC,ETH,SOL"
```

**查询次数**：3次
- 查询 BTC
- 查询 ETH  
- 查询 SOL

---

### 示例2：二维度循环

```bash
--coins "BTC,ETH" --directions "long,short"
```

**查询次数**：4次（2×2）
- BTC + long
- BTC + short
- ETH + long
- ETH + short

---

### 示例3：三维度循环

```bash
--coins "BTC,ETH" \
--strategy-types "11,7" \
--directions "long,short"
```

**查询次数**：8次（2×2×2）
- BTC + 策略11 + long
- BTC + 策略11 + short
- BTC + 策略7 + long
- BTC + 策略7 + short
- ETH + 策略11 + long
- ETH + 策略11 + short
- ETH + 策略7 + long
- ETH + 策略7 + short

---

### 示例4：四维度循环

```bash
--coins "BTC,ETH" \
--strategy-types "11,7" \
--directions "long,short" \
--grid-pcts "80,100,120"
```

**查询次数**：24次（2×2×2×3）

---

### 示例5：混合固定与循环

```bash
--coins "BTC" \              # 固定（1个值）
--strategy-types "11,7" \    # 循环（2个值）
--directions "long" \        # 固定（1个值）
--grid-pcts "80,100,120"     # 循环（3个值）
```

**查询次数**：6次（1×2×1×3）
- BTC + 策略11 + long + 比例80
- BTC + 策略11 + long + 比例100
- BTC + 策略11 + long + 比例120
- BTC + 策略7 + long + 比例80
- BTC + 策略7 + long + 比例100
- BTC + 策略7 + long + 比例120

---

## 📈 查询次数计算

### 完整公式

```
总查询次数 = len(coins) 
           × len(strategy_types) 
           × len(directions) 
           × len(ai_time_ids)
           × len(versions)
           × len(leverages)
           × len(grid_pcts)
           × len(search_extends)
```

**注意**：
- 单个值的维度 = 1
- 未指定的维度 = 1（不循环）

---

### 计算示例

| 参数配置 | 计算 | 结果 |
|---------|------|-----|
| `--coins "BTC"` | 1 | **1次** |
| `--coins "BTC,ETH"` | 2 | **2次** |
| `--coins "BTC,ETH" --directions "long,short"` | 2×2 | **4次** |
| `--coins "BTC,ETH,SOL" --strategy-types "11,7"` | 3×2 | **6次** |
| `--coins "BTC,ETH" --strategy-types "11,7" --directions "long,short"` | 2×2×2 | **8次** |
| `--coins "BTC,ETH" --grid-pcts "80,100,120"` | 2×3 | **6次** |
| 全维度各2个值 | 2×2×2×2×2×2×2×2 | **256次** |

---

## ⚠️ 查询爆炸警告

### 危险组合

```bash
# 极端情况：8个维度各3个值
--coins "BTC,ETH,SOL" \
--strategy-types "11,7,1" \
--directions "long,short" \
--ai-time-ids "5,6,7" \
--versions "1,2,3" \
--leverages "3,5,10" \
--grid-pcts "80,100,120"

# 查询次数 = 3×3×2×3×3×3×3 = 4860 次 ⚠️
```

**建议**：
1. 避免同时循环过多维度
2. 优先固定常用参数
3. 分批次查询

---

## 💡 实际使用建议

### 常见场景1：币种对比

```bash
--coins "BTC,ETH,SOL" --strategy-types "11" --directions "long"
# 查询次数：3次
```

### 常见场景2：策略对比

```bash
--coins "BTC" --strategy-types "11,7,1" --directions "long"
# 查询次数：3次
```

### 常见场景3：网格比例优化

```bash
--coins "BTC" --strategy-types "7" --grid-pcts "60,80,100,120,140"
# 查询次数：5次
```

### 常见场景4：对冲组合

```bash
--coins "BTC,ETH" --directions "long,short"
# 查询次数：4次
```

### 常见场景5：时间周期分析

```bash
--coins "BTC" --ai-time-ids "5,6,7,8"
# 查询次数：4次
```

---

## 🔍 维度详解

### 1. 币种 (coins)

**常用值**：
- 虚拟币：`BTC`, `ETH`, `SOL`, `BNB`, `XRP`
- 美股：`AAPL`, `TSLA`, `NVDA`

**获取可用币种**：
```bash
python3 query.py --list-coins
```

---

### 2. 策略类型 (strategy_types)

**常用值**：
- `11` - 风霆系列（马丁策略）
- `7` - 网格策略
- `1` - 鲲鹏系列（趋势策略）

**获取可用策略**：
```bash
python3 query.py --list-strategies
```

---

### 3. 方向 (directions)

**可选值**：
- `long` - 做多
- `short` - 做空

**注意**：不是所有策略都支持方向参数

---

### 4. 时间周期 (ai_time_ids)

**常用值**：
- `5` - 最近1年
- `6` - 最近2年
- `7` - 最近3年
- `8` - 最近5年

**获取可用时间**：
```bash
python3 query.py --list-times
```

---

### 5. 策略版本 (versions)

**说明**：同一策略类型可能有多个版本（算法迭代）

**示例**：
- 马丁策略：`1`, `2`, `3`
- 网格策略：`1`, `2`

---

### 6. 杠杆倍数 (leverages)

**常用值**：
- 低杠杆：`3`, `5`
- 中杠杆：`10`, `20`
- 高杠杆：`50`, `100`

**注意**：仅合约交易支持

---

### 7. 网格比例 (grid_pcts)

**说明**：网格策略的仓位比例配置

**常用值**：
- BTC：`10`, `20`, `30`, `40`, `50`, `60`, `80`, `100`, `120`
- 其他币种：`60`, `80`, `100`, `120`, `140`

---

### 8. 扩展参数 (search_extends)

**说明**：策略特定的额外配置参数，具体值取决于策略类型

---

## 📝 总结

- **8个维度** 完全灵活配置
- **笛卡尔积** 生成所有查询组合
- **智能识别** 单值固定、多值循环、未指定跳过
- **性能优化** 相比 v1 减少 95%+ 查询次数

---

**更新时间**: 2024-04-27  
**版本**: v2.0.0
