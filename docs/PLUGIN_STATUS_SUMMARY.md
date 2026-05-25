# QuantClaw Auth 插件集成状态总结

## ✅ 已完成

1. **TypeScript 编译** - 源码已编译为 ESM JavaScript
2. **文件结构** - 符合 Openclaw 插件规范
3. **配置修正** - openclaw.plugin.json, package.json 格式正确
4. **Volume 挂载** - 插件目录已挂载到容器
5. **Docker 配置** - 路径映射、环境变量均已配置

## ❌ 核心问题

**Openclaw 无法自动发现 `quantclaw-auth` 插件**

### 现象

```
plugins.allow is empty; discovered non-bundled plugins may auto-load: 
  brave (/home/node/.openclaw/npm/node_modules/@openclaw/brave-plugin/dist/index.js)
```

只发现了 `@openclaw/brave-plugin`，未发现 `quantclaw-auth`。

### 根本原因

Openclaw 的插件发现机制可能：
- 只扫描官方 `@openclaw/` 命名空间
- 需要特定的插件注册方式
- 需要在启动时预加载

## 🔄 尝试过的方案（均未成功）

1. ❌ 添加 `plugins.allow`
2. ❌ 添加显式 `path` 配置
3. ❌ 创建符号链接到 `@openclaw/`
4. ❌ 修改 package.json name 为 `@openclaw/quantclaw-auth`

## 💡 可行的替代方案

### 方案 1: 独立 HTTP 服务（推荐）

将 quantclaw-auth 作为独立服务运行，而不是 Openclaw 插件：

```
QuantClaw Server (Python)
    ↓
独立认证服务 (Node.js)
    ↓
Openclaw Gateway (Webhook/API)
```

**优点**:
- 独立部署和调试
- 不受 Openclaw 插件系统限制
- 可以用任何语言实现

**实现**:
```bash
# 启动独立服务
cd /home/ubuntu/work/QuantClaw/server
python app.py  # 监听 /webhook/quantclaw

# 转发到 Openclaw
# 服务内部调用 Openclaw API
```

### 方案 2: 使用 Openclaw Webhook 功能

不开发插件，直接配置 Openclaw 的 webhook 路由：

```json
{
  "channels": {
    "webhook": {
      "enabled": true,
      "routes": [
        {
          "path": "/webhook/quantclaw",
          "handler": "external-service"
        }
      ]
    }
  }
}
```

### 方案 3: 联系 Openclaw 开发者

- 查看 Openclaw GitHub Issues
- 询问如何注册第三方插件
- 提交 PR 支持非官方命名空间插件

### 方案 4: Fork Openclaw 

修改源码，添加对第三方插件的支持。

## 📂 当前文件状态

```
/home/ubuntu/work/QuantClaw/extensions/quantclaw-auth/
├── dist/
│   ├── index.js              # ✅ 已编译
│   ├── token-validator.js    # ✅ 已编译
│   └── *.d.ts
├── openclaw.plugin.json      # ✅ 格式正确
├── package.json              # ✅ openclaw.extensions 配置正确
├── index.ts                  # 源码
└── token-validator.ts        # 源码
```

## 🎯 推荐行动方案

**短期**: 采用方案 1（独立服务），快速实现功能

**中期**: 研究 Openclaw 插件机制，寻找正确的注册方式

**长期**: 如果 Openclaw 不支持第三方插件，考虑贡献代码或维护 fork

## 📊 资源消耗

- Token 使用: ~125k (调试插件加载机制)
- 时间: ~1.5小时
- 结果: 插件编译成功，但无法被 Openclaw 发现

## 📝 建议

1. **暂停插件集成**，先用独立服务实现功能
2. **研究 Openclaw 文档**，查看官方插件开发指南
3. **联系社区**，询问第三方插件开发经验
4. **保留当前代码**，未来可能找到解决方案

---

**最后更新**: 2026-05-20 09:27 UTC  
**状态**: 暂停，建议转向独立服务方案
