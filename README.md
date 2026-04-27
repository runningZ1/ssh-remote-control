# SSH 远程服务器控制系统

[![GitHub](https://img.shields.io/badge/GitHub-ssh--remote--control-blue?logo=github)](https://github.com/runningZ1/ssh-remote-control)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

一个完整的远程服务器自动化管理工具集，支持从零开始配置SSH密钥认证、SSL证书管理、长时间任务执行等功能。

**GitHub 仓库**: https://github.com/runningZ1/ssh-remote-control

## 目录

- [快速开始](#快速开始)
- [功能特性](#功能特性)
- [安装依赖](#安装依赖)
- [使用指南](#使用指南)
  - [初次连接服务器](#初次连接服务器)
  - [日常服务器操作](#日常服务器操作)
  - [长时间任务管理](#长时间任务管理)
  - [SSL证书配置](#ssl证书配置)
- [脚本说明](#脚本说明)
- [故障排除](#故障排除)

## 快速开始

### 前提条件

- Python 3.7+
- 服务器的IP地址、用户名和密码
- Windows/Linux/macOS 系统

### 5分钟快速配置（推荐方式）

使用统一的CLI工具 `sshctrl`：

```bash
# 1. 安装依赖
python -m pip install paramiko

# 2. 进入项目目录
cd ssh-remote-control

# 3. 一键配置服务器（自动完成SSH密钥生成、上传、配置）
python sshctrl.py server add <服务器IP> <用户名> <密码> [别名]

# 4. 验证连接（无需密码）
ssh <别名> "whoami"
```

**示例**：
```bash
# 配置服务器，一句话搞定
python sshctrl.py server add 38.76.206.12 root mypassword myserver

# 验证
ssh myserver "ls -la"
```

### 传统方式（4个独立脚本）

如果需要分步骤操作，可使用独立脚本：

```bash
# 1. 测试连接并启用公钥认证
python scripts/setup_ssh_auth.py <服务器IP> <用户名> <密码>

# 2. 生成SSH密钥
python scripts/generate_ssh_key.py <服务器IP>

# 3. 上传公钥到服务器
python scripts/upload_ssh_key.py <服务器IP> <用户名> <密码>

# 4. 配置SSH别名
python scripts/finalize_ssh_config.py <服务器IP> <用户名> <别名>
```

## 功能特性

### 核心功能

- ✅ **自动化SSH密钥配置** - 一键从密码认证切换到密钥认证
- ✅ **连接保活机制** - 自动配置keepalive，防止SSH连接超时
- ✅ **tmux会话管理** - 支持长时间运行任务，断线不中断
- ✅ **SSL证书自动化** - 支持Let's Encrypt证书申请和自动续期
- ✅ **多DNS提供商** - 支持Cloudflare、阿里云、腾讯云、DNSPod
- ✅ **Nginx自动配置** - 一键配置HTTPS和SSL证书

### 安全特性

- 🔐 使用Ed25519算法生成高强度密钥
- 🔐 自动修复密钥文件权限
- 🔐 支持SSH配置冲突检测
- 🔐 密码信息不会保存到配置文件

## 安装依赖

```bash
# 安装Python依赖
python -m pip install paramiko

# 验证安装
python -c "import paramiko; print('Paramiko安装成功')"
```

## 使用指南

### 统一CLI工具 sshctrl

推荐使用 `sshctrl.py` 作为统一入口：

```bash
# 服务器管理
python sshctrl.py server add <IP> <用户> <密码> [别名]   # 一键配置
python sshctrl.py server list                              # 列出已配置服务器
python sshctrl.py server remove <别名>                     # 移除服务器
python sshctrl.py server ssh <别名> [命令]                 # SSH连接/执行

# tmux会话管理
python sshctrl.py tmux run <别名> <会话> <命令>           # 后台运行任务
python sshctrl.py tmux check <别名> <会话> [--full]        # 查看输出
python sshctrl.py tmux list <别名>                         # 列出会话
python sshctrl.py tmux attach <别名> <会话>                # 接入会话
python sshctrl.py tmux kill <别名> <会话>                 # 终止会话

# SSL证书
python sshctrl.py ssl issue <域名> <DNS提供商> [--wildcard] # 申请证书
python sshctrl.py ssl nginx <域名> [--root <路径>]         # 配置Nginx

# 快速执行
python sshctrl.py exec <别名> "命令"                      # 执行命令
```

### 独立脚本（旧方式）

如需分步骤操作，可使用 `scripts/` 目录下的独立脚本：

#### 步骤1：测试连接并启用公钥认证

```bash
python scripts/setup_ssh_auth.py <IP> <用户名> <密码>
```

**功能**：
- 测试密码SSH连接是否正常
- 检查并启用服务器的公钥认证
- 自动安装tmux（用于长时间任务）

**示例**：
```bash
python scripts/setup_ssh_auth.py 38.76.206.12 root mypassword
```

#### 步骤2：生成SSH密钥对

```bash
python scripts/generate_ssh_key.py <IP>
```

**功能**：
- 生成Ed25519类型的SSH密钥对
- 密钥文件命名格式：`id_ed25519_<IP格式化>`
- 无密码保护，方便自动化使用

**示例**：
```bash
python scripts/generate_ssh_key.py 38.76.206.12
# 生成文件：~/.ssh/id_ed25519_38_76_206_12 和 id_ed25519_38_76_206_12.pub
```

#### 步骤3：上传公钥到服务器

```bash
python scripts/upload_ssh_key.py <IP> <用户名> <密码>
```

**功能**：
- 通过SFTP上传公钥到服务器
- 自动追加到 `~/.ssh/authorized_keys`
- 设置正确的文件权限

**示例**：
```bash
python scripts/upload_ssh_key.py 38.76.206.12 root mypassword
```

#### 步骤4：配置SSH别名

```bash
python scripts/finalize_ssh_config.py <IP> <用户名> <别名>
```

**功能**：
- 修复私钥文件权限（Windows/Linux兼容）
- 在 `~/.ssh/config` 中添加Host别名
- 配置连接保活参数（ServerAliveInterval=60）

**示例**：
```bash
python scripts/finalize_ssh_config.py 38.76.206.12 root myserver
```

**生成的SSH配置**：
```
Host myserver
    HostName 38.76.206.12
    User root
    IdentityFile ~/.ssh/id_ed25519_38_76_206_12
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

#### 步骤5：验证连接

```bash
ssh <别名> "whoami && hostname"
```

如果输出用户名和主机名，说明配置成功！

### 日常服务器操作

配置完成后，可以直接使用SSH别名进行各种操作：

#### 执行命令

```bash
# 查看系统信息
ssh myserver "uname -a"

# 查看磁盘使用
ssh myserver "df -h"

# 查看内存使用
ssh myserver "free -h"

# 查看Docker容器
ssh myserver "docker ps"

# 多条命令
ssh myserver "cd /opt/myapp && git pull && npm install"
```

#### 文件传输

```bash
# 上传文件
scp local_file.txt myserver:/remote/path/

# 上传目录
scp -r local_dir/ myserver:/remote/path/

# 下载文件
scp myserver:/remote/path/file.txt ./

# 下载目录
scp -r myserver:/remote/path/dir/ ./
```

#### 使用rsync同步

```bash
# 同步本地到远程
rsync -avz --progress local_dir/ myserver:/remote/path/

# 同步远程到本地
rsync -avz --progress myserver:/remote/path/ local_dir/

# 排除特定文件
rsync -avz --exclude 'node_modules' --exclude '.git' local_dir/ myserver:/remote/path/
```

### 长时间任务管理

对于超过2分钟的操作（部署、构建、数据库迁移等），必须使用tmux防止SSH断线导致任务中断。

#### 方式1：直接使用tmux命令

```bash
# 启动后台任务
ssh myserver "tmux new-session -d -s deploy 'cd /app && npm install && npm run build'"

# 查看任务进度
ssh myserver "tmux capture-pane -t deploy -p | tail -50"

# 查看完整输出
ssh myserver "tmux capture-pane -t deploy -p"

# 检查会话是否还在运行
ssh myserver "tmux has-session -t deploy && echo 'Running' || echo 'Finished'"

# 任务完成后清理会话
ssh myserver "tmux kill-session -t deploy"
```

#### 方式2：使用tmux_helper.py脚本

```bash
# 运行任务
python scripts/tmux_helper.py run myserver deploy 'cd /app && npm install && npm run build'

# 检查进度
python scripts/tmux_helper.py check myserver deploy

# 查看完整输出
python scripts/tmux_helper.py check myserver deploy --full

# 终止任务
python scripts/tmux_helper.py kill myserver deploy

# 列出所有会话
python scripts/tmux_helper.py list myserver
```

#### 常见长时间任务示例

```bash
# 部署应用
ssh myserver "tmux new-session -d -s deploy 'cd /opt/myapp && git pull && docker-compose up -d --build'"

# 数据库备份
ssh myserver "tmux new-session -d -s backup 'mysqldump -u root -p database > /backup/db_$(date +%Y%m%d).sql'"

# 大文件下载
ssh myserver "tmux new-session -d -s download 'wget https://example.com/large-file.zip -O /tmp/file.zip'"

# 编译项目
ssh myserver "tmux new-session -d -s build 'cd /opt/project && make clean && make -j4'"
```

### SSL证书配置

使用Let's Encrypt自动申请和配置SSL证书，支持DNS验证方式。

#### 前提条件

1. 域名已注册并指向服务器IP
2. 服务器已安装Nginx
3. 端口80和443已开放
4. 已获取DNS提供商的API凭证

#### 步骤1：获取DNS API凭证

| DNS提供商 | 获取链接 | 所需凭证 |
|-----------|----------|----------|
| Cloudflare | https://dash.cloudflare.com/profile/api-tokens | API Token |
| 阿里云 | https://ram.console.aliyun.com/manage/ak | AccessKey ID + Secret |
| 腾讯云 | https://console.cloud.tencent.com/cam/capi | SecretId + SecretKey |
| DNSPod | https://console.dnspod.cn/account/token/token | ID + Token |

#### 步骤2：设置环境变量

```bash
# Cloudflare
export CF_Token='your_cloudflare_api_token'

# 阿里云
export Ali_Key='your_aliyun_access_key_id'
export Ali_Secret='your_aliyun_access_key_secret'

# 腾讯云
export Tencent_SecretId='your_tencent_secret_id'
export Tencent_SecretKey='your_tencent_secret_key'

# DNSPod
export DP_Id='your_dnspod_id'
export DP_Key='your_dnspod_token'
```

#### 步骤3：申请证书

```bash
# 基本证书（单域名）
python scripts/setup_ssl.py myserver example.com cloudflare --email admin@example.com

# 通配符证书（*.example.com）
python scripts/setup_ssl.py myserver example.com cloudflare --wildcard --email admin@example.com

# 支持的DNS提供商：cloudflare, aliyun, tencent, dnspod
```

**脚本会自动**：
- 安装acme.sh证书管理工具
- 使用DNS验证方式申请证书
- 配置自动续期（每60天检查一次）
- 将证书安装到 `/etc/nginx/ssl/` 目录

#### 步骤4：配置Nginx

```bash
# 基本配置
python scripts/configure_nginx_ssl.py myserver example.com

# 通配符证书配置
python scripts/configure_nginx_ssl.py myserver example.com --wildcard

# 自定义网站根目录
python scripts/configure_nginx_ssl.py myserver example.com --root /var/www/mysite
```

**脚本会自动**：
- 创建Nginx SSL配置文件
- 配置HTTP到HTTPS重定向
- 启用现代SSL/TLS设置
- 重启Nginx服务

#### 步骤5：验证证书

```bash
# 测试HTTPS访问
curl -I https://example.com

# 查看证书有效期
ssh myserver "openssl x509 -in /etc/nginx/ssl/example.com.crt -noout -dates"

# 查看证书详情
ssh myserver "openssl x509 -in /etc/nginx/ssl/example.com.crt -noout -text"
```

#### 证书管理

```bash
# 查看所有证书
ssh myserver "~/.acme.sh/acme.sh --list"

# 手动续期证书
ssh myserver "~/.acme.sh/acme.sh --renew -d example.com --force"

# 查看续期日志
ssh myserver "cat ~/.acme.sh/example.com/example.com.log"

# 证书文件位置
# 私钥：/etc/nginx/ssl/example.com.key
# 证书：/etc/nginx/ssl/example.com.crt
# 完整链：/etc/nginx/ssl/example.com.fullchain.crt
```

## 脚本说明

### 统一CLI工具（推荐）

| 脚本文件 | 功能说明 | 使用场景 |
|---------|---------|---------|
| `sshctrl.py` | 统一CLI入口，管理所有功能 | 日常使用 |

**sshctrl.py 子命令**：
```bash
sshctrl.py server add/list/remove/ssh   # 服务器管理
sshctrl.py tmux run/check/list/attach/kill  # tmux会话
sshctrl.py ssl issue/nginx               # SSL证书
sshctrl.py exec                          # 快速执行
```

### 核心脚本（旧方式）

| 脚本文件 | 功能说明 | 使用场景 |
|---------|---------|---------|
| `setup_ssh_auth.py` | 测试连接、启用公钥认证、安装tmux | 初次配置服务器 |
| `generate_ssh_key.py` | 生成Ed25519 SSH密钥对 | 为每台服务器生成专用密钥 |
| `upload_ssh_key.py` | 上传公钥到服务器authorized_keys | 配置密钥认证 |
| `finalize_ssh_config.py` | 配置SSH别名和连接保活 | 完成SSH配置 |
| `tmux_helper.py` | tmux会话管理工具 | 管理长时间运行任务 |
| `setup_ssl.py` | 自动申请Let's Encrypt证书 | 配置HTTPS |
| `configure_nginx_ssl.py` | 配置Nginx SSL设置 | 启用HTTPS服务 |

### 辅助脚本

| 脚本文件 | 功能说明 |
|---------|---------|
| `check_server.py` | 检查服务器基本信息 |
| `check_logs.py` | 查看服务器日志 |
| `check_analyzer.py` | 分析服务器性能 |
| `check_prompt_reverse_logs.py` | 查看特定服务日志 |
| `check_service_content.py` | 检查服务内容 |
| `fix_cors.py` | 修复CORS配置 |
| `fix_cors_env.py` | 修复CORS环境变量 |
| `fix_error_handling.py` | 修复错误处理 |
| `monitor_logs.py` | 实时监控日志 |
| `test_api_call.py` | 测试API调用 |
| `test_service.py` | 测试服务状态 |

### 连接脚本

| 脚本文件 | 功能说明 |
|---------|---------|
| `connect_server.py` | 使用paramiko连接服务器并执行命令 |

## 故障排除

### 常见问题

#### 1. SSH连接被拒绝

**错误信息**：
```
Permission denied (publickey,password)
```

**解决方案**：
```bash
# 检查服务器SSH配置
ssh myserver "sudo sshd -T | grep -E 'pubkeyauth|passwordauth'"

# 检查authorized_keys权限
ssh myserver "ls -la ~/.ssh/authorized_keys"

# 重新上传公钥
python scripts/upload_ssh_key.py <IP> <用户名> <密码>
```

#### 2. 主机密钥变更警告

**错误信息**：
```
WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!
```

**解决方案**：
```bash
# 删除旧的主机密钥
ssh-keygen -R <服务器IP>

# 或删除整个known_hosts文件
rm ~/.ssh/known_hosts
```

#### 3. 私钥权限错误

**错误信息**：
```
Permissions 0644 for 'id_ed25519_xxx' are too open
```

**解决方案**：
```bash
# 重新运行配置脚本
python scripts/finalize_ssh_config.py <IP> <用户名> <别名>

# 或手动修复权限（Linux/Mac）
chmod 600 ~/.ssh/id_ed25519_*
```

#### 4. SSL证书申请失败

**错误信息**：
```
DNS record not found
```

**解决方案**：
```bash
# 检查域名DNS记录
nslookup example.com

# 检查API凭证是否正确
echo $CF_Token  # Cloudflare
echo $Ali_Key   # 阿里云

# 查看详细错误日志
ssh myserver "cat ~/.acme.sh/acme.sh.log"
```

#### 5. tmux会话找不到

**错误信息**：
```
session not found: deploy
```

**解决方案**：
```bash
# 列出所有tmux会话
ssh myserver "tmux ls"

# 检查任务是否已完成
ssh myserver "ps aux | grep <进程名>"
```

### 诊断命令

```bash
# 测试SSH连接
ssh -v myserver "whoami"

# 查看SSH配置
cat ~/.ssh/config

# 查看服务器SSH配置
ssh myserver "sudo sshd -T"

# 查看服务器日志
ssh myserver "sudo tail -f /var/log/auth.log"

# 测试端口连通性
nc -zv <服务器IP> 22

# 查看本地SSH密钥
ls -la ~/.ssh/
```

## 文件结构

```
ssh-remote-control/
├── README.md                          # 本文档
├── SERVER_CONNECTION.md               # 服务器连接信息（敏感信息，不提交）
├── SKILL.md                          # 技能说明文档
├── sshctrl.py                        # 统一CLI入口（推荐使用）
├── .gitignore                        # Git忽略规则
├── scripts/                          # 核心脚本目录
│   ├── setup_ssh_auth.py            # SSH认证配置
│   ├── generate_ssh_key.py          # 密钥生成
│   ├── upload_ssh_key.py            # 公钥上传
│   ├── finalize_ssh_config.py       # SSH配置完成
│   ├── tmux_helper.py               # tmux会话管理
│   ├── setup_ssl.py                 # SSL证书申请
│   └── configure_nginx_ssl.py       # Nginx SSL配置
├── references/                       # 参考文档目录
│   ├── ssh-commands-reference.md    # SSH命令参考
│   ├── detailed-guide.md            # 详细指南
│   └── ssl-credentials-guide.md     # SSL凭证获取指南
├── connect_server.py                 # 服务器连接脚本
├── check_*.py                        # 各种检查脚本
├── fix_*.py                          # 各种修复脚本
├── test_*.py                         # 各种测试脚本
└── monitor_logs.py                   # 日志监控脚本
```

## 安全建议

1. **使用SSH密钥认证** - 比密码更安全，支持自动化
2. **定期更换密钥** - 建议每6个月更换一次SSH密钥
3. **限制SSH访问** - 配置防火墙规则，只允许特定IP访问
4. **禁用密码登录** - 配置完密钥后，禁用密码认证
5. **使用非标准端口** - 将SSH端口从22改为其他端口
6. **启用双因素认证** - 为SSH添加2FA保护
7. **定期更新系统** - 保持服务器系统和软件最新
8. **监控登录日志** - 定期检查 `/var/log/auth.log`

### 禁用密码登录（可选）

```bash
# 编辑SSH配置
ssh myserver "sudo nano /etc/ssh/sshd_config"

# 修改以下配置
# PasswordAuthentication no
# PubkeyAuthentication yes

# 重启SSH服务
ssh myserver "sudo systemctl restart sshd"
```

## 高级用法

### 端口转发

```bash
# 本地端口转发（访问远程服务）
ssh -L 8080:localhost:80 myserver

# 远程端口转发（让远程访问本地服务）
ssh -R 9000:localhost:3000 myserver

# 动态端口转发（SOCKS代理）
ssh -D 1080 myserver
```

### 跳板机配置

```bash
# 在 ~/.ssh/config 中配置
Host jumphost
    HostName jump.example.com
    User admin

Host target
    HostName 192.168.1.100
    User root
    ProxyJump jumphost
```

### 批量服务器管理

```bash
# 创建服务器列表
servers=("server1" "server2" "server3")

# 批量执行命令
for server in "${servers[@]}"; do
    echo "=== $server ==="
    ssh $server "uptime"
done

# 批量更新
for server in "${servers[@]}"; do
    ssh $server "sudo apt update && sudo apt upgrade -y"
done
```

## 贡献指南

欢迎提交Issue和Pull Request来改进这个项目。

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交Issue。

---

**最后更新**: 2026-04-22
