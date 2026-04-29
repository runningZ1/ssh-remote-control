# SSH Remote Control

[![GitHub](https://img.shields.io/badge/GitHub-ssh--remote--control-blue?logo=github)](https://github.com/runningZ1/ssh-remote-control)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**核心功能**：配置SSH免密连接，之后直接用 `ssh` 命令操作远程服务器。

**GitHub**: https://github.com/runningZ1/ssh-remote-control

---

## 快速开始

### 1. 安装依赖

```bash
pip install paramiko
```

### 2. 配置免密连接（只需一次）

```bash
python sshctrl.py server add <IP> <用户名> <密码> [别名]
```

示例：
```bash
python sshctrl.py server add 38.76.206.12 root mypassword myserver
```

### 3. 日常操作（直接用SSH命令）

```bash
# 执行命令
ssh myserver "docker ps"
ssh myserver "cd /opt/app && git pull"

# 文件传输
scp file.txt myserver:/remote/path/
scp myserver:/remote/path/file.txt ./
```

**不需要任何脚本！**

---

## 工作流程

```
┌─────────────────────────────────────────────────────┐
│  第1步：初始配置（一次性）                             │
│                                                     │
│  python sshctrl.py server add <IP> <用户> <密码>     │
│                                                     │
│  这个命令：                                         │
│  1. 测试密码连接                                    │
│  2. 生成SSH密钥                                     │
│  3. 上传公钥到服务器                                 │
│  4. 配置本地SSH别名                                  │
│  5. 验证免密连接                                    │
└─────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│  第2步：日常操作（直接用原生SSH命令）                 │
│                                                     │
│  ssh <别名> "命令"                                  │
│  scp file.txt <别名>:/path/                          │
│                                                     │
│  不需要任何脚本！                                     │
└─────────────────────────────────────────────────────┘
```

---

## sshctrl 命令

```bash
# 配置服务器免密连接
python sshctrl.py server add <IP> <用户名> <密码> [别名]

# 列出已配置服务器
python sshctrl.py server list

# 移除服务器配置
python sshctrl.py server remove <别名>

# SSH连接
python sshctrl.py server ssh <别名> [命令]
```

---

## SSH 常用命令

### 执行命令

```bash
ssh <别名> "uname -a"
ssh <别名> "df -h"
ssh <别名> "free -h"
ssh <别名> "systemctl status nginx"
ssh <别名> "docker ps"
```

### 文件传输

```bash
# 上传
scp local_file.txt <别名>:/remote/path/
scp -r local_dir/ <别名>:/remote/path/

# 下载
scp <别名>:/remote/path/file.txt ./
scp -r <别名>:/remote/path/dir/ ./
```

### 目录同步

```bash
rsync -avz --progress local_dir/ <别名>:/remote/path/
```

---

## 故障排除

### `REMOTE HOST IDENTIFICATION HAS CHANGED`

```bash
ssh-keygen -R <服务器IP>
```

### 免密连接失败

```bash
# 检查别名配置
cat ~/.ssh/config | grep -A 10 <别名>

# 测试连接
ssh -v <别名> "whoami"
```

### 私钥权限错误

```bash
# Linux/Mac
chmod 600 ~/.ssh/id_ed25519_*

# Windows - 重新运行配置
python sshctrl.py server add <IP> <用户> <密码> [别名]
```

---

## 参考资料

- `references/ssh-commands-reference.md` - SSH命令完整参考
- `references/detailed-guide.md` - 详细指南和故障排除
- `SKILL.md` - 代理操作手册

---

## 安全说明

配置完成后：
- 密码不会保存
- 所有操作使用SSH密钥免密执行
- 建议在服务器上禁用密码认证

---

**最后更新**: 2026-04-30
