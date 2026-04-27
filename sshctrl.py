#!/usr/bin/env python3
"""
SSH Remote Control - 统一的远程服务器管理CLI

用法:
    sshctrl server add <IP> <用户名> <密码> [别名]
    sshctrl server list
    sshctrl server remove <别名>
    sshctrl server ssh <别名> [命令]
    sshctrl tmux run <别名> <会话名> <命令>
    sshctrl tmux check <别名> <会话名> [--full]
    sshctrl tmux list <别名>
    sshctrl tmux attach <别名> <会话名>
    sshctrl tmux kill <别名> <会话名>
    sshctrl ssl issue <域名> <DNS提供商> [--wildcard] [--email <邮箱>]
    sshctrl ssl nginx <域名> [--root <路径>]
    sshctrl exec <别名> <命令>
"""

import argparse
import sys
import os
import json
import subprocess
import platform
import re

VERSION = "1.0.0"

CONFIG_DIR = os.path.expanduser("~/.ssh/sshctrl")
SERVERS_FILE = os.path.join(CONFIG_DIR, "servers.json")

DNS_PROVIDERS = {
    'cloudflare': {'name': 'Cloudflare', 'hook': 'dns_cf', 'env': ['CF_Token']},
    'aliyun': {'name': '阿里云', 'hook': 'dns_ali', 'env': ['Ali_Key', 'Ali_Secret']},
    'tencent': {'name': '腾讯云', 'hook': 'dns_tencent', 'env': ['Tencent_SecretId', 'Tencent_SecretKey']},
    'dnspod': {'name': 'DNSPod', 'hook': 'dns_dp', 'env': ['DP_Id', 'DP_Key']},
}


def ensure_config_dir():
    os.makedirs(CONFIG_DIR, exist_ok=True)


def load_servers():
    if not os.path.exists(SERVERS_FILE):
        return {}
    with open(SERVERS_FILE) as f:
        return json.load(f)


def save_servers(servers):
    ensure_config_dir()
    with open(SERVERS_FILE, 'w') as f:
        json.dump(servers, f, indent=2)


def run_ssh_command(alias, command, capture=True, timeout=30):
    try:
        result = subprocess.run(
            ['ssh', '-o', 'ConnectTimeout=10', alias, command],
            capture_output=capture, text=True, timeout=timeout
        )
        return result
    except subprocess.TimeoutExpired:
        print(f"✗ 命令执行超时（{timeout}秒）")
        sys.exit(1)


def validate_ip(ip):
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, ip):
        return False
    parts = ip.split('.')
    return all(0 <= int(part) <= 255 for part in parts)


def validate_domain(domain):
    pattern = r'^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$'
    return re.match(pattern, domain.lower()) is not None


# ============== Server 子命令 ==============

def cmd_server_add(args):
    import paramiko

    ip = args.IP
    username = args.username
    password = args.password
    alias = args.alias or ip.replace('.', '_')
    skip_ssh = args.skip_ssh

    if not validate_ip(ip):
        print(f"✗ 无效的IP地址: {ip}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("SSH Remote Control - 添加服务器")
    print(f"{'='*60}")
    print(f"服务器: {ip}")
    print(f"用户: {username}")
    print(f"别名: {alias}")
    print(f"{'='*60}\n")

    print("1️⃣ 测试SSH连接...")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=username, password=password, timeout=10)
        print("   ✓ 连接成功")

        stdin, stdout, stderr = ssh.exec_command('uname -a')
        info = stdout.read().decode().strip()
        hostname = info.split()[1] if info else '未知'
        print(f"   主机名: {hostname}")
        ssh.close()
    except paramiko.AuthenticationException:
        print("   ✗ 认证失败，请检查用户名和密码")
        sys.exit(1)
    except Exception as e:
        print(f"   ✗ 连接失败: {e}")
        sys.exit(1)

    if skip_ssh:
        servers = load_servers()
        servers[alias] = {'ip': ip, 'username': username}
        save_servers(servers)
        print(f"\n✓ 服务器信息已保存: {alias}")
        return

    print("\n2️⃣ 生成SSH密钥...")
    home = os.path.expanduser('~')
    key_name = f"id_ed25519_{ip.replace('.', '_')}"
    key_path = os.path.join(home, '.ssh', key_name)

    if os.path.exists(key_path):
        print(f"   ✓ 密钥已存在: {key_name}")
    else:
        result = subprocess.run(
            ['ssh-keygen', '-t', 'ed25519', '-f', key_path, '-N', '', '-C', f'sshctrl-{ip}'],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"   ✓ 密钥已生成: {key_name}")
        else:
            print(f"   ✗ 密钥生成失败: {result.stderr}")
            sys.exit(1)

    with open(key_path + '.pub') as f:
        pubkey = f.read().strip()

    print("\n3️⃣ 上传公钥到服务器...")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=username, password=password, timeout=10)

        stdin, stdout, stderr = ssh.exec_command(f'eval echo ~{username}')
        user_home = stdout.read().decode().strip() or ('/root' if username == 'root' else f'/home/{username}')
        print(f"   家目录: {user_home}")

        ssh.exec_command(f'mkdir -p {user_home}/.ssh && chmod 700 {user_home}/.ssh')

        sftp = ssh.open_sftp()
        auth_keys_path = f'{user_home}/.ssh/authorized_keys'

        try:
            with sftp.open(auth_keys_path, 'a') as f:
                f.write(pubkey + '\n')
            sftp.chmod(auth_keys_path, 0o600)
            print("   ✓ 公钥已上传")
        finally:
            sftp.close()
        ssh.close()
    except Exception as e:
        print(f"   ✗ 上传失败: {e}")
        sys.exit(1)

    print("\n4️⃣ 配置本地SSH...")
    ssh_dir = os.path.join(home, '.ssh')
    os.makedirs(ssh_dir, exist_ok=True)

    if platform.system() == 'Windows':
        try:
            subprocess.run([
                'powershell.exe', '-NoProfile', '-Command',
                f"$path = '{key_path}'; $acl = Get-Acl $path; "
                f"$acl.SetAccessRuleProtection($true, $false); "
                f"$rule = New-Object System.Security.AccessControl.FileSystemAccessRule("
                f"[System.Security.Principal.WindowsIdentity]::GetCurrent().Name,"
                f"'FullControl','Allow'); $acl.SetAccessRule($rule); Set-Acl $path $acl"
            ], check=True, capture_output=True, timeout=30)
            print("   ✓ Windows权限已修复")
        except:
            print("   ⚠ 权限修复失败，请手动处理")
    else:
        os.chmod(key_path, 0o600)
        print("   ✓ 权限已设置为600")

    ssh_config = os.path.join(ssh_dir, 'config')
    existing_aliases = []
    if os.path.exists(ssh_config):
        with open(ssh_config) as f:
            for line in f:
                if line.strip().startswith('Host '):
                    existing_aliases.append(line.split()[1])

    if alias in existing_aliases:
        print(f"   ⚠ 别名 '{alias}' 已存在")
    else:
        config_entry = f"""
Host {alias}
    HostName {ip}
    User {username}
    IdentityFile ~/.ssh/{key_name}
    IdentitiesOnly yes
    StrictHostKeyChecking accept-new
    ServerAliveInterval 60
    ServerAliveCountMax 3
    TCPKeepAlive yes
"""
        with open(ssh_config, 'a') as f:
            f.write(config_entry)
        print(f"   ✓ SSH别名 '{alias}' 已添加")

    servers = load_servers()
    servers[alias] = {'ip': ip, 'username': username}
    save_servers(servers)

    print(f"\n{'='*60}")
    print("✅ 服务器配置完成！")
    print(f"{'='*60}")
    print(f"\n测试命令: ssh {alias} \"whoami\"")


def cmd_server_list(args):
    servers = load_servers()

    if not servers:
        print("没有已配置的服务器。")
        print(f"\n添加服务器: sshctrl server add <IP> <用户名> <密码> [别名]")
        return

    print(f"\n已配置的服务器 ({len(servers)}台):\n")
    for alias, info in sorted(servers.items()):
        print(f"  {alias}")
        print(f"    IP: {info.get('ip', 'N/A')}")
        print(f"    用户: {info.get('username', 'N/A')}")
        print()


def cmd_server_remove(args):
    alias = args.alias
    home = os.path.expanduser('~')

    servers = load_servers()
    if alias not in servers:
        print(f"✗ 服务器 '{alias}' 不存在")
        sys.exit(1)

    del servers[alias]
    save_servers(servers)
    print(f"✓ 已从配置列表移除: {alias}")

    ssh_config = os.path.join(home, '.ssh', 'config')
    if os.path.exists(ssh_config):
        with open(ssh_config) as f:
            lines = f.readlines()

        new_lines = []
        skip_block = False
        for line in lines:
            if line.strip().startswith('Host ' + alias):
                skip_block = True
                continue
            elif skip_block and line.strip().startswith('Host '):
                skip_block = False
            if not skip_block:
                new_lines.append(line)

        with open(ssh_config, 'w') as f:
            f.writelines(new_lines)
        print(f"✓ 已从SSH配置移除: {alias}")

    subprocess.run(['ssh-keygen', '-R', alias], capture_output=True)
    print(f"✓ 已删除主机密钥")


def cmd_server_ssh(args):
    alias = args.alias
    command = args.command

    servers = load_servers()
    if alias not in servers:
        print(f"✗ 服务器 '{alias}' 未找到")
        print(f"可用服务器: {', '.join(servers.keys()) if servers else '无'}")
        sys.exit(1)

    if command:
        result = run_ssh_command(alias, command)
        print(result.stdout)
        sys.exit(result.returncode)
    else:
        os.execvp('ssh', ['ssh', alias])


# ============== Tmux 子命令 ==============

def cmd_tmux_attach(args):
    alias = args.alias
    session = args.session

    print(f"接入 tmux 会话 '{session}'...")
    result = subprocess.run(['ssh', '-t', alias, f'tmux attach -t {session}'])
    if result.returncode != 0:
        print(f"✗ 会话不存在或已被终止")
        sys.exit(1)


def cmd_tmux_run(args):
    alias = args.alias
    session = args.session
    command = args.command

    print(f"🚀 在 tmux 会话 '{session}' 中启动命令...")

    subprocess.run(
        ['ssh', alias, f'tmux kill-session -t {session} 2>/dev/null || true'],
        capture_output=True, timeout=10
    )

    result = subprocess.run(
        ['ssh', alias, f'tmux new-session -d -s {session} "{command}"'],
        capture_output=True, text=True, timeout=30
    )

    if result.returncode != 0:
        print(f"✗ 启动失败: {result.stderr}")
        sys.exit(1)

    print(f"✓ 命令已在后台会话 '{session}' 中启动")
    print(f"\n查看状态: sshctrl tmux check {alias} {session}")
    print(f"接入会话: sshctrl tmux attach {alias} {session}")
    print(f"终止会话: sshctrl tmux kill {alias} {session}")


def cmd_tmux_check(args):
    alias = args.alias
    session = args.session
    full = args.full

    result = subprocess.run(
        ['ssh', alias, f'tmux has-session -t {session} 2>/dev/null'],
        capture_output=True, timeout=10
    )

    if result.returncode != 0:
        print(f"✗ 会话 '{session}' 不存在或已完成")
        sys.exit(1)

    print(f"✓ 会话 '{session}' 正在运行")

    if full:
        result = subprocess.run(
            ['ssh', alias, f'tmux capture-pane -t {session} -p -S -'],
            capture_output=True, text=True, timeout=30
        )
    else:
        result = subprocess.run(
            ['ssh', alias, f'tmux capture-pane -t {session} -p | tail -50'],
            capture_output=True, text=True, timeout=30
        )

    print(f"\n--- 来自 '{session}' 的输出 ---")
    print(result.stdout)
    print("--- 输出结束 ---\n")


def cmd_tmux_list(args):
    alias = args.alias

    print(f"📋 正在列出 {alias} 上的 tmux 会话...")

    result = subprocess.run(
        ['ssh', alias, 'tmux ls 2>/dev/null'],
        capture_output=True, text=True, timeout=10
    )

    if result.returncode != 0:
        print("✗ 没有活动的 tmux 会话")
        sys.exit(1)

    print("\n活动会话:")
    print(result.stdout)


def cmd_tmux_kill(args):
    alias = args.alias
    session = args.session

    print(f"🛑 正在终止会话 '{session}'...")

    result = subprocess.run(
        ['ssh', alias, f'tmux kill-session -t {session}'],
        capture_output=True, text=True, timeout=10
    )

    if result.returncode != 0:
        print(f"✗ 会话不存在")
        sys.exit(1)

    print(f"✓ 会话 '{session}' 已终止")


# ============== SSL 子命令 ==============

def cmd_ssl_issue(args):
    import os as os_module

    domain = args.domain
    dns_provider = args.dns_provider
    wildcard = args.wildcard
    email = args.email or f'admin@{domain}'

    if not validate_domain(domain):
        print(f"✗ 无效的域名: {domain}")
        sys.exit(1)

    if dns_provider not in DNS_PROVIDERS:
        print(f"✗ 未知DNS提供商: {dns_provider}")
        print(f"支持的提供商: {', '.join(DNS_PROVIDERS.keys())}")
        sys.exit(1)

    provider = DNS_PROVIDERS[dns_provider]

    missing = []
    for var in provider['env']:
        if not os_module.environ.get(var):
            missing.append(var)

    if missing:
        print(f"✗ 缺少环境变量: {', '.join(missing)}")
        print(f"\n设置方法:")
        for var in missing:
            print(f"  export {var}='your_value'")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("SSL证书申请")
    print(f"{'='*60}")
    print(f"域名: {domain}")
    print(f"提供商: {provider['name']}")
    print(f"通配符: {'是' if wildcard else '否'}")
    print(f"邮箱: {email}")
    print(f"{'='*60}\n")

    print("⚠️  SSL证书申请需要在已配置SSH别名的服务器上执行。")
    print("   请先配置服务器: sshctrl server add <IP> <用户> <密码> [别名]")
    print(f"\n   然后使用SSH别名运行证书申请命令。")


def cmd_ssl_nginx(args):
    domain = args.domain
    root = args.root

    if not validate_domain(domain):
        print(f"✗ 无效的域名: {domain}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("Nginx SSL配置")
    print(f"{'='*60}")
    print(f"域名: {domain}")
    print(f"文档根目录: {root}")
    print(f"{'='*60}\n")

    print("⚠️  Nginx SSL配置需要在服务器上执行。")
    print("   请先配置服务器并申请证书。")
    print(f"\n   配置文件示例:")
    print(f"""
server {{
    listen 80;
    server_name {domain};
    return 301 https://$server_name$request_uri;
}}

server {{
    listen 443 ssl http2;
    server_name {domain};

    ssl_certificate /etc/nginx/ssl/{domain}.crt;
    ssl_certificate_key /etc/nginx/ssl/{domain}.key;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    root {root};
    index index.html index.htm;

    location / {{
        try_files $uri $uri/ =404;
    }}
}}
""")


# ============== Exec 子命令 ==============

def cmd_exec(args):
    alias = args.alias
    command = args.command

    servers = load_servers()
    if alias not in servers:
        print(f"✗ 服务器 '{alias}' 未找到")
        print(f"可用服务器: {', '.join(servers.keys()) if servers else '无'}")
        sys.exit(1)

    result = run_ssh_command(alias, command)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    sys.exit(result.returncode)


# ============== 主入口 ==============

def main():
    parser = argparse.ArgumentParser(
        description="SSH Remote Control - 统一的远程服务器管理CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  sshctrl server add 192.168.1.100 root password myserver
  sshctrl server list
  sshctrl server ssh myserver "uptime"
  sshctrl tmux run myserver deploy "npm run build"
  sshctrl tmux check myserver deploy
  sshctrl exec myserver "df -h"
        """
    )
    parser.add_argument('--version', action='version', version=f'sshctrl {VERSION}')

    subparsers = parser.add_subparsers(dest='command', help='可用子命令')

    # server 子命令
    server_parser = subparsers.add_parser('server', help='服务器管理')
    server_subparsers = server_parser.add_subparsers(dest='server_command')

    add_parser = server_subparsers.add_parser('add', help='添加并配置新服务器')
    add_parser.add_argument('IP', help='服务器IP地址')
    add_parser.add_argument('username', help='用户名')
    add_parser.add_argument('password', help='密码')
    add_parser.add_argument('alias', nargs='?', help='SSH别名（可选）')
    add_parser.add_argument('--skip-ssh', action='store_true', help='仅保存信息')

    server_subparsers.add_parser('list', help='列出所有已配置的服务器')

    remove_parser = server_subparsers.add_parser('remove', help='移除服务器配置')
    remove_parser.add_argument('alias', help='要移除的服务器别名')

    ssh_parser = server_subparsers.add_parser('ssh', help='SSH连接到服务器')
    ssh_parser.add_argument('alias', help='服务器别名')
    ssh_parser.add_argument('command', nargs='?', default=None, help='要执行的命令（可选）')

    # tmux 子命令
    tmux_parser = subparsers.add_parser('tmux', help='tmux会话管理')
    tmux_subparsers = tmux_parser.add_subparsers(dest='tmux_command')

    run_parser = tmux_subparsers.add_parser('run', help='在tmux后台运行命令')
    run_parser.add_argument('alias', help='服务器别名')
    run_parser.add_argument('session', help='tmux会话名称')
    run_parser.add_argument('command', help='要执行的命令')

    check_parser = tmux_subparsers.add_parser('check', help='检查tmux会话输出')
    check_parser.add_argument('alias', help='服务器别名')
    check_parser.add_argument('session', help='tmux会话名称')
    check_parser.add_argument('--full', action='store_true', help='显示完整输出')

    tmux_subparsers.add_parser('list', help='列出所有tmux会话', aliases=['ls'])

    attach_parser = tmux_subparsers.add_parser('attach', help='接入tmux会话')
    attach_parser.add_argument('alias', help='服务器别名')
    attach_parser.add_argument('session', help='tmux会话名称')

    kill_parser = tmux_subparsers.add_parser('kill', help='终止tmux会话')
    kill_parser.add_argument('alias', help='服务器别名')
    kill_parser.add_argument('session', help='tmux会话名称')

    # ssl 子命令
    ssl_parser = subparsers.add_parser('ssl', help='SSL证书管理')
    ssl_subparsers = ssl_parser.add_subparsers(dest='ssl_command')

    issue_parser = ssl_subparsers.add_parser('issue', help='申请SSL证书')
    issue_parser.add_argument('domain', help='域名')
    issue_parser.add_argument('dns_provider', help='DNS提供商')
    issue_parser.add_argument('--wildcard', action='store_true', help='申请通配符证书')
    issue_parser.add_argument('--email', help='通知邮箱')

    nginx_parser = ssl_subparsers.add_parser('nginx', help='配置Nginx SSL')
    nginx_parser.add_argument('domain', help='域名')
    nginx_parser.add_argument('--root', default='/var/www/html', help='文档根目录')

    # exec 子命令
    exec_parser = subparsers.add_parser('exec', help='快速执行命令')
    exec_parser.add_argument('alias', help='服务器别名')
    exec_parser.add_argument('command', help='要执行的命令')

    args = parser.parse_args()

    if args.command == 'server':
        if args.server_command == 'add':
            cmd_server_add(args)
        elif args.server_command == 'list':
            cmd_server_list(args)
        elif args.server_command == 'remove':
            cmd_server_remove(args)
        elif args.server_command == 'ssh':
            cmd_server_ssh(args)
        else:
            server_parser.print_help()
    elif args.command == 'tmux':
        if args.tmux_command in ('list', 'ls'):
            cmd_tmux_list(args)
        elif args.tmux_command == 'run':
            cmd_tmux_run(args)
        elif args.tmux_command == 'check':
            cmd_tmux_check(args)
        elif args.tmux_command == 'attach':
            cmd_tmux_attach(args)
        elif args.tmux_command == 'kill':
            cmd_tmux_kill(args)
        else:
            tmux_parser.print_help()
    elif args.command == 'ssl':
        if args.ssl_command == 'issue':
            cmd_ssl_issue(args)
        elif args.ssl_command == 'nginx':
            cmd_ssl_nginx(args)
        else:
            ssl_parser.print_help()
    elif args.command == 'exec':
        cmd_exec(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
