# QuantClaw 量化工作区

## 项目结构
- `strategies/` - 交易策略代码与笔记
- `data/` - 市场数据与分析文件
- `backtests/` - 回测结果与报告
- `skills/` - 量化技能模块（链接自 QuantClaw）
- `analysis/` - 深度分析报告

## 使用说明
你可以询问关于加密货币、交易策略、市场分析、风险管理等问题。

## 工作流程
1. **数据获取** - 获取并清洗市场数据
2. **策略开发** - 设计和实现交易策略
3. **回测验证** - 历史数据回测
4. **风险评估** - 分析潜在风险
5. **优化迭代** - 根据结果优化策略

## 重要记忆文件

### memory/strategy_types.md
记录所有策略类型的分类（马丁/网格/趋势）

**何时使用**：
- 用户询问策略类型时
- 需要了解策略分类时

**查看方式**：
```bash
read memory/strategy_types.md
```

---

## 技能使用指南

### backtest-query - 智能推荐策略组合（核心技能）

**何时使用**：
- 用户需要**创建策略组合**时（最常用）
- 用户询问"推荐策略"/"组合"/"对冲"/"分散"等关键词
- 用户指定条件查询策略（币种、方向、风险偏好等）

---

### 🎯 核心工作流程

#### 1️⃣ 智能推荐（主要功能）

```bash
cd /home/ubuntu/work/QuantClaw
python3 skills/backtest-query/smart_group_recommend.py \
  --query "用户需求描述" \
  --coins "BTC,ETH" \
  --directions "long,short" \
  --min-total-win-rate 60 \
  --max-recent-drawdown 15 \
  --output /tmp/rec_$(date +%s).json
```

**典型场景**：
```
❓ "帮我推荐BTC的对冲组合"
✅ --query "BTC对冲" --coins "BTC" --directions "long,short"

❓ "主流币做多，要稳定一点的"
✅ --coins "BTC,ETH,SOL" --directions "long" 
   --min-total-win-rate 65 --max-recent-drawdown 10

❓ "风霆策略组合"
✅ --strategy-types "1,11" --coins "BTC,ETH"
```

#### 2️⃣ 自动创建策略组

**判断逻辑**：
- 用户说"创建"/"建立"/"生成" → 推荐后**自动创建**
- 否则 → 推荐后**询问确认**

```bash
# 提取 tokens
TOKENS=$(python3 -c "
import json
with open('/tmp/rec_*.json') as f:
    data = json.load(f)
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

### 📋 参数速查表

#### 查询范围
| 参数 | 说明 | 示例 |
|------|------|------|
| `--coins` | 币种（逗号分隔） | `"BTC,ETH,SOL"` |
| `--strategy-types` | 策略类型ID | `"1,11"` (马丁) |
| `--directions` | 方向 | `"long,short"` |
| `--ai-time-ids` | 时间ID | `"5,6"` |

#### 筛选条件
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--min-total-win-rate` | 最小总胜率（%） | 60 |
| `--min-recent-profit-rate` | 最小近期收益（%） | - |
| `--max-recent-drawdown` | 最大近期回撤（%） | 15 |
| `--min-trade-count` | 最小交易次数 | 50 |

#### 排序与组合
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--top-per-group` | 每组取几个 | 5 |
| `--sort-methods` | 排序方式 | `"sharpe,return,drawdown"` |
| `--max-combinations` | 最多推荐几个组合 | 10 |

---

### 🔍 查询可用参数

**在推荐前先查询最新数据**（已缓存，快速返回）：

```bash
cd /home/ubuntu/work/QuantClaw/skills/backtest-query

# 可用币种
python3 query.py --list-coins

# 策略类型
python3 query.py --list-strategies

# 时间ID
python3 query.py --list-ai-times
```

**策略类型映射**：
| 用户描述 | 策略类型ID | 说明 |
|---------|-----------|------|
| 马丁策略 | `1, 11` | 名称含"风霆" |
| 网格策略 | `7` | 天阙网格 |
| 趋势策略 | 其他所有 | 鲲鹏等 |

---

### 🎨 典型场景速查

```bash
# 1. 对冲组合（多空）
--coins "BTC" --directions "long,short" --query "BTC对冲"

# 2. 币种分散（主流币）
--coins "BTC,ETH,SOL" --directions "long" --query "主流币做多"

# 3. 马丁策略
--strategy-types "1,11" --coins "BTC,ETH" --query "马丁组合"

# 4. 高质量策略（严格筛选）
--min-total-win-rate 65 --max-recent-drawdown 10 --min-trade-count 100

# 5. 特定版本（如风霆v4.3）
--strategy-types "11" --version-configs '[{"version":4.3,"leverage":3}]'
```

---

### ⚠️ 常见错误

| 错误 | 原因 | 解决 |
|------|------|------|
| `未查询到任何策略` | 筛选太严格 | 放宽条件或扩大范围 |
| `策略数量不足` | 少于2个策略 | 降低筛选标准 |
| 创建失败 | token 无效 | 重新推荐获取最新 |

---

**详细文档**：查看 `skills/backtest-query/SKILL.md`

## 注意事项
- 所有分析需要注明数据来源
- 回测结果需要记录参数和时间范围
- 风险警示必须明确说明
- 使用技能前先检查参数是否完整
