# SSH命令参考 - 远程自动化

本参考提供了用于远程服务器自动化、文件传输、隧道和高级操作的基本SSH命令。所有命令设计用于非交互环境（脚本、Claude Code、自动化工具）。

## 基本远程执行

### 单条命令
```bash
# 执行单条命令
ssh user@hostname 'uptime'

# 使用特定密钥执行
ssh -i ~/.ssh/id_rsa user@hostname 'ls -la'

# 执行多条命令（顺序）
ssh user@hostname 'cd /var/log && tail -n 20 syslog'

# 使用sudo执行（sudoers中需要NOPASSWD）
ssh user@hostname 'sudo systemctl restart nginx'
```

### 使用SSH配置别名
```bash
# 使用此技能设置后
ssh myserver 'whoami && hostname'

# 链式命令
ssh myserver 'cd /app && git pull && npm install'
```

## 端口转发和隧道

### 本地端口转发
将本地端口转发到远程服务（本地访问远程服务）：

```bash
# 将本地8080转发到远程端口80
ssh -L 8080:localhost:80 user@hostname
# 访问：http://localhost:8080

# 通过跳板服务器转发到不同的远程主机
ssh -L 8080:database.example.com:5432 user@jumphost
# 通过jumphost访问远程数据库

# 多个转发
ssh -L 8080:localhost:80 -L 3306:localhost:3306 user@hostname

# 后台隧道（非阻塞）
ssh -f -N -L 8080:localhost:80 user@hostname
# -f: 后台模式
# -N: 不执行命令（仅隧道）
```

**自动化用例：**
- 在本地访问远程web管理面板
- 连接到远程数据库而不暴露端口
- 通过堡垒主机访问内部API

### 远程端口转发
将远程端口转发到本地服务（将本地服务暴露给远程）：

```bash
# 使本地服务可从远程访问
ssh -R 8080:localhost:3000 user@hostname
# 远程服务器可通过其端口8080访问localhost:3000

# 将本地开发服务器暴露给远程
ssh -R 9000:localhost:9000 user@publicserver
```

**自动化用例：**
- Webhook测试（将本地服务器暴露到互联网）
- 远程访问本地开发环境
- 无需防火墙更改即可临时暴露服务

### 动态端口转发（SOCKS代理）
创建SOCKS代理以通过远程服务器路由流量：

```bash
# 在本地端口1080创建SOCKS5代理
ssh -D 1080 user@hostname

# 后台SOCKS代理
ssh -f -N -D 1080 user@hostname

# 与curl一起使用
curl --socks5 localhost:1080 https://example.com

# 与浏览器一起使用（配置SOCKS5: localhost:1080）
```

**自动化用例：**
- 通过远程服务器路由浏览器自动化
- 访问地理限制服务
- 从不同网络位置测试应用程序
- 绕过自动化脚本的防火墙限制

### 保持隧道活跃
```bash
# 带保活的隧道（防止超时）
ssh -o ServerAliveInterval=60 -L 8080:localhost:80 user@hostname

# 持久后台隧道
ssh -f -N -o ServerAliveInterval=60 -o ServerAliveCountMax=3 \
  -L 8080:localhost:80 user@hostname
```

## 文件传输

### SCP（安全复制）
```bash
# 上传文件到远程
scp file.txt user@hostname:/path/to/destination/

# 使用别名上传
scp file.txt myserver:/var/www/html/

# 从远程下载文件
scp user@hostname:/path/file.txt ./local/

# 递归复制目录
scp -r /local/dir user@hostname:/remote/dir/

# 带压缩复制（大型文件更快）
scp -C large-file.zip user@hostname:/path/

# 保留时间戳和权限
scp -p file.txt user@hostname:/path/

# 使用特定端口复制
scp -P 2222 file.txt user@hostname:/path/

# 带进度复制（详细模式）
scp -v file.txt user@hostname:/path/
```

### SFTP（安全FTP）
```bash
# 非交互式SFTP（批处理模式）
sftp -b commands.txt user@hostname

# 示例commands.txt:
# cd /remote/dir
# put local-file.txt
# get remote-file.txt
# bye

# 通过管道执行单条命令
echo "put file.txt" | sftp user@hostname:/remote/dir/

# 下载多个文件
echo -e "cd /logs\nmget *.log\nbye" | sftp user@hostname
```

### Rsync over SSH（推荐用于自动化）
```bash
# 同步目录（保留权限、时间戳）
rsync -avz /local/dir/ user@hostname:/remote/dir/

# 带进度同步
rsync -avz --progress /local/dir/ user@hostname:/remote/dir/

# 带删除同步（镜像 - 删除源中不存在的文件）
rsync -avz --delete /local/dir/ user@hostname:/remote/dir/

# 排除模式
rsync -avz --exclude '*.log' --exclude 'node_modules/' \
  /local/dir/ user@hostname:/remote/dir/

# 试运行（预览更改而不执行）
rsync -avz --dry-run /local/dir/ user@hostname:/remote/dir/

# 自定义SSH端口
rsync -avz -e "ssh -p 2222" /local/dir/ user@hostname:/remote/dir/

# 使用别名同步
rsync -avz --progress /local/app/ myserver:/var/www/app/

# 带时间戳备份
rsync -avz /local/data/ myserver:/backup/data-$(date +%Y%m%d)/

# 仅同步较新文件
rsync -avzu /local/dir/ myserver:/remote/dir/
```

**Rsync自动化优势：**
- 仅传输更改的文件（高效）
- 恢复中断的传输
- 保留权限和时间戳
- 支持复杂排除模式
- 试运行模式用于测试

## 跳板主机（堡垒服务器）

### ProxyJump（现代方法）
```bash
# 通过单个跳板主机连接
ssh -J bastion.example.com user@internal.local

# 多次跳转
ssh -J bastion1,bastion2 user@final-destination

# 配合文件传输
scp -J bastion.example.com file.txt user@internal:/path/

# 配合端口转发
ssh -J bastion.example.com -L 8080:localhost:80 user@internal
```

### SSH配置的跳板主机
添加到`~/.ssh/config`：
```
Host bastion
    HostName bastion.example.com
    User admin
    IdentityFile ~/.ssh/id_bastion

Host internal
    HostName 10.0.0.5
    User admin
    ProxyJump bastion
    IdentityFile ~/.ssh/id_internal
```

然后简单地：
```bash
ssh internal
scp file.txt internal:/path/
```

## 连接复用（性能优化）

重用单个SSH连接用于多个会话（后续连接更快）：

### SSH配置设置
添加到`~/.ssh/config`：
```
Host *
    ControlMaster auto
    ControlPath ~/.ssh/sockets/%r@%h-%p
    ControlPersist 600
```

创建套接字目录：
```bash
mkdir -p ~/.ssh/sockets
```

### 优势
- 首次连接：正常速度
- 后续连接：几乎瞬时
- 共享认证（无需重新认证）
- 减少服务器负载

### 手动控制
```bash
# 启动主连接
ssh -M -S ~/.ssh/control-myserver user@hostname

# 使用现有连接
ssh -S ~/.ssh/control-myserver user@hostname 'command'

# 检查连接状态
ssh -O check -S ~/.ssh/control-myserver user@hostname

# 关闭主连接
ssh -O exit -S ~/.ssh/control-myserver user@hostname
```

## 高级SSH配置

### 完整示例（`~/.ssh/config`）
```
# 所有主机的默认设置
Host *
    ServerAliveInterval 60
    ServerAliveCountMax 3
    TCPKeepAlive yes
    ControlMaster auto
    ControlPath ~/.ssh/sockets/%r@%h-%p
    ControlPersist 600

# 生产服务器
Host prod
    HostName prod.example.com
    User deploy
    Port 2222
    IdentityFile ~/.ssh/id_prod
    IdentitiesOnly yes
    ForwardAgent no

# 带端口转发的开发服务器
Host dev
    HostName dev.example.com
    User developer
    IdentityFile ~/.ssh/id_dev
    LocalForward 8080 localhost:80
    LocalForward 3306 localhost:3306

# 跳板主机配置
Host bastion
    HostName bastion.example.com
    User admin
    IdentityFile ~/.ssh/id_bastion

Host internal-*
    ProxyJump bastion
    User admin
    IdentityFile ~/.ssh/id_internal

# 多个服务器的通配符
Host server-*
    User root
    IdentityFile ~/.ssh/id_servers
    StrictHostKeyChecking no
```

### 配置选项解释
```
ServerAliveInterval 60      # 每60秒发送一次保活
ServerAliveCountMax 3       # 3次失败保活后断开
TCPKeepAlive yes           # 启用TCP级保活
IdentitiesOnly yes         # 仅使用指定密钥（防止尝试所有密钥）
StrictHostKeyChecking no   # 自动接受主机密钥（谨慎使用）
ForwardAgent yes           # 转发SSH代理（安全风险）
Compression yes            # 启用压缩（适合慢速网络）
Port 2222                  # 自定义SSH端口
LogLevel QUIET             # 减少详细程度
ConnectTimeout 10          # 连接超时秒数
```

## 自动化安全最佳实践

### 密钥管理
```bash
# 为自动化生成专用密钥（无密码）
ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_automation -C "automation-key"

# 检查密钥指纹
ssh-keygen -lf ~/.ssh/id_automation.pub

# 复制密钥到服务器
ssh-copy-id -i ~/.ssh/id_automation.pub user@hostname
```

### 在服务器上限制密钥使用
在服务器上编辑`~/.ssh/authorized_keys`：
```
# 限制到特定命令
command="/usr/local/bin/deploy-script" ssh-ed25519 AAAAC3... automation-key

# 限制源IP
from="192.168.1.0/24" ssh-ed25519 AAAAC3... automation-key

# 禁用转发
no-port-forwarding,no-X11-forwarding,no-agent-forwarding ssh-ed25519 AAAAC3... automation-key

# 组合限制
command="/usr/local/bin/deploy",from="192.168.1.100",no-port-forwarding ssh-ed25519 AAAAC3... automation-key
```

### 服务器加固（`/etc/ssh/sshd_config`）
```bash
# 禁用密码认证
PasswordAuthentication no
PubkeyAuthentication yes

# 禁用root登录
PermitRootLogin no

# 更改默认端口
Port 2222

# 限制用户
AllowUsers deploy automation

# 禁用空密码
PermitEmptyPasswords no

# 重启SSH服务
sudo systemctl restart sshd
```

## 故障排除

### 连接问题
```bash
# 详细调试
ssh -v user@hostname
ssh -vv user@hostname  # 更详细
ssh -vvv user@hostname  # 最详细

# 不执行命令测试连接
ssh -T user@hostname

# 测试端口是否开放
telnet hostname 22
nc -zv hostname 22

# 使用特定密钥测试
ssh -i ~/.ssh/id_test -vvv user@hostname
```

### 权限问题
```bash
# 修复本地SSH目录权限
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_*
chmod 644 ~/.ssh/id_*.pub
chmod 644 ~/.ssh/config
chmod 644 ~/.ssh/known_hosts

# 修复远程权限（在服务器上运行）
ssh user@hostname 'chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys'
```

### 主机密钥问题
```bash
# 删除旧主机密钥
ssh-keygen -R hostname

# 按IP删除
ssh-keygen -R 192.168.1.100

# 检查已知主机密钥
ssh-keygen -F hostname

# 禁用主机密钥检查（不建议用于生产）
ssh -o StrictHostKeyChecking=no user@hostname
```

### 认证问题
```bash
# 检查正在使用哪个密钥
ssh -v user@hostname 2>&1 | grep "Offering public key"

# 仅强制使用特定密钥
ssh -o IdentitiesOnly=yes -i ~/.ssh/id_specific user@hostname

# 检查服务器端认证日志
ssh user@hostname 'sudo tail -f /var/log/auth.log'

# 测试公钥认证
ssh -o PreferredAuthentications=publickey user@hostname
```

## 自动化模式

### 并行执行
```bash
# 并行在多个服务器上执行
for server in server1 server2 server3; do
    ssh $server 'uptime' &
done
wait

# 带错误处理
for server in server1 server2 server3; do
    (ssh $server 'command' && echo "$server: OK" || echo "$server: FAILED") &
done
wait
```

### 部署脚本示例
```bash
#!/bin/bash
SERVER="myserver"
APP_DIR="/var/www/app"

# 拉取最新代码
ssh $SERVER "cd $APP_DIR && git pull origin main"

# 安装依赖
ssh $SERVER "cd $APP_DIR && npm install --production"

# 构建应用程序
ssh $SERVER "cd $APP_DIR && npm run build"

# 重启服务
ssh $SERVER "sudo systemctl restart myapp"

# 验证
ssh $SERVER "curl -f http://localhost:3000/health || exit 1"

echo "部署完成"
```

### 备份脚本示例
```bash
#!/bin/bash
SERVER="myserver"
BACKUP_DIR="/backup"
DATE=$(date +%Y%m%d)

# 创建远程备份
ssh $SERVER "tar -czf /tmp/backup-$DATE.tar.gz /var/www/app"

# 下载备份
scp $SERVER:/tmp/backup-$DATE.tar.gz $BACKUP_DIR/

# 清理远程
ssh $SERVER "rm /tmp/backup-$DATE.tar.gz"

# 仅保留最近7天
find $BACKUP_DIR -name "backup-*.tar.gz" -mtime +7 -delete

echo "备份完成: backup-$DATE.tar.gz"
```

### 健康检查脚本
```bash
#!/bin/bash
SERVERS="server1 server2 server3"

for server in $SERVERS; do
    echo "检查 $server..."

    # 检查运行时间
    ssh $server 'uptime'

    # 检查磁盘空间
    ssh $server 'df -h | grep -E "/$|/var"'

    # 检查内存
    ssh $server 'free -h'

    # 检查服务状态
    ssh $server 'systemctl is-active nginx'

    echo "---"
done
```

## 与tmux集成（长时间运行的任务）

### 启动后台任务
```bash
# 在tmux中启动部署
ssh myserver "tmux new-session -d -s deploy 'cd /app && ./deploy.sh'"

# 检查进度
ssh myserver "tmux capture-pane -t deploy -p | tail -20"

# 附加到会话（交互式）
ssh myserver -t "tmux attach -t deploy"

# 完成后终止会话
ssh myserver "tmux kill-session -t deploy"
```

### 列出和管理会话
```bash
# 列出所有tmux会话
ssh myserver "tmux ls"

# 检查会话是否存在
ssh myserver "tmux has-session -t deploy 2>/dev/null && echo 'exists' || echo 'not found'"

# 发送命令到现有会话
ssh myserver "tmux send-keys -t deploy 'ls -la' C-m"

# 捕获完整会话输出
ssh myserver "tmux capture-pane -t deploy -p -S -"
```

## 性能提示

### 慢速网络压缩
```bash
# 启用压缩
ssh -C user@hostname

# 在配置中：
Host slowserver
    Compression yes
```

### 减少延迟
```bash
# 禁用DNS查找
ssh -o GSSAPIAuthentication=no user@hostname

# 使用连接复用（见前文）
```

### 批量操作
```bash
# 使用单个SSH连接执行多条命令
ssh user@hostname 'bash -s' << 'EOF'
cd /app
git pull
npm install
npm run build
sudo systemctl restart myapp
EOF
```

## 参考资料

- [OpenSSH手册](https://www.openssh.com/manual.html)
- [SSH配置文件格式](https://man.openbsd.org/ssh_config)
- 手册页：`man ssh`、`man ssh_config`、`man scp`、`man sftp`
