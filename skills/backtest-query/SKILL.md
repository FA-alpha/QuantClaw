# 回测数据查询与组合优化

查询 AI 回测数据，支持多条件筛选，智能分析策略组合，自动推荐最优投资组合。

## 🎯 核心能力

1. **智能推荐** - 跨币种、跨策略类型的组合推荐（一键完成）
2. **数据查询** - 多维度筛选回测策略
3. **组合创建** - 将多个策略组合成策略组
4. **分析工具** - 相关性分析、风险评估、组合优化

---

## 📚 子技能模块（按需加载）

根据用户需求选择对应的模块：

### 1. 智能推荐（跨策略类型）

**何时使用**：
- 用户未指定具体策略类型
- 需要多币种、多策略类型的组合
- 需要根据行情推荐策略

**示例**：
- "给我推荐BTC和ETH的组合"
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

### 3. 高级查询（特定策略类型）

**何时使用**：
- 用户明确指定了策略类型（风霆/鲲鹏/网格等）
- 需要找该策略类型的"最佳"策略
- 需要对不确定参数进行多次尝试

**示例**：
- "BTC做多风霆v4比较好的策略"
- "BTC做多风霆v4的组合"
- "ETH网格策略的组合"

**详见**：`skills/query_advanced.md`

---

## 🔧 快速决策树

```
用户提问
    ↓
是否指定了具体策略类型（风霆/鲲鹏/网格）？
    ├─ 是 → 读取 skills/query_advanced.md
    └─ 否 → 继续判断
              ↓
        是否需要组合推荐？
            ├─ 是 → 读取 skills/smart_recommend.md
            └─ 否 → 读取 skills/query_basic.md
```

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

1. **Token 认证**：所有操作需要用户 token
2. **参数必填**：`--coin`、`--sort`、`--strategy-type` 查询时必填
3. **时间参数**：`--year` 和 `--ai-time-id` 二选一必传
4. **方向参数**：只有 strategy_type=1,7,11 支持 `--direction`
5. **不确定参数**：用户需求模糊时，尝试多个参数组合

---

## 📖 详细文档

- **完整参数说明**：`docs/skills/BACKTEST_QUERY.md`
- **使用示例**：`docs/skills/BACKTEST_QUERY_DEMO.md`
- **工作流指南**：`docs/skills/BACKTEST_QUERY_WORKFLOW.md`

---

## 🚀 快速开始

**最常用的两个命令**：

```bash
# 1. 智能推荐（推荐）
python skills/backtest-query/smart_recommend.py \
  --token <token> --coins "BTC,ETH" --year 2024 \
  --workspace <workspace> --save-memory

# 2. 查询列表
python skills/backtest-query/query.py \
  --token <token> --list-strategies
```

---

根据用户具体问题，加载对应的子技能模块获取详细说明。
