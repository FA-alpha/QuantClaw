# Templates Changelog

## 2025-05-19

### 新增模板机制
- 创建 `agent-workspace/` 模板目录
- 包含 7 个标准 MD 文件：
  - `AGENTS.md` - 项目结构与工作流程
  - `SOUL.md` - Agent 个性与工作风格
  - `IDENTITY.md` - Agent 身份定义
  - `MEMORY.md` - 记忆索引
  - `TOOLS.md` - 工具使用笔记
  - `USER.md` - 用户信息模板
  - `HEARTBEAT.md` - 定期任务配置

### 集成到 quantclaw-auth
- 修改 `index.ts` 的 `createWorkspace()` 方法
- 新增 `templatePath` 配置项
- 支持从模板自动复制文件
- 保留回退机制：模板不存在时使用硬编码

### 优势
- ✅ 统一管理所有 agent 的初始配置
- ✅ 修改模板即可影响新创建的所有 agent
- ✅ 版本控制友好，可追踪模板变更历史
- ✅ 便于团队协作和标准化

## 2025-05-19 (更新 4 - 最终方案)

### Fallback Workspace 方案
- **问题**：动态注册 agent 需要修改 Gateway 配置并重启
- **最终方案**：利用 Clawdbot 的 fallback 机制
  - Plugin 创建 `~/clawd-{agentId}/` 格式的目录
  - 从模板复制 MD 文件
  - Gateway 自动发现并使用（无需注册）
  - **Clawdbot 不会覆盖已存在的文件** ✅
- **优势**：
  - 无需动态注册
  - 无需重启 Gateway
  - 支持用户级配置隔离
  - 模板文件安全生效
- **文档**：`docs/FALLBACK-WORKSPACE.md`

## 2025-05-19 (更新 3)

### 改用共享 Agent 方案（推荐）
- **问题**：动态注册 agent 需要修改 Gateway 配置并重启
- **之前方案**：每个用户独立 agent (`qc-{hash}`)
  - 需要修改 `~/.clawdbot/clawdbot.json`
  - 需要重启 Gateway 生效
  - 管理复杂
- **新方案**：所有用户共享一个 agent (`quantclaw`)
  - 通过 sessionKey 隔离：`agent:quantclaw:{userId}`
  - 无需动态注册、无需重启
  - Server 层隔离聊天历史
- **配置**：新增 `sharedAgentId` 配置项（默认 `quantclaw`）
- **文档**：
  - `docs/SHARED-AGENT.md` - 共享 Agent 方案说明
  - `docs/ARCHITECTURE.md` - 完整架构文档

## 2025-05-19 (更新 2)

### 修正能力边界约束
- **重要修复**：SOUL.md 中的"能力边界"过于严格
- 之前："执行 shell 命令" 被禁止 → 导致 agent 不敢使用技能
- 修正后：明确**允许使用技能查询数据**
- 新增："主动使用技能获取回测数据"到工作模式
- 结果：agent 可以正常调用 `skills/backtest-query` 等技能

### 模板同步工具
- **新增脚本**：`scripts/sync-templates.py`
- 功能：将模板更新同步到所有现有用户
- 特性：
  - 自动备份（`.backup-YYYYMMDD-HHMMSS/`）
  - 预览模式（`--dry-run`）
  - 选择性更新（`--files SOUL.md`）
  - 排除文件（`--exclude USER.md`）
- 用途：修复模板后批量更新现有用户

## 2025-05-19 (更新)

### 精简与约束
- 移除 `BOOTSTRAP.md`（不需要初始化任务）
- 精简 `SOUL.md`：移除编码行为准则
- **新增"能力边界"**：明确禁止文件操作，仅允许分析服务
  - 禁止：创建/修改/删除文件、执行命令、写入数据
  - 允许：回答问题、分析数据、提供建议

### 技能使用指南
- **AGENTS.md 新增"技能使用指南"**：
  - 明确 `backtest-query` 技能的使用场景
  - 提供典型问题与参数示例
  - 引导 Agent 正确使用技能查询回测数据
  - **⭐ 突出策略组合功能**：创建策略组是核心功能，用于将多个优选策略组合成投资组合
