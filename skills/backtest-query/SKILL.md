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

## 🎯 核心能力

1. **智能推荐** - 跨币种、跨策略类型的组合推荐（一键完成）
2. **数据查询** - 多维度筛选回测策略
3. **组合创建** - 将多个策略组合成策略组
4. **分析工具** - 相关性分析、风险评估、组合优化

---

## 📚 子技能模块（按需加载）

根据用户需求选择对应的模块：

### 1. 智能推荐（参数不完整时的组合推荐）

**何时使用**：
- 用户需要组合推荐，但**参数不完整**
- 未明确指定策略类型、时间范围或其他筛选条件
- 需要根据行情/风险偏好推荐策略

**示例**：
- "给我推荐BTC和ETH的组合"
- "BTC做多的组合"（未指定策略类型）
- "BTC风霆的组合"（未指定版本/时间/排序）
- "震荡行情下的策略组合"
- "保守型的投资组合"

**详见**：`skills/smart_recommend.md`

---

### 2. 基础查询

**何时使用**：
- 查询回测列表
- 查看策略详情
- 获取策略类型列表

**示例**：
- "查询BTC做多的策略"
- "2024年夏普率最高的策略"
- "有哪些可用的策略类型？"

**详见**：`skills/query_basic.md`

---

### 3. 高级查询（单条查询/特定策略类型）

**何时使用**：
- 用户**不需要组合推荐**，只需查询策略列表
- 明确指定了策略类型（风霆/鲲鹏/网格等）但只要查询结果
- 需要对不确定参数进行多次尝试

**示例**：
- "BTC做多风霆v4有哪些策略？"
- "查询ETH网格策略"
- "2024年夏普率最高的鲲鹏策略"

**注意**：如果用户问的是"组合"或"推荐"，应该走智能推荐而非此模块

**详见**：`skills/query_advanced.md`

---

## 🔧 快速决策树

```
用户提问
    ↓
是否需要组合推荐？
    ├─ 是 → 参数是否完整（所有必填参数都明确）？
    │       ├─ 完整 → 直接创建组合（query.py --create-group）
    │       └─ 不完整 → 智能推荐（skills/smart_recommend.md）
    │
    └─ 否 → 是单条查询还是批量查询？
            ├─ 明确指定了策略类型 → 高级查询（skills/query_advanced.md）
            └─ 未指定策略类型 → 基础查询（skills/query_basic.md）
```

**参数完整性判断**：
- 完整：币种、策略类型、方向、时间范围全部明确指定
- 不完整：任何参数缺失或模糊（如"比较好的"、"推荐"等表述）

---

## 🔑 关键概念

### 策略类型分类

在 Agent 工作区中查看：`memory/strategy_types.md`

- **马丁策略**：名称含"风霆"
- **网格策略**：只有 strategy_type=7
- **趋势策略**：其他策略（包括鲲鹏系列）

### 工具选择

| 场景 | 工具 |
|------|-----|
| 跨策略类型推荐 | `smart_recommend.py` |
| 单策略类型查询 | `query.py` 多次查询 |
| 创建组合 | `query.py --create-group` |

---

## ⚠️ 核心注意事项

1. **Token 认证**：
   - 所有操作需要用户 token
   - **自动获取**：脚本会自动从 `~/.quantclaw/users.json` 获取当前 Agent 的 token
   - **手动指定**：如需指定 token，使用 `--token` 参数
   
2. **参数必填**：`--coin`、`--sort`、`--strategy-type` 查询时必填

3. **参数默认值**（动态获取）：
   - **币种**：未指定时使用接口返回的前3个币种
   - **策略类型**：未指定时使用接口返回的前3个策略类型
   - **时间**：未指定时使用接口返回的第1个时间ID
   - 优先级：`--ai-time-id` > `--year`
   
4. **方向参数**：只有 strategy_type=1,7,11 支持 `--direction`

5. **不确定参数**：用户需求模糊时，尝试多个参数组合

---

## 🚀 快速开始

**所有脚本已支持自动获取 token，无需任何额外操作！**

### 智能推荐（推荐）

```bash
# Token 自动获取，直接使用
python3 skills/backtest-query/smart_recommend.py \
  --coins "BTC,ETH" \
  --year 2024 \
  --workspace $(pwd) \
  --save-memory

# 单币种
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

### 手动指定 Token（可选）

如果需要，可以手动指定：

```bash
python3 skills/backtest-query/smart_recommend.py \
  --token "your_token_here" \
  --coins "BTC,ETH" \
  --year 2024
```

---

根据用户具体问题，加载对应的子技能模块获取详细说明。
