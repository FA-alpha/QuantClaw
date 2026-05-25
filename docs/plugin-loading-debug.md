# QuantClaw Auth 插件加载调试记录

## 当前状态

- ✅ TypeScript 已编译为 JavaScript
- ✅ 文件结构正确（dist/index.js, openclaw.plugin.json, package.json）
- ✅ ESM import 路径已修复（.js 扩展名）
- ✅ package.json 配置正确（openclaw.extensions）
- ✅ 插件可以手动加载（node --import test 成功）
- ❌ Openclaw Gateway 无法自动发现插件

## 问题

**Openclaw 只自动发现 `@openclaw/` 命名空间下的插件**

日志显示：
```
plugins.allow is empty; discovered non-bundled plugins may auto-load: 
brave (/home/node/.openclaw/npm/node_modules/@openclaw/brave-plugin/dist/index.js)
```

`quantclaw-auth` 不在 `@openclaw/` 命名空间，未被自动发现。

## 尝试过的方案

### 1. 添加 plugins.allow ❌
```json
{
  "plugins": {
    "allow": ["quantclaw-auth"]
  }
}
```
**结果**: 导致其他插件也无法加载（只剩 brave）

### 2. 添加显式 path ❌
```json
{
  "plugins": {
    "entries": {
      "quantclaw-auth": {
        "enabled": true,
        "path": "/home/node/.openclaw/npm/node_modules/quantclaw-auth"
      }
    }
  }
}
```
**结果**: 无效果，配置 hot reload 报错 "Invalid input"

### 3. 最小化配置 ✅ (但未加载)
```json
{
  "plugins": {
    "entries": {
      "quantclaw-auth": {
        "enabled": true
      }
    }
  }
}
```
**结果**: 配置成功，hot reload 成功，但插件未加载

## 可能的解决方案

### 方案 A: 移动到 @openclaw 命名空间

```bash
cd /home/ubuntu/work/QuantClaw/extensions
mv quantclaw-auth @openclaw-quantclaw-auth

# 修改 package.json
{
  "name": "@openclaw/quantclaw-auth"
}

# 修改 openclaw.plugin.json  
{
  "id": "quantclaw-auth"
}
```

### 方案 B: 创建符号链接

```bash
sudo docker exec openclaw-2026518-openclaw-gateway-1 \
  ln -s /home/node/.openclaw/npm/node_modules/quantclaw-auth \
  /home/node/.openclaw/npm/node_modules/@openclaw/quantclaw-auth
```

### 方案 C: 联系 Openclaw 开发者

查看 Openclaw 文档或源码，了解如何注册非官方命名空间的插件。

## 下一步

建议尝试 **方案 B（符号链接）**，最简单且不改变代码结构。

---

**更新时间**: 2026-05-20 09:26 UTC
