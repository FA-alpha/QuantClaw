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

### backtest-query - 回测数据查询与策略组合

**何时使用**：
- 用户询问回测结果时
- 需要查询策略表现时
- 需要筛选特定条件的策略时
- 需要获取策略详情时
- **⭐ 需要创建策略组合时（核心功能）**

**典型场景**：

#### 基础查询
```
❓ "有哪些可用的回测时间段？"
✅ backtest-query --list-ai-times

❓ "查询BTC做多策略，按收益率排序"
✅ backtest-query --coin BTC --direction long --sort 2

❓ "2024年夏普率最高的策略"
✅ backtest-query --year 2024 --sort 3

❓ "查看某个策略的详细回测数据"
✅ backtest-query --detail <回测ID>
```

#### ⭐ 策略组合（重要）
```
❓ "帮我选几个BTC策略，创建一个对冲组合"
✅ 步骤：
   1. backtest-query --coin BTC --sort 2 --limit 10
   2. 从结果中选出优选策略的 strategy_token
   3. backtest-query --create-group --group-name "BTC对冲组" 
      --strategy-tokens "token1,token2,token3"

💡 组合策略可用于：
   - 对冲风险（多空组合）
   - 币种分散
   - 策略类型组合
   - 风险分级配置
```

**关键参数**：
- `--list-ai-times` 列出 AI 回测时间
- `--list-strategies` 列出 AI 回测策略类型
- `--list-coins` 列出可用币种
- `--coin` 币种（必填）
- `--amt-type` 类型（1现货 2合约）
- `--sort` 排序（1最新 2收益率 3夏普 4回撤）
- `--direction` 方向（long/short，仅策略类型1/7/11需要）
- `--ai-time-id` 按时间ID查询（与 --year 二选一）
- **`--create-group`** 创建策略组（核心）
- **`--group-name`** 策略组名称
- **`--strategy-tokens`** 策略 token 列表（逗号分隔）

**详细文档**：查看 `skills/backtest-query/SKILL.md`

## 注意事项
- 所有分析需要注明数据来源
- 回测结果需要记录参数和时间范围
- 风险警示必须明确说明
- 使用技能前先检查参数是否完整
