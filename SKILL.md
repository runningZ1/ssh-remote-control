---
name: ssh-remote-control
description: 智能代理的远程服务器操作完整指南。用自动化工作流程替代传统手动服务器配置和管理。
---

# SSH远控 - 代理操作手册

## 概述

执行传统开发人员手动完成的远程服务器操作：

- **初始设置**：从零建立无密码SSH访问
- **SSL证书**：使用DNS验证颁发Let's Encrypt证书（Cloudflare、阿里云、腾讯云、DNSPod）
- **连接稳定性**：keepalive + tmux保持长时间任务稳定
- **高级网络**：端口转发、SSH隧道、SOCKS代理、跳板
- **文件操作**：SCP、SFTP、rsync部署和备份
- **生产操作**：部署、健康检查、监控

---

## 🔴 重要：远程/本地操作隔离规则

### 操作模式切换

**一旦用户提出使用此技能连接远程服务器，后续所有操作默认在远程服务器上执行，直到用户明确要求切换到本地操作。**

#### 远程操作模式（默认）
- 使用 `ssh <别名> "命令"` 执行所有操作
- 文件编辑使用远程编辑方式（见下文）
- 代码修改在远程服务器上进行
- 明确标注 "在远程服务器上执行"

#### 本地操作模式
- 仅当用户明确说明 "在本地"、"本地操作"、"切换到本地" 时
- 使用本地工具（Read、Edit、Write）
- 明确标注 "在本地执行"

#### 模式切换示例
```
用户: "帮我连接服务器 192.168.1.100"
→ 进入远程操作模式

用户: "修改 /opt/app/config.py 文件"
→ 在远程服务器上修改

用户: "现在在本地修改 README.md"
→ 切换到本地操作模式

用户: "继续在服务器上部署"
→ 切换回远程操作模式
```

---

## 远程文件编辑最佳实践

### ❌ 避免：PowerShell 转义问题

**不要使用内联 sed/awk 命令**，会遇到多层转义问题：
```bash
# ❌ 错误示例 - PowerShell 转义地狱
ssh server "sed -i 's/old/new/' file.txt"
```

### ✅ 推荐方法

#### 方法1：使用 heredoc（小文件）
```bash
ssh server "cat > /path/to/file.txt << 'EOF'
文件内容
多行内容
EOF"
```

#### 方法2：使用 SCP 上传（推荐）
```bash
# 1. 创建本地临时文件
cat > /tmp/temp_file.txt << 'EOF'
文件内容
EOF

# 2. 上传到远程
scp /tmp/temp_file.txt server:/path/to/file.txt

# 3. 清理本地临时文件
rm /tmp/temp_file.txt
```

#### 方法3：使用 Python 脚本（复杂编辑）
```python
import paramiko

# 通过 SFTP 读取、修改、写回
ssh = paramiko.SSHClient()
ssh.connect(server_ip, username=username, password=password)
sftp = ssh.open_sftp()

# 读取
with sftp.open('/path/to/file.txt', 'r') as f:
    content = f.read()

# 修改
new_content = content.replace('old', 'new')

# 写回
with sftp.open('/path/to/file.txt', 'w') as f:
    f.write(new_content)

sftp.close()
ssh.close()
```

#### 方法4：使用 tmux + vim（交互式）
```bash
# 在 tmux 会话中使用 vim
ssh server -t "tmux new-session -s edit 'vim /path/to/file.txt'"
```

---

## 触发条件

**使用此技能**：
- 用户提供服务器凭证（IP、用户名、密码）并希望获得服务器访问
- 用户要求"连接服务器"、"设置SSH"、"配置HTTPS"、"部署"
- 用户需要"端口转发"、"创建隧道"、"同步目录"

**不要使用**：
- 服务器已配置SSH密钥（用`ssh <主机> "whoami"`测试）
- 目标不是Linux服务器
- 用户明确要求基于密码的认证

---

## 📋 必需的用户输入

### 初始连接信息

用户必须提供以下信息才能开始：

1. **服务器IP地址**（必需）
   - 格式：`192.168.1.100` 或 `38.76.206.12`
   - 示例：`154.217.245.99`

2. **用户名**（必需）
   - 通常是 `root` 或其他用户名
   - 示例：`root`、`ubuntu`、`admin`

3. **密码**（必需）
   - 服务器登录密码
   - 注意：密码仅用于初始设置，之后使用密钥认证

4. **SSH别名**（可选，建议提供）
   - 简短易记的名称
   - 示例：`myserver`、`prod1`、`dev-server`
   - 如未提供，将使用 IP 地址作为默认别名

### 输入示例

```
用户输入示例1：
"帮我连接服务器 192.168.1.100，用户名 root，密码 MyPass123"

用户输入示例2：
"配置SSH到 38.76.206.12
用户名：ubuntu
密码：SecurePass456
别名：webserver"

用户输入示例3：
"连接服务器
IP: 154.217.245.99
User: root
Password: P@ssw0rd
Alias: prod-server"
```

### 提取信息流程

1. 从用户消息中提取 IP、用户名、密码
2. 验证 IP 格式是否正确
3. 如果缺少信息，主动询问用户
4. 确认信息后开始执行

---

## 工作流程

### SSH初始设置

**前提**：用户已提供 IP、用户名、密码

**步骤1：进入项目目录**
```bash
cd scripts
```

**步骤2：安装依赖**
```bash
python -m pip install paramiko -q && python -c "import paramiko; print('ok')"
```

**步骤3：测试连接并启用公钥认证**
```bash
python setup_ssh_auth.py <IP> <用户名> <密码>
```
- 测试密码SSH连接
- 启用PubkeyAuthentication
- 安装tmux（会话持久性）

**步骤4：生成专用SSH密钥**
```bash
python generate_ssh_key.py <IP>
```
- 创建无密码保护的Ed25519密钥对

**步骤5：上传公钥**
```bash
python upload_ssh_key.py <IP> <用户名> <密码>
```
- 通过SFTP追加到`~/.ssh/authorized_keys`

**步骤6：配置SSH别名**
```bash
python finalize_ssh_config.py <IP> <用户名> <别名>
```
- 修复私钥权限
- 配置SSH别名（Host别名、keepalive设置）

**步骤7：验证**
```bash
ssh <别名> "whoami && hostname"
```

### 日常使用（远程操作模式）

```bash
# 执行命令
ssh <别名> "cd /project && git pull && npm install"

# 上传文件
scp local_file.txt <别名>:/remote/path/

# 下载文件
scp <别名>:/remote/path/file.txt ./
```

---

## 长时间运行任务

**必须使用tmux**（超过2分钟的操作）：
- 部署、构建、大型文件传输、数据库迁移、编译

**手动使用tmux**：
```bash
# 启动
ssh <别名> "tmux new-session -d -s deploy 'cd /app && npm install && npm run build'"

# 检查进度
ssh <别名> "tmux capture-pane -t deploy -p | tail -50"

# 完成后清理
ssh <别名> "tmux kill-session -t deploy"
```

**或使用tmux_helper.py**：
```bash
python tmux_helper.py run <别名> <会话名> '<命令>'
python tmux_helper.py check <别名> <会话名>
python tmux_helper.py list <别名>
python tmux_helper.py kill <别名> <会话名>
```

---

## SSL证书设置

### 前提条件
- 域名已注册且DNS由支持提供商管理
- 域名A记录指向服务器IP
- Nginx已安装，端口80和443开放

### 步骤1：获取DNS API凭证

| 提供商 | 获取链接 |
|--------|----------|
| Cloudflare | https://dash.cloudflare.com/profile/api-tokens |
| 阿里云 | https://ram.console.aliyun.com/manage/ak |
| 腾讯云 | https://console.cloud.tencent.com/cam/capi |
| DNSPod | https://console.dnspod.cn/account/token/token |

### 步骤2：设置环境变量

```bash
# Cloudflare
export CF_Token='your_token'

# 阿里云
export Ali_Key='your_key'
export Ali_Secret='your_secret'

# 腾讯云
export Tencent_SecretId='your_id'
export Tencent_SecretKey='your_key'

# DNSPod
export DP_Id='your_id'
export DP_Key='your_token'
```

### 步骤3：颁发证书
```bash
# 基本证书
python setup_ssl.py <别名> <域名> <DNS提供商> --email <邮箱>

# 通配符证书
python setup_ssl.py <别名> <域名> <DNS提供商> --wildcard --email <邮箱>
```

### 步骤4：配置Nginx
```bash
python configure_nginx_ssl.py <别名> <域名> [选项]

# 选项：
#   --wildcard    通配符证书
#   --root 路径   文档根目录（默认：/var/www/html）
```

### 验证
```bash
curl -I https://<域名>
ssh <别名> "openssl x509 -in /etc/nginx/ssl/<域名>.crt -noout -dates"
```

---

## 故障排除

| 问题 | 解决方案 |
|------|----------|
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | `ssh-keygen -R <服务器IP>` |
| 私钥权限错误 | 重新运行 finalize_ssh_config.py |
| 公钥认证失败 | 检查sshd配置和authorized_keys权限 |

```bash
# 诊断
ssh <别名> "sshd -T | grep -E 'pubkeyauth|authorizedkeys'"
ssh <别名> "ls -l ~/.ssh/authorized_keys"
```

---

## 脚本清单

**注意**：所有脚本路径相对于项目根目录的 `scripts/` 文件夹

| 脚本 | 功能 |
|------|------|
| `setup_ssh_auth.py` | 测试连接、启用公钥认证、安装tmux |
| `generate_ssh_key.py` | 创建无密码SSH密钥对 |
| `upload_ssh_key.py` | 上传公钥到服务器 |
| `finalize_ssh_config.py` | 修复权限、配置SSH别名 |
| `tmux_helper.py` | tmux会话管理工具 |
| `setup_ssl.py` | 自动化SSL证书颁发 |
| `configure_nginx_ssl.py` | 配置Nginx SSL |
| `utils.py` | 共享工具函数库 |

---

## 参考资料

| 文档 | 用途 |
|------|------|
| `references/ssh-commands-reference.md` | 端口转发、隧道、SOCKS代理、文件传输、跳板主机 |
| `references/detailed-guide.md` | 故障排除、边缘情况、平台特定说明 |
| `references/ssl-credentials-guide.md` | DNS API凭证获取说明 |

---

## 成功标准

1. `ssh <别名> "whoami"` 无密码执行成功
2. 域名显示有效HTTPS证书
3. 长时间运行任务无SSH断开
4. 用户确认服务器按预期工作
5. 远程/本地操作明确区分，无混淆

---

## 项目可移植性

**此项目完全可移植**：
- ✅ 无硬编码绝对路径
- ✅ 所有脚本使用相对导入
- ✅ 可移动到任意目录
- ✅ 只需在 `scripts/` 目录下执行脚本

**使用方式**：
```bash
# 无论项目在哪个目录，都进入 scripts 文件夹执行
cd /path/to/project/scripts
python setup_ssh_auth.py <参数>
```
