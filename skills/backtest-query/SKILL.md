# 回测数据查询与策略组合

智能推荐策略组合并创建策略组。

---

## 命令格式

```bash
python3 skills/backtest-query/smart_group_recommend.py \
  --query "用户需求" \
  [参数选项...]
```

**创建判断**：
- 明确说"创建/建立/生成" → 自动创建
- 只说"推荐/查询" → 展示结果 + 问是否创建
- 不确定 → 先展示，再问用户

---

## 核心参数

### 必填
- `--query` - 用户需求描述

### 常用参数
- `--coins` - 币种（逗号分隔），默认查所有
- `--strategy-types` - 策略类型ID（逗号分隔），默认查所有
- `--ai-time-ids` - 时间ID（逗号分隔），默认查所有
- `--strategy-version-map` - 版本控制（JSON）
- `--strategy-direction-map` - 方向控制（JSON）
- `--top-per-group` - 每组取几个，默认5
- `--max-combinations` - 最多推荐几个组合，默认10

### 筛选条件
- `--min-total-win-rate` - 最小总胜率（%）
- `--min-recent-profit-rate` - 最小近期收益率（%）
- `--max-recent-drawdown` - 最大近期回撤（%）
- `--min-trade-count` - 最小交易次数

---

## Agent 决策规则

### 0. 查询优化（重要）
**轮询机制**：coins × strategy_types × versions × directions × time_ids × pcts = 组合数

**条件太少时引导用户**：
```
❌ 条件不足示例：
用户："帮我推荐策略"
→ 没指定币种、策略类型、版本、时间
→ 可能产生数千个组合，查询缓慢

✅ 引导话术：
"为了更精准推荐，请先提供：
 1. **币种**？（如 BTC、ETH、SOL，最多建议3-5个）
 2. 策略类型？（风霆/网格/马丁）
 3. 时间范围？（最近30天/90天）
 4. 其他偏好？（方向、版本、风险等）"
```

**建议最少提供**：
- **币种（1-5个）** - 影响最大，必须限制
- 策略类型（1-3个）
- 时间范围（1个）

**币种不限的后果**：
```
不指定币种 = 查询所有币种（可能30+个）
→ 组合数爆炸：30币 × 2策略 × 2方向 = 120+组合
→ 查询时间：2-5分钟

对比：
- 1币种 × 2策略 × 2方向 = 4组合（秒级）
- 3币种 × 2策略 × 2方向 = 12组合（5-10秒）
- 30币种 × 2策略 × 2方向 = 120组合（2-5分钟）
```

**优先级**：币种 > 时间 > 策略类型

### 1. 触发关键词
**组合类**：策略组、回测组、组合、投资组合  
**推荐类**：推荐、建议、帮我选、怎么配  
**多策略**：多策略、对冲、配对

### 2. 参数动态查询
```bash
# 必须先查询，不要硬编码
python3 skills/backtest-query/query.py --list-coins       # 币种列表
python3 skills/backtest-query/query.py --list-strategies  # 策略类型（重要：返回 id）
python3 skills/backtest-query/query.py --list-ai-times    # 时间ID
```

**策略类型说明**（重要）：
```
常见策略类型 ID：
  11 - 风霆V4
  7  - 星辰（网格）
  1  - 风霆V1（马丁）
  8  - 鲲鹏V4
  3  - 鲲鹏V1

用户说               → 查询后映射
───────────────────────────────
"风霆"/"风霆V4"     → id=11
"网格"/"星辰"       → id=7
"马丁"              → id=1
"鲲鹏"              → id=8 或 3（需确认版本）
```

⚠️ **必须先执行 `--list-strategies` 查询 ID，不要硬编码！**

### 3. 版本控制（重要）
**统一用 `--strategy-version-map`，不用 `--versions`**

```json
{
  "11": ["4.3"],    // 简化格式：查询 4.3 的所有配置（不同杠杆/复投）
  "7": null,        // 查所有版本
  "1": [完整版本对象]  // 完整格式：必须包含策略版本的全部字段
}
```

**两种格式**：
1. **简化格式（推荐）**：`["4.3", "4.4"]`
   - 自动查询该版本号的所有配置（不同杠杆、复投等）
   - 用户只说版本号时用这个

2. **完整格式（精确控制）**：`[完整版本对象]`
   - 必须传入策略版本的完整对象（包含所有字段）
   - 从 `--list-strategies` 的返回中获取
   - 不要只传 `{"version": "4.3", "leverage": 3}`（不完整）

**规则**：
- 用户说 "V4.3" → 传 `["4.3"]`（简化格式）
- 用户未指定 → 传 `null`（查所有）
- 用户说 "V4.3 3倍杠杆" → 传 `["4.3"]`，不要试图构造完整对象

### 4. 方向控制
```json
// strategy-direction-map 格式
{
  "11": ["long", "short"],  // 所有币种统一方向
  "7": ["long"]
}
```

**限制**：不支持按币种细分方向（如 BTC做多、SOL做空）  
**解决**：所有币种统一方向，或告知用户限制

### 5. 时间映射
```
用户说 "最近30天"
  ↓
1. 执行 --list-ai-times
2. 找到 "3 - 最近30天"
3. 传 --ai-time-ids "3"
```

---

## 典型案例

### 案例1：简单推荐
```bash
--query "推荐 BTC 策略" --coins "BTC"
```

### 案例2：多空对冲
```bash
--query "BTC 对冲" \
--coins "BTC" \
--strategy-direction-map '{"11": ["long", "short"]}'
```

### 案例3：指定版本+时间
```bash
# 用户："风霆V4.3 3倍杠杆，最近30天，2个BTC做多+2个做空"

# 步骤1：查时间ID
python3 skills/backtest-query/query.py --list-ai-times  # 得到 id=3

# 步骤2：推荐
--query "风霆V4.3 3倍杠杆，最近30天高收益" \
--coins "BTC" \
--strategy-types "11" \
--strategy-version-map '{"11": ["4.3"]}' \
--ai-time-ids "3" \
--strategy-direction-map '{"11": ["long", "short"]}' \
--top-per-group 2 \
--max-combinations 1

# 注意：
# - 用简化格式 ["4.3"]，会自动查询所有 4.3 版本（3倍、1.5倍等）
# - 不要试图构造 {"version": "4.3", "leverage": 3}（不完整）
# - 系统会自动过滤出 3 倍杠杆的配置
```

### 案例4：多币种多策略
```bash
--query "BTC风霆v4.3 + ETH网格v1.0" \
--coins "BTC,ETH" \
--strategy-types "11,7" \
--strategy-version-map '{"11": ["4.3"], "7": ["1"]}'
```

---

## 结果处理

```json
{
  "error": "错误信息（如有）",
  "combinations": [
    {
      "strategies": [
        {"strategy_token": "token123", "coin": "BTC", "name": "风霆_做多"}
      ]
    }
  ]
}
```

**创建策略组**：
```bash
python3 skills/backtest-query/query.py \
  --create-group \
  --group-name "组合名" \
  --strategy-tokens "token1,token2,token3"
```

---

## 常见错误

| 错误 | 解决 |
|------|------|
| 无法自动获取token | 检查执行路径 |
| 未查询到任何策略 | 放宽筛选条件 |
| 重试失败 timeout | 降低 `--max-qps` |
| 策略X没有版本Y | 先查询可用版本 |
| 查询过慢 | 引导用户增加筛选条件 |

---

## 性能参考

| 查询条件 | 组合数 | 预计耗时 |
|---------|--------|---------|
| 1币 × 1策略 × 1时间 | ~50 | 3-5秒 |
| 3币 × 2策略 × 1时间 | ~300 | 15-30秒 |
| 5币 × 3策略 × 3时间 | ~2000+ | 2-5分钟 |

**优化建议**：
- **优先限制 `--coins`**（币种数量最多，影响最大）
- 限制 `--ai-time-ids`（减少时间维度）
- 限制 `--strategy-types`（减少策略类型）
- 使用 `--max-workers 15-20`（提高并发）
