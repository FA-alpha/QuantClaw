# 回测数据查询与组合优化

查询 AI 回测数据，支持多条件筛选，智能分析策略组合，自动推荐最优投资组合。

---

## ⚡ 重要提示

**所有 Python 脚本已内置自动获取 token 功能！**

- ❌ **不要使用** `--token` 参数
- ✅ **直接运行**脚本，token 会自动从 `~/.quantclaw/users.json` 获取

**示例**：
```bash
# 正确 ✅
python3 skills/backtest-query/smart_recommend.py --coins "BTC,ETH" --year 2024

# 错误 ❌ 
python3 skills/backtest-query/smart_recommend.py --token xxx --coins "BTC,ETH"
```

---

## 🚀 快速开始

### 智能推荐（推荐）

```bash
# 跨币种推荐组合
python3 skills/backtest-query/smart_recommend.py \
  --coins "BTC,ETH" \
  --year 2024 \
  --workspace $(pwd) \
  --save-memory

# 单币种指定策略类型
python3 skills/backtest-query/smart_recommend.py \
  --coins "BTC" \
  --strategy-type 11 \
  --direction long \
  --year 2024
```

### 基础查询

```bash
# 列出可用币种
python3 skills/backtest-query/query.py --list-coins

# 列出策略类型
python3 skills/backtest-query/query.py --list-strategies

# 查询回测数据
python3 skills/backtest-query/query.py \
  --coin BTC \
  --strategy-type 11 \
  --sort 2
```

---

## 🎯 使用场景

### 何时使用智能推荐 (`smart_recommend.py`)

- ✅ 需要组合推荐，但参数不完整
- ✅ 跨币种、跨策略类型组合
- ✅ "给我推荐BTC和ETH的组合"
- ✅ "BTC做多的组合"（未指定策略类型）
- ✅ "震荡行情下的策略组合"

→ **详见**：`skills/smart_recommend.md`

### 何时使用基础查询 (`query.py`)

- ✅ 查询策略列表
- ✅ 获取可用币种/策略类型
- ✅ "查询BTC做多的策略"
- ✅ "2024年夏普率最高的策略"

→ **详见**：`skills/query_basic.md`、`skills/query_advanced.md`

---

## 🔑 关键概念

### 策略类型

- **马丁策略**：名称含"风霆"
- **网格策略**：strategy_type=7
- **趋势策略**：其他策略（如鲲鹏系列）

详见：`memory/strategy_types.md`

### 工具选择

| 需求 | 使用 |
|------|-----|
| 推荐组合 | `smart_recommend.py` |
| 查询列表 | `query.py` |
| 创建组合 | `query.py --create-group` |

---

## ⚠️ 注意事项

1. **参数必填**（查询时）：`--coin`、`--sort`、`--strategy-type`

2. **参数默认值**（动态获取）：
   - 币种：未指定时使用接口返回的前3个
   - 策略类型：未指定时使用接口返回的前3个
   - 时间：未指定时使用接口返回的第1个
   - 优先级：`--ai-time-id` > `--year`

3. **方向参数**：只有 strategy_type=1,7,11 支持 `--direction`

4. **不确定参数**：用户需求模糊时，尝试多个参数组合

---

## 📚 决策流程

```
用户提问
    ↓
需要推荐组合？
    ├─ 是 → smart_recommend.py
    └─ 否 → query.py
```

**参数完整性判断**：
- 完整：币种、策略类型、方向、时间范围全部明确
- 不完整：任何参数缺失或模糊（"比较好的"、"推荐"等）

---

根据用户具体问题，加载对应的子技能模块 (`skills/*.md`) 获取详细说明。
