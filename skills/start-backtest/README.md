# 回测启动与初始化模块

管理回测任务的启动、初始化和基础配置。

---

## 📂 文件结构

```
start-backtest/
├── SKILL.md                      # 技能描述（Agent 阅读）
├── start.py                      # 回测启动主脚本
├── backtest_monitor.py           # 回测监控与状态管理
├── config_manager.py             # 配置加载与参数处理
├── defaults.py                   # 默认配置参数
├── requirements.txt              # Python 依赖
└── utils/                        # 工具模块
    ├── path_resolver.py          # 路径解析工具
    └── logger.py                 # 日志记录工具
```

---

## 📚 文件详细说明

### start.py
- 主要功能：启动回测任务
- 核心职责：
  1. 解析命令行参数
  2. 初始化回测环境
  3. 配置回测参数
  4. 触发回测流程

### backtest_monitor.py
- 监控回测进程状态
- 提供实时状态追踪
- 管理回测任务生命周期
- 支持 `--total-balance` 和 `--leverage` 参数

### config_manager.py
- 加载和管理回测配置
- 处理配置文件读取
- 参数验证与默认值设置
- 支持多种配置来源（文件、命令行）

### defaults.py
- 定义回测的默认配置参数
- 提供基础配置模板
- 确保回测有最小可用配置

### utils/path_resolver.py
- 解析文件和目录路径
- 处理相对路径与绝对路径
- 确保路径的一致性和安全性

### utils/logger.py
- 自定义日志记录工具
- 支持多级别日志输出
- 记录回测过程中的关键信息和错误

---

## 🚀 快速开始

详细使用说明请参考 `SKILL.md`