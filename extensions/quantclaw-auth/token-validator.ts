/**
 * Token 验证器
 * 调用外部接口验证 token 真实性
 */

import * as https from 'https';
import * as http from 'http';

export interface TokenValidationResult {
  valid: boolean;
  status?: number;
  userId?: string;
  message?: string;
}

export interface TokenValidatorConfig {
  apiUrl: string;              // 验证接口 URL
  apiMethod?: string;          // HTTP method (默认 POST)
  apiHeaders?: Record<string, string>;  // 额外 headers
  showType?: number;           // show_type 参数
  timeoutMs?: number;          // 超时时间
}

export class TokenValidator {
  private config: TokenValidatorConfig;

  constructor(config: TokenValidatorConfig) {
    this.config = {
      apiMethod: 'POST',
      showType: 2,
      timeoutMs: 5000,
      ...config,
    };
  }

  /**
   * 验证 token
   */
  async validate(token: string): Promise<TokenValidationResult> {
    if (!this.config.apiUrl) {
      // 如果未配置验证 URL，直接通过（向后兼容）
      return { valid: true };
    }

    try {
      const result = await this.callApi(token);
      
      // 根据返回的 status 和 info 判断
      // status === 1 且 info 不是 "nologin" 才认为有效
      if (result.status === 1) {
        // 检查 info 是否为对象（有效登录）还是字符串 "nologin"
        if (typeof result.info === 'object' && result.info !== null) {
          const userType = result.info.user_type || '';
          if (userType && userType.trim() !== '') {
            return {
              valid: true,
              status: result.status,
              userId: result.info.user_id || result.info.email,
            };
          }
        }
      }
      
      // 无效 token
      return {
        valid: false,
        status: result.status,
        message: result.info === 'nologin' ? 'Token not logged in' : (result.message || 'Invalid token'),
      };
    } catch (error: any) {
      // 网络错误或超时，记录日志但不阻止（可配置）
      console.error('[TokenValidator] Validation failed:', error.message);
      return {
        valid: false,
        message: `Validation error: ${error.message}`,
      };
    }
  }

  private async callApi(token: string): Promise<any> {
    return new Promise((resolve, reject) => {
      const url = new URL(this.config.apiUrl);
      const isHttps = url.protocol === 'https:';
      const lib = isHttps ? https : http;

      // 使用 form-urlencoded 格式（正确的 API 格式）
      const params = new URLSearchParams({
        show_type: String(this.config.showType || 2),
        usertoken: token,  // 注意：参数名是 usertoken 不是 token
        app_v: '1.0.1',
        lang: '1',
      });
      const postData = params.toString();

      const options = {
        hostname: url.hostname,
        port: url.port || (isHttps ? 443 : 80),
        path: url.pathname + url.search,
        method: this.config.apiMethod,
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
          'Content-Length': Buffer.byteLength(postData),
          ...this.config.apiHeaders,
        },
        timeout: this.config.timeoutMs,
      };

      const req = lib.request(options, (res) => {
        let data = '';

        res.on('data', (chunk) => {
          data += chunk;
        });

        res.on('end', () => {
          try {
            const json = JSON.parse(data);
            resolve(json);
          } catch (e) {
            reject(new Error(`Invalid JSON response: ${data}`));
          }
        });
      });

      req.on('error', (e) => {
        reject(e);
      });

      req.on('timeout', () => {
        req.destroy();
        reject(new Error('Request timeout'));
      });

      req.write(postData);
      req.end();
    });
  }
}
