# 文件组织说明

技能文件与文档的分离结构。

---

## 📂 目录结构

### 技能目录 `/skills/backtest-query/`

**仅保留必要的执行文件**：

```
skills/backtest-query/
├── SKILL.md                      # 技能描述（Agent 阅读）
├── README.md                     # 简要说明
├── query.py                      # 基础查询工具
├── smart_group_recommend.py      # 智能推荐脚本
├── defaults.py                   # 默认配置
├── requirements.txt              # Python 依赖
└── analysis/                     # 分析模块
    ├── __init__.py
    ├── correlation.py            # 相关性分析
    ├── risk_analyzer.py          # 风险分析
    └── portfolio_optimizer.py    # 组合优化
```

---

### 文档目录 `/docs/skills/backtest-query/`

**所有说明类文档**：

```
docs/skills/backtest-query/
├── README.md                     # 文档索引
├── API_SORT.md                   # API 排序说明
├── ARCHITECTURE.md               # 架构设计
├── DIMENSIONS.md                 # 参数说明
├── SORTING_STRATEGY.md           # 排序策略
├── SORT_METHODS.md               # 排序方法详解
├── examples/                     # 示例
│   ├── smart_group_example.md
│   └── multi_sort_demo.md
└── old-docs/                     # 历史文档
    ├── query_basic.md
    └── query_advanced.md
```

---

## 🎯 设计原则

1. **技能目录** - 仅包含代码和 Agent 必读的 SKILL.md
2. **文档目录** - 所有详细说明、示例、设计文档
3. **保持干净** - 无 __pycache__、测试脚本等临时文件

---

## 📋 迁移记录

**已移动到文档目录**：
- API_SORT.md
- ARCHITECTURE.md
- DIMENSIONS.md
- SORTING_STRATEGY.md
- SORT_METHODS.md
- examples/
- skills/ (旧文档) → old-docs/

**已删除**：
- test_smart_group.sh (测试脚本)
- __pycache__/ (Python 缓存)

---

*最后更新: 2026-04-28*
