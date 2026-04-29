---
name: ssh-remote-control
description: SSH远控技能 - 配置SSH免密连接后，使用原生SSH命令操作远程服务器。
---

# SSH远控 - 代理操作手册

## 概述

建立与远程服务器的SSH免密验证连接。配置完成后，日常操作直接使用原生SSH命令，无需任何脚本。

## 核心原则

**配置免密一次，后续操作只用 `ssh <别名> "命令"`**

---

## 🔴 强制规则：免密操作

### 唯一可用方式
| 阶段 | 操作方式 |
|------|----------|
| 初始配置 | `sshctrl.py server add <IP> <用户> <密码> [别名]` |
| 日常操作 | `ssh <别名> "命令"` |

### 禁止方式
```
❌ python script.py <别名> <命令>     # 禁止用脚本执行
❌ sshpass -p 'pass' ssh <别名>        # 禁止用密码
❌ paramiko + password                # 禁止用密码认证
```

### 为什么
1. **安全**：密码不出现在日志、历史记录
2. **简洁**：直接用系统SSH命令，不依赖脚本
3. **可靠**：SSH客户端已是最优实现

---

## 初始配置SOP

**前提**：用户提供 IP、用户名、密码

**执行**：
```bash
python sshctrl.py server add <IP> <用户名> <密码> [别名]
```

**这个命令做了什么**（透明化流程）：
1. 测试密码SSH连接
2. 生成Ed25519 SSH密钥对
3. 上传公钥到服务器的 `~/.ssh/authorized_keys`
4. 配置本地 `~/.ssh/config` 添加别名和保活参数
5. **验证免密连接是否成功**

**完成后输出**：
```
✅ 服务器配置完成！
验证命令: ssh <别名> "whoami && hostname"
```

---

## 日常操作（配置完成后）

**直接使用原生SSH命令**：
```bash
# 执行命令
ssh <别名> "docker ps"
ssh <别名> "cd /opt/app && git pull && npm install"

# 文件传输
scp local_file.txt <别名>:/remote/path/
scp -r local_dir/ <别名>:/remote/path/

# 下载文件
scp <别名>:/remote/path/file.txt ./
```

**不需要任何脚本，所有操作通过SSH完成。**

---

## 命令参考

### sshctrl（初始配置用）

```bash
# 配置服务器免密连接（仅需执行一次）
python sshctrl.py server add <IP> <用户名> <密码> [别名]

# 列出已配置服务器
python sshctrl.py server list

# 移除服务器配置
python sshctrl.py server remove <别名>

# SSH连接（可选，日常直接用 ssh <别名> 即可）
python sshctrl.py server ssh <别名> [命令]
```

### SSH（日常操作用）

```bash
# 连接并执行命令
ssh <别名> "命令"

# 文件上传
scp local_file.txt <别名>:/remote/path/

# 文件下载
scp <别名>:/remote/path/file.txt ./

# 目录同步
rsync -avz --progress local_dir/ <别名>:/remote/path/
```

---

## 故障排除

| 问题 | 解决 |
|------|------|
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | `ssh-keygen -R <服务器IP>` |
| 免密验证失败 | `ssh <别名> "whoami"` 检查 |
| 私钥权限错误 | `chmod 600 ~/.ssh/id_ed25519_*` |

```bash
# 诊断
ssh <别名> "sshd -T | grep -E 'pubkeyauth|authorizedkeys'"
ssh <别名> "ls -l ~/.ssh/authorized_keys"
```

---

## 文件结构

```
ssh-remote-control/
├── sshctrl.py           # 初始配置CLI（仅用于建立免密连接）
├── SKILL.md             # 本文档
├── README.md            # 用户文档
└── references/         # 参考资料
    └── ssh-commands-reference.md  # SSH命令完整参考
```

---

## 成功标准

1. `ssh <别名> "whoami"` 无需密码执行成功
2. 用户确认可以直接使用SSH命令操作服务器
3. 后续操作不需要任何脚本

---

## 设计理念

**保持简单**：
- 初始配置用一个小脚本
- 日常操作用原生SSH命令
- 不造轮子，不写冗余脚本
