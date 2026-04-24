# SSL证书设置 - DNS提供商凭证指南

本指南说明如何从每个支持的DNS提供商获取API凭证，以实现自动化SSL证书颁发。

---

## Cloudflare

### 你需要什么
- **CF_Token**：具有`Zone:DNS:Edit`权限的API令牌
- **CF_Zone_ID**：（可选）用于更快DNS查找的Zone ID

### 如何获取凭证

1. **登录Cloudflare仪表板**
   - 访问：https://dash.cloudflare.com/

2. **创建API令牌**
   - 访问：https://dash.cloudflare.com/profile/api-tokens
   - 点击"创建令牌"
   - 使用"编辑区域DNS"模板
   - 或创建具有以下权限的自定义令牌：
     - 区域 → DNS → 编辑
     - 区域 → 区域 → 读取
   - 选择特定区域或所有区域
   - 点击"继续查看摘要" → "创建令牌"
   - **立即复制令牌**（仅显示一次）

3. **获取Zone ID（可选）**
   - 进入域名的概述页面
   - 向下滚动到右侧栏的"API"部分
   - 复制"Zone ID"

### 使用示例

```bash
export CF_Token='your_cloudflare_api_token_here'
export CF_Zone_ID='your_zone_id_here'  # 可选

python ssh-remote-control/scripts/setup_ssl.py myserver example.com cloudflare --wildcard --email admin@example.com
```

### 故障排除

**错误："Invalid token"**
- 验证令牌具有`Zone:DNS:Edit`权限
- 检查令牌未过期
- 确保令牌用于正确的账户

**错误："Zone not found"**
- 验证域名已添加到Cloudflare
- 检查CF_Zone_ID是否正确（或省略它）

---

## 阿里云

### 你需要什么
- **Ali_Key**：AccessKey ID
- **Ali_Secret**：AccessKey Secret

### 如何获取凭证

1. **登录阿里云控制台**
   - 访问：https://www.aliyun.com/

2. **创建AccessKey**
   - 访问：https://ram.console.aliyun.com/manage/ak
   - 或：控制台 → 访问密钥管理
   - 点击"创建AccessKey"
   - **立即下载并保存AccessKey Secret**（仅显示一次）

3. **安全建议**
   - 使用RAM用户而非root账户
   - 授予最小权限：`AliyunDNSFullAccess`
   - 为RAM用户启用MFA

### 创建RAM用户（推荐）

1. 访问：https://ram.console.aliyun.com/users
2. 点击"创建用户"
3. 启用"编程访问"
4. 保存AccessKey ID和Secret
5. 附加策略：`AliyunDNSFullAccess`

### 使用示例

```bash
export Ali_Key='your_accesskey_id_here'
export Ali_Secret='your_accesskey_secret_here'

python ssh-remote-control/scripts/setup_ssl.py myserver example.com aliyun --wildcard --email admin@example.com
```

### 故障排除

**错误："InvalidAccessKeyId.NotFound"**
- 验证AccessKey ID正确
- 检查AccessKey未删除或禁用

**错误："SignatureDoesNotMatch"**
- 验证AccessKey Secret正确
- 检查是否有额外的空格或换行符

**错误："Forbidden.RAM"**
- 为RAM用户授予`AliyunDNSFullAccess`权限

---

## 腾讯云

### 你需要什么
- **Tencent_SecretId**：SecretId
- **Tencent_SecretKey**：SecretKey

### 如何获取凭证

1. **登录腾讯云控制台**
   - 访问：https://cloud.tencent.com/

2. **创建API密钥**
   - 访问：https://console.cloud.tencent.com/cam/capi
   - 或：控制台 → 访问管理 → API密钥
   - 点击"创建密钥"
   - **立即保存SecretKey**（仅显示一次）

3. **安全建议**
   - 使用子账户而非root账户
   - 授予最小权限：`QcloudDNSPodFullAccess`
   - 为子账户启用MFA

### 创建子账户（推荐）

1. 访问：https://console.cloud.tencent.com/cam
2. 点击"用户" → "创建用户"
3. 选择"编程访问"
4. 保存SecretId和SecretKey
5. 附加策略：`QcloudDNSPodFullAccess`

### 使用示例

```bash
export Tencent_SecretId='your_secret_id_here'
export Tencent_SecretKey='your_secret_key_here'

python ssh-remote-control/scripts/setup_ssl.py myserver example.com tencentcloud --wildcard --email admin@example.com
```

### 故障排除

**错误："AuthFailure.SecretIdNotFound"**
- 验证SecretId正确
- 检查API密钥未删除

**错误："AuthFailure.SignatureFailure"**
- 验证SecretKey正确
- 检查是否有额外的空格或换行符

**错误："UnauthorizedOperation"**
- 为子账户授予`QcloudDNSPodFullAccess`权限

---

## DNSPod

### 你需要什么
- **DP_Id**：API ID
- **DP_Key**：API令牌

### 如何获取凭证

1. **登录DNSPod控制台**
   - 访问：https://console.dnspod.cn/

2. **创建API令牌**
   - 访问：https://console.dnspod.cn/account/token/token
   - 或：控制台 → 账户设置 → API令牌
   - 点击"创建令牌"
   - 输入令牌名称和描述
   - **立即保存API令牌**（仅显示一次）
   - API ID显示在令牌列表中

### 使用示例

```bash
export DP_Id='your_api_id_here'
export DP_Key='your_api_token_here'

python ssh-remote-control/scripts/setup_ssl.py myserver example.com dnspod --wildcard --email admin@example.com
```

### 故障排除

**错误："Authentication failed"**
- 验证DP_Id和DP_Key正确
- 检查令牌未过期或已撤销

**错误："Domain not found"**
- 验证域名已添加到DNSPod
- 检查域名DNS使用DNSPod nameservers

---

## 安全最佳实践

### 1. 使用最小权限
- 仅授予DNS管理权限
- 避免使用root/管理员账户凭证
- 为SSL自动化创建专用API密钥

### 2. 定期轮换凭证
- 每90天更改API密钥
- 撤销未使用或旧的密钥
- 监控API密钥使用日志

### 3. 保护凭证
- 绝不提交凭证到Git
- 使用环境变量（不是硬编码）
- 存储在安全的密码管理器中
- 使用`.gitignore`的`.env`文件

### 4. 监控API使用
- 启用API访问日志
- 设置异常活动警报
- 定期审查API调用历史

### 5. 使用IP白名单（如果可用）
- 仅允许服务器IP访问API
- Cloudflare和阿里云支持IP限制

---

## 快速参考表

| 提供商 | 必需变量 | 可选变量 | 文档链接 |
|----------|-------------------|-------------------|-----------|
| Cloudflare | `CF_Token` | `CF_Zone_ID` | https://dash.cloudflare.com/profile/api-tokens |
| 阿里云 | `Ali_Key`, `Ali_Secret` | - | https://ram.console.aliyun.com/manage/ak |
| 腾讯云 | `Tencent_SecretId`, `Tencent_SecretKey` | - | https://console.cloud.tencent.com/cam/capi |
| DNSPod | `DP_Id`, `DP_Key` | - | https://console.dnspod.cn/account/token/token |

---

## 测试凭证

在运行完整SSL设置之前，测试你的凭证：

### Cloudflare
```bash
export CF_Token='your_token'
curl -X GET "https://api.cloudflare.com/client/v4/user/tokens/verify" \
  -H "Authorization: Bearer $CF_Token"
```

### 阿里云
```bash
# 使用阿里云CLI
aliyun configure set --profile default --access-key-id $Ali_Key --access-key-secret $Ali_Secret
aliyun alidns DescribeDomains
```

### 腾讯云
```bash
# 使用腾讯云CLI
tccli configure set secretId $Tencent_SecretId secretKey $Tencent_SecretKey
tccli dnspod DescribeDomainList
```

---

## 常见问题

### 问题："Rate limit exceeded"
**解决方案**：等待1小时后再试。使用暂存环境进行测试。

### 问题："DNS propagation timeout"
**解决方案**：DNS更改可能需要2-5分钟。脚本会自动等待。

### 问题："Domain not managed by this provider"
**解决方案**：验证域名的nameservers指向DNS提供商。

### 问题："Credentials work in browser but fail in script"
**解决方案**：检查不可见字符（BOM、空格）。重新复制凭证。

---

## 需要帮助？

如果遇到问题：
1. 仔细检查错误消息
2. 验证凭证正确（无额外空格）
3. 确保域名由DNS提供商管理
4. 检查DNS提供商的状态页面是否有关闭
5. 查看detailed-guide.md了解故障排除

对于DNS提供商特定的问题，请查阅上方链接的官方文档。
