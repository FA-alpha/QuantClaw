# 回测启动与监控模块

管理回测任务的启动、监控和基础配置。

---

## 📂 文件结构

```
start-backtest/
├── SKILL.md                      # 技能描述（Agent 阅读）
├── start.py                      # 回测启动主脚本
├── backtest_monitor.py           # 回测监控与状态管理
├── API_RESPONSE_GUIDE.md         # API 响应指南文档
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

### API_RESPONSE_GUIDE.md
- 记录 API 交互的响应规范
- 定义标准化的 API 返回格式
- 提供错误处理和状态码说明

### SKILL.md
- 技能描述文档
- 详细说明模块功能
- 提供使用指南和示例

---

## 🚀 快速开始

详细使用说明请参考 `SKILL.md`