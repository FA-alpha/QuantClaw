/**
 * QuantClaw Authentication Plugin
 * 
 * 功能：
 * 1. API Key 认证
 * 2. 自动注册：首次访问自动创建 User + Agent
 * 3. 消息过滤：只允许量化相关问题
 * 4. CLI 用户管理
 */

import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';

// ============ 类型定义 ============

interface UserRecord {
  userId: string;
  token: string;  // 唯一 token，用于认证和绑定
  agentId: string;
  workspace: string;
  createdAt: string;
  enabled: boolean;
}

interface PluginConfig {
  dataPath: string;
  workspaceBase: string;
  defaultModel: string;
  webhookPath: string;
  webhookSecret?: string;
  filterMode: 'keywords' | 'strict' | 'off';
  autoRegister: boolean;  // 是否允许自动注册
  skillsPath: string;  // QuantClaw 技能路径
  templatePath?: string;  // Agent workspace 模板路径
}

// ============ 消息过滤器 ============

class MessageFilter {
  private static QUANT_KEYWORDS = [
    'btc', 'eth', 'bitcoin', 'ethereum', 'usdt', 'usdc', 'bnb', 'sol', 'xrp',
    '比特币', '以太坊', '加密货币', '数字货币', '币', '链',
    'trade', 'trading', 'buy', 'sell', 'long', 'short', 'position',
    '交易', '买入', '卖出', '做多', '做空', '仓位', '订单',
    'price', 'market', 'chart', 'candle', 'kline', 'volume',
    '价格', '行情', '走势', 'k线', '成交量',
    'strategy', 'backtest', 'grid', 'martingale', 'dca',
    '策略', '回测', '网格', '马丁', '定投', '套利', '量化',
    'whale', 'wallet', 'onchain', 'defi', 'dex',
    '鲸鱼', '钱包', '链上', '大户',
    'fed', 'fomc', 'cpi', 'nfp',
    '美联储', '非农', '利率', '通胀',
    'risk', 'stop', 'loss', 'profit', 'leverage',
    '风险', '止损', '止盈', '杠杆', '爆仓',
    'binance', 'okx', 'bybit', 'coinbase',
    '币安', '交易所', '合约', '现货',
    'fear', 'greed', '恐惧', '贪婪',
    'quant', 'alpha', 'sharpe', 'drawdown',
    '收益', '回撤', '年化',
  ];

  private static BLOCKED_PATTERNS = [
    /^(hi|hello|hey|你好|您好|嗨)[\s!！。,.]*$/i,
    /^(谢谢|thanks|thx)[\s!！。,.]*$/i,
    /^(再见|bye|拜拜)[\s!！。,.]*$/i,
    /天气|weather/i,
    /电影|movie|音乐|music|游戏|game(?!.*crypto)/i,
    /美食|餐厅|restaurant/i,
    /旅游|旅行|travel/i,
  ];

  static check(message: string, mode: string): { ok: boolean; reason?: string } {
    // 暂时关闭过滤
    return { ok: true };
  }
}

// ============ 用户管理器 ============

class UserManager {
  private users = new Map<string, UserRecord>(); // token -> user
  private userIndex = new Map<string, string>(); // userId -> token
  private config: PluginConfig;
  private logger: any;

  constructor(config: PluginConfig, logger: any) {
    this.config = config;
    this.logger = logger;
    this.loadUsers();
  }

  private expandPath(p: string): string {
    return p.replace(/^~/, process.env.HOME || '/root');
  }

  private loadUsers() {
    try {
      const dataPath = this.expandPath(this.config.dataPath);
      if (fs.existsSync(dataPath)) {
        const data = JSON.parse(fs.readFileSync(dataPath, 'utf-8'));
        for (const user of data.users || []) {
          this.users.set(user.token, user);
          this.userIndex.set(user.userId, user.token);
        }
        this.logger.info(`[quantclaw-auth] Loaded ${this.users.size} users`);
      }
    } catch (err) {
      this.logger.warn(`[quantclaw-auth] Failed to load users: ${err}`);
    }
  }

  private saveUsers() {
    try {
      const dataPath = this.expandPath(this.config.dataPath);
      const dir = path.dirname(dataPath);
      if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
      fs.writeFileSync(dataPath, JSON.stringify({ users: Array.from(this.users.values()) }, null, 2));
    } catch (err) {
      this.logger.error(`[quantclaw-auth] Failed to save users: ${err}`);
    }
  }

  findByToken(token: string) { return this.users.get(token); }
  findByUserId(userId: string) { 
    const token = this.userIndex.get(userId);
    return token ? this.users.get(token) : undefined;
  }
  listUsers() { return Array.from(this.users.values()); }

  // 自动注册：绑定客户端传入的 token
  async autoRegister(clientToken: string): Promise<UserRecord> {
    // 使用客户端 token 的 hash 生成用户ID
    const hash = crypto.createHash('sha256').update(clientToken).digest('hex').substring(0, 12);
    const userId = `u_${hash}`;
    const agentId = `qc-${hash}`;
    // 使用 clawd- 前缀，让 Gateway 自动发现（fallback 机制）
    const workspace = this.expandPath(`~/clawd-${agentId}`);

    await this.createWorkspace(workspace, userId);

    const user: UserRecord = {
      userId,
      token: clientToken,  // 绑定客户端的 token
      agentId,
      workspace,
      createdAt: new Date().toISOString(),
      enabled: true,
    };

    this.users.set(clientToken, user);
    this.userIndex.set(userId, clientToken);
    this.saveUsers();
    this.updateAgentConfig(user);

    this.logger.info(`[quantclaw-auth] Registered ${userId} with client token`);
    return user;
  }

  // 手动注册
  async register(userId: string): Promise<UserRecord> {
    if (this.userIndex.has(userId)) throw new Error(`User ${userId} already exists`);

    const token = 'qc_' + crypto.randomBytes(24).toString('hex');
    const agentId = `qc-${userId.toLowerCase().replace(/[^a-z0-9]/g, '-')}`;
    // 使用 clawd- 前缀，让 Gateway 自动发现（fallback 机制）
    const workspace = this.expandPath(`~/clawd-${agentId}`);

    await this.createWorkspace(workspace, userId);

    const user: UserRecord = {
      userId,
      token,
      agentId,
      workspace,
      createdAt: new Date().toISOString(),
      enabled: true,
    };

    this.users.set(token, user);
    this.userIndex.set(userId, token);
    this.saveUsers();
    this.updateAgentConfig(user);

    this.logger.info(`[quantclaw-auth] Registered ${userId}`);
    return user;
  }

  private async createWorkspace(workspace: string, userId: string) {
    if (!fs.existsSync(workspace)) fs.mkdirSync(workspace, { recursive: true });
    
    // 从模板复制 MD 文件
    const templatePath = this.expandPath(this.config.templatePath || '~/work/QuantClaw/templates/agent-workspace');
    
    if (fs.existsSync(templatePath)) {
      const templateFiles = fs.readdirSync(templatePath).filter(f => f.endsWith('.md'));
      
      for (const file of templateFiles) {
        const srcPath = path.join(templatePath, file);
        const destPath = path.join(workspace, file);
        
        if (!fs.existsSync(destPath)) {
          try {
            fs.copyFileSync(srcPath, destPath);
            this.logger.info(`[quantclaw-auth] Copied template: ${file}`);
          } catch (err) {
            this.logger.warn(`[quantclaw-auth] Failed to copy ${file}: ${err}`);
          }
        }
      }
    } else {
      this.logger.warn(`[quantclaw-auth] Template path not found: ${templatePath}, using fallback`);
      
      // 回退：创建基础文件
      const agentsMd = `# ${userId} 量化工作区\n\n## 使用说明\n你可以询问关于加密货币、交易策略、市场分析等问题。\n`;
      fs.writeFileSync(path.join(workspace, 'AGENTS.md'), agentsMd);
      
      const soulMd = `# QuantClaw\n\n## 核心能力\n- 量化分析\n- 数据驱动\n`;
      fs.writeFileSync(path.join(workspace, 'SOUL.md'), soulMd);
    }

    for (const d of ['strategies', 'data', 'backtests', 'analysis']) {
      const p = path.join(workspace, d);
      if (!fs.existsSync(p)) fs.mkdirSync(p);
    }

    // 创建 skills 软链接到 QuantClaw 技能目录
    const skillsPath = this.expandPath(this.config.skillsPath);
    const workspaceSkillsPath = path.join(workspace, 'skills');
    
    if (fs.existsSync(skillsPath) && !fs.existsSync(workspaceSkillsPath)) {
      try {
        fs.symlinkSync(skillsPath, workspaceSkillsPath, 'dir');
        this.logger.info(`[quantclaw-auth] Linked skills to ${workspaceSkillsPath}`);
      } catch (err) {
        this.logger.warn(`[quantclaw-auth] Failed to link skills: ${err}`);
      }
    }
  }

  private updateAgentConfig(user: UserRecord) {
    const cfgPath = this.expandPath('~/.quantclaw/agents-config.json');
    const dir = path.dirname(cfgPath);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

    let cfg: any = { agents: { list: [] } };
    if (fs.existsSync(cfgPath)) {
      try { cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf-8')); } catch {}
    }
    
    if (!cfg.agents) cfg.agents = { list: [] };
    if (!cfg.agents.list) cfg.agents.list = [];

    if (!cfg.agents.list.find((a: any) => a.id === user.agentId)) {
      cfg.agents.list.push({
        id: user.agentId,
        name: `QuantClaw - ${user.userId}`,
        workspace: user.workspace,
        model: this.config.defaultModel,
      });
      // Skills 通过 workspace/skills 软链接自动加载
    }
    
    fs.writeFileSync(cfgPath, JSON.stringify(cfg, null, 2));
  }

  delete(userId: string): boolean {
    const token = this.userIndex.get(userId);
    if (!token) return false;
    this.users.delete(token);
    this.userIndex.delete(userId);
    this.saveUsers();
    return true;
  }

  setEnabled(userId: string, enabled: boolean): boolean {
    const user = this.findByUserId(userId);
    if (!user) return false;
    user.enabled = enabled;
    this.saveUsers();
    return true;
  }

  regenToken(userId: string): string | null {
    const user = this.findByUserId(userId);
    if (!user) return null;
    this.users.delete(user.token);
    user.token = 'qc_' + crypto.randomBytes(24).toString('hex');
    this.users.set(user.token, user);
    this.saveUsers();
    return user.token;
  }
}

// ============ 插件入口 ============

export default function register(api: any) {
  const cfg = api.config?.plugins?.entries?.['quantclaw-auth']?.config || {};
  
  const config: PluginConfig = {
    dataPath: cfg.dataPath || '~/.quantclaw/users.json',
    workspaceBase: cfg.workspaceBase || '~/quantclaw-users',
    defaultModel: cfg.defaultModel || 'openrouter/anthropic/claude-sonnet-4-5',
    webhookPath: cfg.webhookPath || '/webhook/quantclaw',
    webhookSecret: cfg.webhookSecret,
    filterMode: cfg.filterMode || 'keywords',
    autoRegister: cfg.autoRegister ?? true,
    skillsPath: cfg.skillsPath || '~/work/QuantClaw/skills',
    templatePath: cfg.templatePath || '~/work/QuantClaw/templates/agent-workspace',
  };

  const userManager = new UserManager(config, api.logger);

  // ======== Webhook ========
  api.registerHttpRoute({
    path: config.webhookPath,
    handler: async (req: any, res: any) => {
      const sendJson = (data: any) => {
        res.setHeader('Content-Type', 'application/json');
        res.end(JSON.stringify(data));
      };

      try {
        // 读取请求体
        let body: any;
        if (req.body && typeof req.body === 'object') {
          body = req.body;
        } else {
          const chunks: Buffer[] = [];
          for await (const chunk of req) chunks.push(chunk);
          const raw = Buffer.concat(chunks).toString('utf8');
          try { body = JSON.parse(raw); } catch { body = null; }
        }

        if (!body) return sendJson({ success: false, error: 'Invalid request body' });
        if (!body.message) return sendJson({ success: false, error: 'Missing message' });

        // 验证签名（如果配置了）
        if (config.webhookSecret) {
          const sig = req.headers?.['x-quantclaw-signature'];
          const expected = crypto.createHmac('sha256', config.webhookSecret).update(JSON.stringify(body)).digest('hex');
          if (sig !== expected) return sendJson({ success: false, error: 'Invalid signature' });
        }

        let user: UserRecord | undefined;
        let isNewUser = false;

        // 必须提供 token（客户端生成或登录获取）
        if (!body.token) {
          return sendJson({ success: false, error: 'Missing token' });
        }

        // 查找是否已绑定用户
        user = userManager.findByToken(body.token);
        
        if (user) {
          // 已有用户
          if (!user.enabled) return sendJson({ success: false, error: 'User disabled' });
        } else if (config.autoRegister) {
          // 新 token，自动创建用户并绑定
          try {
            user = await userManager.autoRegister(body.token);
            isNewUser = true;
            api.logger.info(`[quantclaw-auth] New user: ${user.userId} bound to token`);
          } catch (err: any) {
            api.logger.error(`[quantclaw-auth] Auto-register failed: ${err.message}`);
            return sendJson({ success: false, error: 'Registration failed' });
          }
        } else {
          return sendJson({ success: false, error: 'Token not registered' });
        }

        // 认证检查请求
        if (body.message === '__auth_check__') {
          return sendJson({ 
            success: true,
            token: user.token,
            userId: user.userId, 
            agentId: user.agentId,
            isNewUser,
          });
        }

        // 消息过滤
        const filter = MessageFilter.check(body.message, config.filterMode);
        if (!filter.ok) {
          return sendJson({ success: false, rejected: true, error: filter.reason });
        }

        api.logger.info(`[quantclaw-auth] ${user.userId}: ${body.message.substring(0, 50)}...`);

        // 返回认证信息
        const sessionId = body.sessionId || 'main';
        sendJson({
          success: true,
          token: user.token,  // 客户端保存此 token
          userId: user.userId,
          agentId: user.agentId,
          sessionKey: `agent:${user.agentId}:${sessionId}`,
          gatewayWs: `ws://127.0.0.1:${api.config?.gateway?.port || 18789}`,
          message: body.message,
          isNewUser,
        });

      } catch (err: any) {
        api.logger.error(`[quantclaw-auth] Error: ${err.message}`);
        sendJson({ success: false, error: 'Internal error' });
      }
    },
  });

  // ======== RPC ========
  api.registerGatewayMethod('quantclaw.verify', ({ params, respond }: any) => {
    const user = userManager.findByToken(params?.token);
    respond(true, user?.enabled ? { valid: true, userId: user.userId, agentId: user.agentId } : { valid: false });
  });

  api.registerGatewayMethod('quantclaw.list', ({ respond }: any) => {
    respond(true, { 
      users: userManager.listUsers().map(u => ({ 
        userId: u.userId, 
        agentId: u.agentId, 
        enabled: u.enabled,
        createdAt: u.createdAt,
      })) 
    });
  });

  // ======== CLI ========
  api.registerCli(({ program }: any) => {
    const qc = program.command('quantclaw').description('QuantClaw 用户管理');

    qc.command('register <userId>').description('手动注册').action(async (userId: string) => {
      try {
        const user = await userManager.register(userId);
        console.log(`✅ 注册成功\n   Token: ${user.token}\n   Agent: ${user.agentId}\n\n⚠️ clawdbot gateway restart 生效`);
      } catch (e: any) { console.error(`❌ ${e.message}`); }
    });

    qc.command('list').description('列出用户').action(() => {
      const users = userManager.listUsers();
      if (!users.length) return console.log('无用户');
      console.log(`\n共 ${users.length} 个用户:\n`);
      users.forEach(u => {
        const status = u.enabled ? '✅' : '🚫';
        console.log(`${status} ${u.userId} | ${u.agentId} | ${u.token.slice(0,15)}...`);
      });
    });

    qc.command('info <userId>').description('详情').option('--show-token', '显示完整Token').action((userId: string, opts: any) => {
      const user = userManager.findByUserId(userId);
      if (!user) return console.log('❌ 用户不存在');
      console.log(`用户: ${user.userId}\nToken: ${opts.showToken ? user.token : user.token.slice(0,15)+'...'}\nAgent: ${user.agentId}\n状态: ${user.enabled ? '启用' : '禁用'}\n创建: ${user.createdAt}`);
    });

    qc.command('delete <userId>').description('删除').action((userId: string) => {
      console.log(userManager.delete(userId) ? '✅ 已删除' : '❌ 用户不存在');
    });

    qc.command('enable <userId>').description('启用').action((userId: string) => {
      console.log(userManager.setEnabled(userId, true) ? '✅ 已启用' : '❌ 用户不存在');
    });

    qc.command('disable <userId>').description('禁用').action((userId: string) => {
      console.log(userManager.setEnabled(userId, false) ? '🚫 已禁用' : '❌ 用户不存在');
    });

    qc.command('regen-token <userId>').description('重新生成Token').action((userId: string) => {
      const token = userManager.regenToken(userId);
      console.log(token ? `✅ 新Token: ${token}` : '❌ 用户不存在');
    });

    qc.command('webhook').description('Webhook信息').action(() => {
      console.log(`
📡 QuantClaw Webhook: ${config.webhookPath}
自动注册: ${config.autoRegister ? '✅' : '❌'}

首次请求 (自动注册):
curl -X POST http://localhost:18789${config.webhookPath} \\
  -H "Content-Type: application/json" \\
  -d '{"message":"查询BTC价格"}'

后续请求 (带token):
curl -X POST http://localhost:18789${config.webhookPath} \\
  -H "Content-Type: application/json" \\
  -d '{"token":"qc_xxx","message":"查询BTC价格"}'
`);
    });

  }, { commands: ['quantclaw'] });

  api.logger.info(`[quantclaw-auth] Loaded (webhook: ${config.webhookPath}, autoRegister: ${config.autoRegister.enabled})`);
}

export const id = 'quantclaw-auth';
export const name = 'QuantClaw Authentication';
