# QuantClaw 量化工作区

## ⚡ 性能优化：Skills 路径规范

**本工作区已通过软链接安装 QuantClaw skills**：
- 本地路径：`./skills/` → `**/skills`

**强制规则（避免性能损耗）**：
1. ✅ **使用技能时，始终优先使用本地路径**：`./skills/<skill-name>/`
2. ✅ **读取 SKILL.md**：`./skills/<skill-name>/SKILL.md`
3. ✅ **执行脚本**：`./skills/<skill-name>/<script>.py`
4. ❌ **禁止使用全局路径**：`/home/ubuntu/.npm-global/...`（慢，会浪费时间）

**为什么重要**：Clawdbot 默认会先扫描 npm-global 目录，非常慢。使用本地路径可以**立即访问技能**。

---

## 项目结构
- `skills/` - 量化技能模块（软链接自 QuantClaw）⚡

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

### backtest-query - 智能推荐策略组合

**⚡ 技能路径**（必须使用本地路径）：
- 📄 SKILL.md: `./skills/backtest-query/SKILL.md`
- 🐍 脚本: `./skills/backtest-query/query.py`

**何时使用**：
- 用户询问"AI 回测"/"查询回测"/"回测结果"
- 用户询问"推荐策略"/"组合"/"对冲"/"分散"
- 需要创建策略组合时
- 根据条件筛选策略时（币种/方向/风险偏好）

**核心流程**：
```
查询需求 → 智能推荐 → 自动创建（或询问确认）
```

**典型场景**：
- "推荐BTC对冲组合" → 自动筛选多空策略
- "主流币做多，要稳定的" → 按风险偏好筛选
- "风霆策略组合" → 按策略类型筛选

**策略类型**：
- 马丁策略：`1, 11`（名称含"风霆"）
- 网格策略：`7`（网格）
- 趋势策略：其他所有

**使用示例**：
```bash
# ✅ 正确：使用本地路径读取技能
read ./skills/backtest-query/SKILL.md
exec python3 ./skills/backtest-query/query.py --coin BTC

# ❌ 错误：不要用全局路径（慢）
read /home/ubuntu/.npm-global/lib/node_modules/clawdbot/skills/backtest-query/SKILL.md
```

---

### trade-bot - 交易机器人管理

**⚡ 技能路径**（必须使用本地路径）：
- 📄 SKILL.md: `./skills/trade-bot/SKILL.md`
- 🐍 入口: `./skills/trade-bot/scripts/trade_bot.py`

**何时使用**：
- 查询运行中的机器人列表或详情
- 停止/批量停止/预约停止机器人
- 暂停/取消暂停加仓
- 手动加仓/取消加仓
- 调整保证金（增加/减少）
- 编辑策略参数（杠杆/止损/网格等）
- 查询杠杆率统计、实时币价/余额

**核心流程**：
```
🟢 只读操作（直接执行）:
  list → 查看机器人列表
  detail → 查看单台详情
  leverage → 杠杆率统计
  exchange-list → 交易所账户
  realtime → 实时币价/余额

🔴 写操作（预览 → 用户确认 → --confirm 执行）:
  ① 不加 --confirm → 返回预览
  ② 展示 agent_display 给用户
  ③ 用户确认 → 加 --confirm 重新运行

🟡 编辑（三步流程）:
  ① edit --bot-id → 预览可编辑字段
  ② edit --bot-id --rule → 差异对比
  ③ edit --bot-id --merged-rule → 确认执行
```

**关键规则**：
- 🚨 **写操作必须先预览、后确认** — 绝对不要跳过预览直接加 `--confirm`
- 🚨 **Agent 不得自行决定金额/价格** — 加仓/调保证金必须等用户指定
- 🚨 **blocked=true 必须停止** — 展示 `agent_display.user_prompt`，不做任何操作
- ⚠️ **preview 返回后先展示给用户** — 用户说"确认"后再加 `--confirm` 原样重跑
- ⚠️ **edit 第③步用第②步的 merged_rule** — 不要自己拼参数

**使用示例**：
```bash
# ✅ 只读：查看运行中机器人
cd skills/trade-bot/scripts && python3 trade_bot.py list --agent-id "qc-xxx"

# ✅ 只读：查看详情
cd skills/trade-bot/scripts && python3 trade_bot.py detail --agent-id "qc-xxx" --bot-id "2039"

# ✅ 写操作：先预览
cd skills/trade-bot/scripts && python3 trade_bot.py stop --agent-id "qc-xxx" --bot-id "2039" --save-type "4"
# → 展示预览 → 用户确认 →
cd skills/trade-bot/scripts && python3 trade_bot.py stop --agent-id "qc-xxx" --bot-id "2039" --save-type "4" --confirm

# ❌ 错误：跳过预览直接执行
cd skills/trade-bot/scripts && python3 trade_bot.py stop --agent-id "qc-xxx" --bot-id "2039" --save-type "4" --confirm
```

---

### start-backtest - 启动回测任务

**⚡ 技能路径**（必须使用本地路径）：
- 📄 SKILL.md: `./skills/start-backtest/SKILL.md`

**何时使用**：
- 用户说"回测"/"启动回测"/"开始回测"
- 需要启动新的回测任务
- 查看策略组列表或策略详情

**核心流程**：
```
用户请求 → 识别模式 → 询问参数 → 启动回测
```

**强制动作**：
1. 立即停止一切 AI 时间列表相关操作
2. 回测的时间范围技能中会自己判断
3. AI 时间 ID（1-16）与回测完全无关，禁止查询、禁止引用、禁止映射

**回测模式**：
- **单策略回测**：一次一个策略（不需要保证金模式）
- **共享模式回测**：多策略，保证金池共享
- **独立模式回测**：多策略，独立保证金

**重要规则**：
- 🚨 **回测时的时间范围不与AI时间列表相关**  - 绝对不要使用AI时间列表中的数据（backtest-query 技能中使用的）
- 🚨 **每次回测必须询问时间范围** - 绝对不要复用历史时间
- 🚨 **回测成功后不要询问是否等待** - 直接告知结果
- ⚠️ **每次回测都是独立任务** - 不要查询历史回测


## 注意事项
- 所有分析需要注明数据来源
- 回测结果需要记录参数和时间范围
- 风险警示必须明确说明
- 使用技能前先检查参数是否完整

**🎯 核心原则: 任务连续性 + 需求全覆盖**
