# 回测数据查询与策略组合

智能推荐策略组合并创建策略组。

---

## 使用流程

### 1. 推荐策略

```bash
python3 skills/backtest-query/smart_group_recommend.py \
  --query "用户需求描述" \
  --coins "BTC,ETH" \
  --directions "long,short" \
  --min-total-win-rate 60 \
  --max-recent-drawdown 15 \
  --output /tmp/rec_$(date +%s).json
```

**判断是否直接创建**：
- 用户说"创建"/"建立"/"生成" → 推荐后直接创建
- 否则 → 推荐后询问确认

### 2. 提取并创建

```bash
# 提取 tokens
TOKENS=$(python3 -c "
import json
with open('/tmp/rec_*.json') as f:
    data = json.load(f)
if 'error' in data:
    print('ERROR:' + data['error'])
    exit(1)
tokens = [s['strategy_token'] for s in data['combinations'][0]['strategies']]
print(','.join(tokens))
")

# 创建策略组
python3 skills/backtest-query/query.py \
  --create-group \
  --group-name "组合名_$(date +%Y%m%d)" \
  --strategy-tokens "$TOKENS"
```

---

## 参数说明

### 查询范围

#### 全局参数

| 参数 | 说明 | 示例 | 依赖关系 | 未传时行为 |
|------|------|------|---------|-----------|
| `--coins` | 币种（逗号分隔） | `"BTC,ETH,SOL"` | 独立 | 查询所有可用币种 |
| `--strategy-types` | 策略类型ID（逗号分隔） | `"1,11"` | 独立 | 查询所有策略类型 |
| `--ai-time-ids` | 时间ID（逗号分隔） | `"5,6"` | 独立 | 查询所有时间ID |
| `--versions` | 版本号（逗号分隔） | `"4.2,4.3"` | **依赖 strategy-types** | 自动提取该策略的所有版本 |
| `--directions` | 方向 | `"long,short"` | **依赖 strategy-types** | 类型 1,7,11 轮询 long/short，其他不传 |
| `--search-pcts` | 网格比例（逗号分隔） | `"80,100,120"` | **依赖 coins** | BTC: 10~120，其他: 60~140 |
| `--search-recommand-type` | 推荐类型 | `1`（推荐）/ `2`（交易中） | 独立 | 默认 1 |

#### 映射参数（🔥 推荐使用）

| 参数 | 说明 | 格式 | 优先级 |
|------|------|------|--------|
| `--strategy-version-map` | 按策略指定版本配置 | JSON 对象 | 🔥 最高 |
| `--strategy-direction-map` | 按策略指定方向 | JSON 对象 | 🔥 最高 |
| `--coin-pct-map` | 按币种指定比例 | JSON 对象 | 🔥 最高 |

**格式说明**：
```json
// strategy-version-map 格式（支持三种）
{
  "11": ["4.3", "4.4"],                          // 简化格式：版本号数组
  "7": [{"version": "3.2", "leverage": 10}],     // 完整格式：配置对象数组
  "1": null                                       // null：自动查询所有版本
}

// strategy-direction-map 格式
{
  "11": ["long", "short"],   // 指定方向
  "7": ["long"],             // 单方向
  "8": null                  // null：自动判断
}

// coin-pct-map 格式
{
  "BTC": ["80", "100", "120"],  // 指定比例
  "ETH": ["60", "80"],          // 不同币种不同比例
  "SOL": null                   // null：使用默认比例
}
```

#### 参数优先级规则

系统按以下优先级处理参数：

**优先级 1：映射参数（最高）** 🔥
- `--strategy-version-map`：按策略精确指定版本
- `--strategy-direction-map`：按策略精确指定方向
- `--coin-pct-map`：按币种精确指定比例

**优先级 2：全局参数（中）**
- `--versions`：对所有策略类型生效
- `--directions`：对所有策略类型生效
- `--search-pcts`：对所有币种生效

**优先级 3：自动查询（最低）**
- 未传任何参数时，系统自动查询所有可能值

**示例**：
```bash
# 场景：11 使用 v4.3，7 使用 v3.2，其他策略自动查询
--strategy-types "11,7,1" \
--versions "4.0" \                      # 全局：所有策略用 v4.0
--strategy-version-map '{
  "11": ["4.3"],                        # 覆盖：策略11用v4.3
  "7": ["3.2"]                          # 覆盖：策略7用v3.2
}'
# 结果：11→v4.3, 7→v3.2, 1→v4.0（使用全局参数）
```

#### 参数依赖关系

**1. versions 依赖 strategy-types**
- 每个策略类型有不同的版本列表
- 映射参数可为每个策略单独指定
- 简化格式（版本号字符串）会自动查询该版本的所有配置（如所有杠杆组合）

**2. directions 依赖 strategy-types**
- 仅策略类型 **1, 7, 11** 需要传方向
- 映射参数可为支持方向的策略单独指定

**3. search-pcts 依赖 coins**
- BTC：`['10', '20', '30', '40', '50', '60', '80', '100', '120']`
- 其他：`['60', '80', '100', '120', '140']`
- 映射参数可为每个币种单独指定

### 筛选条件

| 参数 | 说明 | 示例 |
|------|------|------|
| `--min-total-win-rate` | 最小总胜率（%） | `60` |
| `--min-recent-profit-rate` | 最小近期收益率（%） | `10` |
| `--max-recent-drawdown` | 最大近期回撤（%） | `15` |
| `--min-trade-count` | 最小交易次数 | `50` |
| `--min-stability` | 最小稳定性 | `0.8` |

### 排序和组合

| 参数 | 说明 | 示例 |
|------|------|------|
| `--top-per-group` | 每种排序取几个 | `5` |
| `--sort-methods` | 排序方式（逗号分隔） | `"sharpe,return,drawdown"` |
| `--api-sort` | API排序类型 | `2`（收益）/ `3`（夏普）/ `4`（回撤） |
| `--max-combinations` | 最多推荐几个组合 | `10` |
| `--quiet` | 静默模式 | 不输出详细过程 |

---

## 查询可用参数

在构建查询前，先获取最新的可用参数：

```bash
# 查看可用币种
python3 skills/backtest-query/query.py --list-coins

# 查看策略类型
python3 skills/backtest-query/query.py --list-strategies

# 查看时间ID
python3 skills/backtest-query/query.py --list-ai-times
```

### 根据用户需求筛选

**示例1：用户说"马丁策略"**
1. 查询策略列表 → 找到包含"风霆"的策略
2. 提取策略类型ID（如 `1, 11`）
3. 构建参数：`--strategy-types "1,11"`
4. ✅ **无需传 `--versions`**，系统会自动提取所有版本
5. ✅ **无需传 `--directions`**，系统会自动轮询 long/short

**示例2：用户说"所有虚拟货币"**
1. 查询币种列表 → 筛选 `type="CRYPTO"` 的币种
2. 提取币种代码（如 `BTC,ETH,SOL,...`）
3. 构建参数：`--coins "BTC,ETH,SOL,..."`
4. ✅ **无需传 `--search-pcts`**，系统会根据币种自动选择比例

**示例3：用户说"主流币"**
- 根据常识筛选：`BTC,ETH,SOL,BNB`
- 或者直接**不传 `--coins`**，系统会查询所有币种

**示例4：用户说"BTC 做多"**
- 只需传：`--coins "BTC" --directions "long"`
- ✅ **无需传 `--strategy-types`**，系统会查询所有策略类型
- ✅ **无需传 `--versions`**，系统会自动提取所有版本

### 🎯 推荐实践：只传用户明确指定的参数

由于系统会自动处理参数依赖关系，建议：
- **只传用户明确指定的参数**
- 其他参数留空，让系统自动查询和组合
- 这样可以获得更全面的推荐结果

### Agent 使用指南

#### 场景1：用户为不同策略指定不同版本

**用户需求**："BTC 风霆 v4.3/v4.4，ETH 网格 v3.2"

✅ **正确做法**：使用 `--strategy-version-map`
```bash
--coins "BTC,ETH" \
--strategy-types "11,7" \
--strategy-version-map '{
  "11": ["4.3", "4.4"],
  "7": ["3.2"]
}'
```

❌ **错误做法**：使用全局参数
```bash
--versions "4.3,4.4,3.2"  # 会导致网格查询 v4.3/v4.4（但它可能没有）
```

#### 场景2：用户明确指定杠杆等参数

**用户需求**："BTC 风霆 v4.3，3倍杠杆"

✅ **使用完整格式**：
```bash
--strategy-version-map '{
  "11": [{"version": "4.3", "leverage": 3, "search_extend": "3w"}]
}'
```

#### 场景3：混合使用（部分精确，部分宽泛）

**用户需求**："BTC 风霆 v4.3(3倍)，其他策略用最新版本"

✅ **结合映射和全局参数**：
```bash
--strategy-types "11,7,1" \
--versions "4.5" \              # 全局：默认用 v4.5
--strategy-version-map '{
  "11": [{"version": "4.3", "leverage": 3}]  # 策略11特殊指定
}'
# 结果：11→v4.3(3x), 7→v4.5, 1→v4.5
```

#### 场景4：用户需求宽泛

**用户需求**："推荐 BTC 策略"

✅ **只传明确的，其他自动**：
```bash
--coins "BTC"
# strategy-types/versions/directions 全部自动查询
```

#### Agent 决策树

```
分析用户需求
├─ 是否为不同策略指定了不同参数（版本/方向/比例）？
│  ├─ 是 → 使用映射参数 (strategy-version-map 等)
│  └─ 否 ↓
│
├─ 是否明确指定了 leverage 等额外字段？
│  ├─ 是 → 使用完整格式 {"version": "4.3", "leverage": 3}
│  └─ 否 → 使用简化格式 ["4.3", "4.4"]（自动获取所有配置）
│
└─ 用户明确说的 → 传入
   用户没说的 → 不传（自动查询）
```

---

## JSON 结构

```json
{
  "error": "错误信息（如有）",
  "combinations": [
    {
      "score": 85.5,
      "expected_return": 95.2,
      "portfolio_risk": {"max_drawdown": 11.5},
      "strategies": [
        {
          "strategy_token": "token123",
          "coin": "BTC",
          "name": "风霆_做多",
          "year_rate": 102,
          "sharp_rate": 2.35
        }
      ]
    }
  ]
}
```

**提取路径**：
- 检查错误：`error` 字段
- 最优组合：`combinations[0]`
- 策略 tokens：`combinations[0].strategies[].strategy_token`

---

## 常见错误

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `无法自动获取 token` | 不在用户 workspace | 确保在正确路径执行 |
| `未查询到任何策略` | 筛选条件太严格 | 放宽条件或扩大范围 |
| `策略数量不足` | 少于2个策略 | 降低筛选标准 |
| `API 请求失败` | 网络问题 | 检查网络或稍后重试 |
| 创建失败 | token 格式/策略不存在 | 重新推荐获取最新 tokens |

---

## 快速参考

### 典型场景示例

```bash
# 场景1：对冲组合（BTC 多空）
--query "BTC 对冲组合" \
--coins "BTC" \
--directions "long,short"

# 场景2：币种分散（只做多）
--query "多币种分散做多" \
--coins "BTC,ETH,SOL" \
--directions "long"

# 场景3：马丁策略（所有币种）
--query "马丁策略推荐" \
--strategy-types "1,11"

# 场景4：高质量策略（不限类型、不限币种）
--query "高质量低回撤策略" \
--min-total-win-rate 65 \
--max-recent-drawdown 10 \
--min-trade-count 100

# 场景5：多策略不同版本（使用映射参数）
--query "BTC 风霆 v4.3/v4.4，ETH 网格 v3.2" \
--coins "BTC,ETH" \
--strategy-types "11,7" \
--strategy-version-map '{
  "11": ["4.3", "4.4"],
  "7": ["3.2"]
}'

# 场景6：精确控制杠杆
--query "BTC 风霆 v4.3 3倍杠杆" \
--coins "BTC" \
--strategy-types "11" \
--strategy-version-map '{
  "11": [{"version": "4.3", "leverage": 3}]
}'

# 场景7：不同币种不同比例
--query "BTC 高比例，ETH 低比例" \
--coins "BTC,ETH" \
--coin-pct-map '{
  "BTC": ["100", "120"],
  "ETH": ["60", "80"]
}'
```

### 📌 参数传递原则

**根据用户需求传参，不要自作主张添加或省略**：

**场景1：用户需求明确** ✅
```bash
# 用户说："我要 BTC 风霆 v4.3 做多，80% 比例，最近 1 年"
# → 全部传入，这是精确需求
--coins "BTC" \
--strategy-types "11" \
--versions "4.3" \
--directions "long" \
--search-pcts "80" \
--ai-time-ids "5"
```

**场景2：用户需求部分明确** ✅
```bash
# 用户说："我要 BTC 马丁策略"
# → 只传用户明确说的，其他自动查询
--coins "BTC" \
--strategy-types "1,11"
# versions/directions/pcts/time_ids 由系统自动处理
```

**场景3：用户需求宽泛** ✅
```bash
# 用户说："推荐一些高质量策略"
# → 只传筛选条件，范围参数全部自动查询
--min-total-win-rate 65 \
--max-recent-drawdown 10
# coins/strategy-types/versions... 全部自动查询
```

**❌ 错误做法**：AI 自作主张限制范围
```bash
# 用户说："推荐 BTC 策略"
# ❌ 不要自己决定只查 v4.3、只做多、只用 80% 比例
--coins "BTC" \
--versions "4.3" \        # 用户没说版本，不要限制
--directions "long" \     # 用户没说方向，不要限制
--search-pcts "80"        # 用户没说比例，不要限制

# ✅ 正确做法：只传用户明确说的
--coins "BTC"
# 让系统查询所有版本、所有方向、所有比例
```
