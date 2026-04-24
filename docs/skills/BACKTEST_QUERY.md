# backtest-query - 回测数据查询与智能组合优化

## 📖 概述

完整的量化策略分析工具，支持查询、筛选、智能推荐和组合创建。

## 🎯 核心功能

| 功能 | 脚本 | 说明 |
|-----|-----|-----|
| **智能推荐** | `smart_recommend.py` | ⭐ 一键完成查询→分析→推荐→记忆 |
| 数据查询 | `query.py` | 查询回测数据、筛选策略 |
| 组合创建 | `query.py --create-group` | 创建策略组 |
| 策略详情 | `query.py --detail` | 查看完整回测统计 |

## 📊 分析模块

位于 `analysis/` 目录：

- **correlation.py** - 相关性分析
- **risk_analyzer.py** - 风险分析（回撤错位检测）
- **portfolio_optimizer.py** - 组合优化（智能评分）

## 🚀 快速开始

### 1. 智能推荐（推荐）

```bash
python smart_recommend.py \
  --token YOUR_TOKEN \
  --coins "BTC,ETH,SOL" \
  --year 2024 \
  --workspace ~/clawd-qc-xxx \
  --save-memory
```

### 2. 基础查询

```bash
# 查询BTC做多策略
python query.py \
  --token YOUR_TOKEN \
  --coin BTC \
  --direction long \
  --amt-type 2 \
  --sort 2 \
  --strategy-type 11 \
  --year 2024
```

### 3. 创建策略组

```bash
python query.py \
  --token YOUR_TOKEN \
  --create-group \
  --group-name "我的组合" \
  --strategy-tokens "st_abc,st_def,st_xyz"
```

## 📚 文档

- **SKILL.md** - 完整参数说明
- **AGENT_WORKFLOW.md** - Agent 使用指南
- **DEMO.md** - 演示场景
- **README.md** - 本文件

## 🔧 依赖

```bash
pip install -r requirements.txt
```

依赖项：
- numpy>=1.24.0
- requests>=2.31.0

## 📁 目录结构

```
backtest-query/
├── query.py                 # 基础查询脚本
├── smart_recommend.py       # 智能推荐脚本 ⭐
├── analysis/                # 分析模块
│   ├── correlation.py
│   ├── risk_analyzer.py
│   └── portfolio_optimizer.py
├── requirements.txt
├── SKILL.md                 # 技能说明
├── AGENT_WORKFLOW.md        # Agent 工作流
├── DEMO.md                  # 演示指南
├── README.md                # 本文件
├── test_analysis.py         # 分析模块测试
└── simple_test.py           # 简单测试

```

## 🎓 使用建议

### For Agent

1. **优先使用 `smart_recommend.py`** - 自动完成完整分析
2. **始终开启 `--save-memory`** - 建立用户画像
3. **解读结果** - 用人话说，不要直接抛数据
4. **风险警示** - 每次推荐必须说明风险

### For 用户

1. **明确需求** - 告诉 Agent 币种、风险偏好、目标
2. **查看历史** - 询问之前的推荐记录
3. **小仓测试** - 实盘前先用小资金测试
4. **设置止损** - 务必做好风险管理

## 🧪 测试

```bash
# 测试分析模块
python simple_test.py

# 测试完整流程（需要 token）
python smart_recommend.py \
  --token YOUR_TOKEN \
  --coins "BTC" \
  --year 2024 \
  --no-detail \
  --format json
```

## ⚠️ 注意事项

1. **Token 安全** - 不要泄露用户 token
2. **API 限制** - 避免频繁调用
3. **数据时效** - 缓存 24 小时后会过期
4. **回测局限** - 历史数据不代表未来
5. **风险自负** - 投资有风险，决策需谨慎

## 📊 Phase 1 完成度

✅ 相关性分析  
✅ 风险分析  
✅ 组合优化  
✅ 智能推荐  
✅ 记忆管理  
✅ Agent 工作流  
✅ 文档完善  

## 🔜 未来计划

- [ ] 实时净值监控
- [ ] 策略组表现跟踪
- [ ] 市场环境自适应
- [ ] 风险预警系统
- [ ] 回测参数优化

## 💬 反馈

如有问题或建议，请通过 Agent 反馈。

---

**Version**: 2.0  
**Last Updated**: 2024-04-24  
**Status**: Phase 2 完成 ✅
