# QuantClaw Auth 插件对接到 Docker Openclaw

## 当前状态

✅ **已完成：**
1. Docker compose 配置已添加 volume 挂载
2. Openclaw 配置文件已添加插件配置
3. 插件目录已挂载到容器

❌ **待完成：**
- TypeScript 源码需要编译成 JavaScript

---

## 问题分析

**Openclaw 插件加载机制：**
- 扫描 `/home/node/.openclaw/npm/node_modules/*/` 目录
- 读取 `package.json` 的 `main` 字段或 `clawdbot.extensions`
- 只加载 **已编译的 `.js` 文件**，不支持直接加载 `.ts`

**当前插件状态：**
```json
{
  "main": "index.ts",  // ❌ 需要改为 dist/index.js
  "clawdbot": {
    "extensions": ["./index.ts"]  // ❌ 需要编译
  }
}
```

---

## 解决方案

### 方案 1：在宿主机编译（推荐）

**步骤：**

1. **安装 TypeScript**
   ```bash
   cd /home/ubuntu/work/QuantClaw/extensions/quantclaw-auth
   npm install --save-dev typescript @types/node
   ```

2. **创建 tsconfig.json**
   ```bash
   npx tsc --init \
     --target ES2020 \
     --module ESNext \
     --moduleResolution node \
     --outDir dist \
     --declaration \
     --esModuleInterop \
     --skipLibCheck
   ```

3. **编译**
   ```bash
   npx tsc
   ```

4. **修改 package.json**
   ```json
   {
     "main": "dist/index.js",
     "clawdbot": {
       "extensions": ["./dist/index.js"]
     }
   }
   ```

5. **重启容器**
   ```bash
   cd /home/ubuntu/work/Docker/openclaw-2026.5.18
   sudo docker compose restart openclaw-gateway
   ```

---

### 方案 2：在容器内编译

**优点**：开发时自动重新编译  
**缺点**：需要修改 Docker 镜像，增加体积

1. **修改 docker-compose.yml**，添加编译脚本：
   ```yaml
   openclaw-gateway:
     command: >
       sh -c "
       cd /home/node/.openclaw/npm/node_modules/quantclaw-auth &&
       npm install && npx tsc &&
       cd /home/node && node dist/index.js gateway --bind lan --port 18789
       "
   ```

2. **重启**：
   ```bash
   sudo docker compose up -d --force-recreate
   ```

---

## 验证插件加载

```bash
# 1. 检查插件目录
sudo docker exec openclaw-2026518-openclaw-gateway-1 \
  ls -la /home/node/.openclaw/npm/node_modules/quantclaw-auth/dist/

# 2. 查看 Gateway 日志
sudo docker logs openclaw-2026518-openclaw-gateway-1 2>&1 | grep -i "quantclaw"

# 3. 检查已加载插件
sudo docker logs openclaw-2026518-openclaw-gateway-1 2>&1 | grep "http server listening"
# 应该看到：(9 plugins: ..., quantclaw-auth, ...)
```

---

## 配置说明

**已添加的配置**（在 `/home/ubuntu/.openclaw/openclaw.json`）：

```json
{
  "plugins": {
    "entries": {
      "quantclaw-auth": {
        "enabled": true,
        "config": {
          "dataPath": "/home/node/.openclaw/quantclaw-users.yaml",
          "workspaceBase": "/home/node/quantclaw-users",
          "webhookPath": "/webhook/quantclaw",
          "filterMode": "keywords",
          "autoRegister": true,
          "skillsPath": "/home/ubuntu/work/QuantClaw/skills",
          "templatePath": "/home/ubuntu/work/QuantClaw/templates/agent-workspace"
        }
      }
    }
  }
}
```

**Volume 挂载**（在 `docker-compose.yml`）：

```yaml
volumes:
  - /home/ubuntu/work/QuantClaw/extensions/quantclaw-auth:/home/node/.openclaw/npm/node_modules/quantclaw-auth:ro
```

---

## 下一步

1. 选择方案 1 或方案 2
2. 编译 TypeScript
3. 重启容器
4. 验证插件加载
5. 测试 webhook 端点：`http://localhost:19789/webhook/quantclaw`

---

## 常见问题

**Q: 插件未加载？**
- 检查 `dist/index.js` 是否存在
- 检查 `package.json` 的 `main` 字段
- 查看 Gateway 日志是否有报错

**Q: 编译错误？**
- 确保安装了 `typescript` 和 `@types/node`
- 检查 TypeScript 版本：`npx tsc --version`

**Q: 修改插件后如何生效？**
- 重新编译：`npx tsc`
- 重启 Gateway：`sudo docker compose restart openclaw-gateway`
