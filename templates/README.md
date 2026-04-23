# QuantClaw Agent Templates

## 说明

这个目录包含创建新 agent workspace 时使用的模板文件。

## 目录结构

```
templates/
└── agent-workspace/      # Agent 工作区模板
    ├── AGENTS.md         # 项目结构与工作流程
    ├── SOUL.md           # Agent 个性与编码准则
    ├── IDENTITY.md       # Agent 身份定义
    ├── MEMORY.md         # 记忆索引
    ├── TOOLS.md          # 工具使用笔记
    ├── USER.md           # 用户信息
    └── HEARTBEAT.md      # 定期任务
```

## 使用方式

当 `quantclaw-auth` 插件创建新用户时，会自动从这个模板复制文件到用户的 workspace。

## 修改模板

修改这些文件会影响**所有新创建的 agent**，已存在的 agent 不会自动更新。

如需批量更新现有 agent，需要单独的脚本或手动操作。
