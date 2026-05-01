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
| 初始配置 | `sshctrl.py server add <host> <用户> <密码> [别名] [--port 端口]` |
| 日常操作 | `ssh <别名> "命令"` |

### 禁止方式
```
❌ python script.py <别名> <命令>     # 禁止用脚本执行
❌ sshpass -p 'pass' ssh <别名>        # 禁止用密码
❌ paramiko + password                # 禁止用密码认证
❌ python <<'PYEOF' ... paramiko ...  # 禁止heredoc内联远控
```

### 为什么
1. **安全**：密码不出现在日志、历史记录
2. **简洁**：直接用系统SSH命令，不依赖脚本
3. **可靠**：SSH客户端已是最优实现

---

## 初始配置SOP

**前提**：用户提供 host（IP或域名）、用户名、密码（可选端口）

**执行**：
```bash
python sshctrl.py server add <host> <用户名> <密码> [别名] [--port 端口]
```

示例（非22端口）：
```bash
python sshctrl.py server add connect.nmb2.seetacloud.com root <密码> seetacloud_20605 --port 20605
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

# 文件传输（推荐 rsync）
rsync 是传输文件/目录的最佳工具，支持增量传输、断点续传、压缩传输、保留属性和进度显示。

```bash
# 传输单个文件
rsync -avz --progress local_file.txt <别名>:/remote/path/

# 传输整个目录（推荐）
rsync -avz --progress local_dir/ <别名>:/remote/path/

# 大文件推荐加上 --partial 支持断点续传
rsync -avz --partial --progress large_file.txt <别名>:/remote/path/

# 非默认SSH端口
rsync -avz -e "ssh -p 2222" local_dir/ <别名>:/remote/path/

# 下载文件
rsync -avz --progress <别名>:/remote/path/file.txt ./
rsync -avz --progress <别名>:/remote/path/folder/ ./local/folder/
```

**rsync 优势**：比 scp 更智能，只传输变化的部分（增量传输），节省时间和流量。适合大文件或目录同步。

**备选：SFTP reget**（当 rsync 未安装或安装失败时）
```bash
# 上传
sftp <别名> << 'EOF'
put local_file.txt /remote/path/
put -r local_dir/ /remote/path/
EOF

# 断点续传下载（大文件推荐）
sftp <别名> << 'EOF'
reget /remote/path/large_file.zip
EOF
```

**备选 scp**（简单场景）：
```bash
scp local_file.txt <别名>:/remote/path/
scp -r local_dir/ <别名>:/remote/path/
scp <别名>:/remote/path/file.txt ./
```

**不需要任何脚本，所有操作通过SSH完成。**

---

## 命令参考

### sshctrl（初始配置用）

```bash
# 配置服务器免密连接（仅需执行一次）
python sshctrl.py server add <host> <用户名> <密码> [别名] [--port 端口]

# 自动修复服务端公钥认证（免密失败时）
python sshctrl.py server repair-pubkey <别名> <密码>

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

### 关键特例：脚本显示配置完成，但免密仍失败

当 `sshctrl.py server add` 输出“配置完成”但 `ssh <别名>` 仍失败时，按下面顺序排查：

```bash
# 1) 先排除 known_hosts 冲突
ssh-keygen -R <服务器IP>

# 2) 禁止交互模式，快速看真实认证结果
ssh -vvv -o BatchMode=yes -o ConnectTimeout=10 <别名> "echo ok"
```

如果日志末尾是 `Permission denied (password)`，说明公钥未被服务端接受。此时在服务器侧检查：

```bash
sshd -T | grep -E 'pubkeyauthentication|passwordauthentication|authorizedkeysfile'
```

若返回 `pubkeyauthentication no`，需要先开启公钥认证，再重载 `sshd`。否则该技能只能走密码路径，无法达到“免密 + 原生 ssh”成功标准。

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
4. （建议）`ssh -o BatchMode=yes <别名> "echo ok"` 返回成功
5. （建议）服务器 `sshd -T` 显示 `pubkeyauthentication yes`

---

## 自动化闭环（新增）

当 `server add` 后免密失败，统一按以下闭环执行：

1. `python sshctrl.py server repair-pubkey <别名> <密码>`
2. `ssh -o BatchMode=yes <别名> "whoami && hostname"`
3. `ssh <别名> "uptime && free -h && df -h /"`

这三步通过后，即可认为技能完成“可稳定复用”的交付标准。

---

## 调用策略（防偏航）

当代理在其他项目调用本技能时，必须显式遵守：

1. 必须使用 `$ssh-remote-control` 技能。
2. 必须使用原生命令：`ssh <别名> "..."` / `scp ...`。
3. 禁止 `python <<'PYEOF'`、`paramiko`、`sshpass` 等密码或脚本执行路径。
4. 若首次配置，最多只允许一次 `python sshctrl.py server add ...` 用于引导免密。

推荐任务前置提示词：
```text
使用 $ssh-remote-control 技能。
禁止 python<<PYEOF、paramiko、sshpass。
只用 ssh/scp：ssh <alias> "<command>"。
```

若出现错误调用，立即中断并重定向：
```text
停止当前实现。你违反了远程执行策略。
重新执行：仅使用 `ssh <alias> "<command>"`。
```

---

## 设计理念

**保持简单**：
- 初始配置用一个小脚本
- 日常操作用原生SSH命令
- 不造轮子，不写冗余脚本
