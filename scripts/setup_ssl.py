"""
SSH远控 - SSL证书设置
使用acme.sh和DNS API验证自动化SSL证书颁发。
支持Cloudflare、阿里云和腾讯云DNS提供商。
"""

import sys
import subprocess
import time


DNS_PROVIDERS = {
    'cloudflare': {
        'name': 'Cloudflare',
        'dns_hook': 'dns_cf',
        'env_vars': ['CF_Token'],
        'optional_vars': ['CF_Zone_ID'],
        'docs': 'https://dash.cloudflare.com/profile/api-tokens'
    },
    'aliyun': {
        'name': '阿里云',
        'dns_hook': 'dns_ali',
        'env_vars': ['Ali_Key', 'Ali_Secret'],
        'optional_vars': [],
        'docs': 'https://ram.console.aliyun.com/manage/ak'
    },
    'tencentcloud': {
        'name': '腾讯云',
        'dns_hook': 'dns_tencent',
        'env_vars': ['Tencent_SecretId', 'Tencent_SecretKey'],
        'optional_vars': [],
        'docs': 'https://console.cloud.tencent.com/cam/capi'
    },
    'dnspod': {
        'name': 'DNSPod',
        'dns_hook': 'dns_dp',
        'env_vars': ['DP_Id', 'DP_Key'],
        'optional_vars': [],
        'docs': 'https://console.dnspod.cn/account/token/token'
    }
}


# 导入共享工具
try:
    from utils import run_ssh_command, validate_domain
except ImportError:
    print("✗ 无法导入utils模块，请确保utils.py在同一目录")
    sys.exit(1)


def check_acme_installed(alias):
    """检查远程服务器上是否安装了acme.sh。"""
    result = run_ssh_command(alias, 'test -f ~/.acme.sh/acme.sh && echo "installed"')
    return 'installed' in result.stdout


def install_acme(alias, email):
    """在远程服务器上安装acme.sh。"""
    print("📦 正在安装acme.sh...")

    result = run_ssh_command(
        alias,
        f'curl -s https://get.acme.sh | sh -s email={email}',
        capture=False
    )

    if result.returncode != 0:
        print("✗ acme.sh安装失败")
        return False

    # 验证安装
    time.sleep(2)
    if check_acme_installed(alias):
        print("✓ acme.sh安装成功")
        return True
    else:
        print("✗ acme.sh安装验证失败")
        return False


def issue_certificate(alias, domain, wildcard, dns_provider, credentials):
    """使用DNS API验证颁发SSL证书。"""
    provider_info = DNS_PROVIDERS[dns_provider]
    dns_hook = provider_info['dns_hook']

    print(f"\n🔐 正在为 {domain} 颁发SSL证书...")
    print(f"DNS提供商: {provider_info['name']}")
    print(f"通配符: {'是' if wildcard else '否'}")

    # 构建环境变量文件（更安全的方式）
    import tempfile
    import os

    env_vars = {}
    for var in provider_info['env_vars']:
        if var not in credentials:
            print(f"✗ 缺少必需的凭证: {var}")
            return False
        env_vars[var] = credentials[var]

    for var in provider_info['optional_vars']:
        if var in credentials:
            env_vars[var] = credentials[var]

    # 创建临时环境变量文件
    env_content = '\n'.join([f'export {k}="{v}"' for k, v in env_vars.items()])

    # 上传环境变量到远程临时文件
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as f:
        f.write(env_content)
        local_env_file = f.name

    try:
        # 使用scp上传环境变量文件
        remote_env_file = f'/tmp/acme_env_{int(time.time())}.sh'
        subprocess.run(
            ['scp', '-q', local_env_file, f'{alias}:{remote_env_file}'],
            check=True,
            timeout=10
        )

        # 构建域名参数
        domain_args = f"-d {domain}"
        if wildcard:
            domain_args += f" -d '*.{domain}'"

        # 构建完整命令（从文件加载环境变量）
        issue_command = (
            f"source {remote_env_file} && "
            f"~/.acme.sh/acme.sh --issue --dns {dns_hook} {domain_args} --force"
        )

        print("\n⏳ 正在颁发证书（可能需要2-3分钟）...")
        result = run_ssh_command(alias, issue_command, capture=False, timeout=300)

        # 清理远程临时文件
        run_ssh_command(alias, f'rm -f {remote_env_file}', timeout=10)

        if result.returncode != 0:
            print("\n✗ 证书颁发失败")
            print("常见问题:")
            print("  - DNS API凭证不正确")
            print("  - DNS提供商API速率限制已达到")
            print("  - 域名DNS未由此提供商管理")
            return False

        print("\n✓ 证书颁发成功")
        return True

    finally:
        # 清理本地临时文件
        if os.path.exists(local_env_file):
            os.remove(local_env_file)


def install_certificate(alias, domain, web_server='nginx'):
    """将证书安装到Web服务器。"""
    print(f"\n📋 正在将证书安装到 {web_server}...")

    # 创建SSL目录
    ssl_dir = f"/etc/{web_server}/ssl"
    run_ssh_command(alias, f"sudo mkdir -p {ssl_dir}")

    # 确定重载命令
    if web_server == 'nginx':
        reload_cmd = "sudo systemctl reload nginx"
    elif web_server == 'apache':
        reload_cmd = "sudo systemctl reload apache2"
    else:
        reload_cmd = f"sudo systemctl reload {web_server}"

    # 安装证书
    install_command = (
        f"~/.acme.sh/acme.sh --install-cert -d {domain} "
        f"--key-file {ssl_dir}/{domain}.key "
        f"--fullchain-file {ssl_dir}/{domain}.crt "
        f"--reloadcmd '{reload_cmd}'"
    )

    result = run_ssh_command(alias, install_command, capture=False)

    if result.returncode != 0:
        print("✗ 证书安装失败")
        return False

    print(f"✓ 证书已安装到 {ssl_dir}/")
    print(f"  - 私钥: {ssl_dir}/{domain}.key")
    print(f"  - 证书: {ssl_dir}/{domain}.crt")
    return True


def verify_auto_renewal(alias):
    """验证自动续期cron作业是否已配置。"""
    print("\n🔄 正在验证自动续期...")

    result = run_ssh_command(alias, "crontab -l | grep acme.sh")

    if result.returncode == 0 and 'acme.sh' in result.stdout:
        print("✓ 自动续期已配置（每日检查）")
        print("  证书将在到期前60天自动续期")
        return True
    else:
        print("⚠ 未找到自动续期cron作业")
        print("  运行: ssh <别名> '~/.acme.sh/acme.sh --install-cronjob'")
        return False


def main():
    if len(sys.argv) < 2:
        print("SSL证书设置 - 使用acme.sh自动化SSL")
        print("\n用法:")
        print("  python setup_ssl.py <别名> <域名> <DNS提供商> [选项]")
        print("\n参数:")
        print("  别名         - 来自~/.ssh/config的SSH别名")
        print("  域名        - 域名（例如：example.com）")
        print("  DNS提供商  - cloudflare | aliyun | tencentcloud | dnspod")
        print("\n选项:")
        print("  --wildcard    - 颁发通配符证书（*.domain.com）")
        print("  --email 邮箱 - 证书通知邮箱")
        print("  --server 类型 - Web服务器类型（nginx|apache，默认：nginx）")
        print("\nDNS提供商凭证（设置为环境变量）:")
        print("\nCloudflare:")
        print("  CF_Token      - 具有Zone:DNS:Edit权限的API令牌")
        print("  CF_Zone_ID    - （可选）用于更快DNS查找的Zone ID")
        print("  获取令牌: https://dash.cloudflare.com/profile/api-tokens")
        print("\n阿里云:")
        print("  Ali_Key       - AccessKey ID")
        print("  Ali_Secret    - AccessKey Secret")
        print("  获取凭证: https://ram.console.aliyun.com/manage/ak")
        print("\n腾讯云:")
        print("  Tencent_SecretId  - SecretId")
        print("  Tencent_SecretKey - SecretKey")
        print("  获取凭证: https://console.cloud.tencent.com/cam/capi")
        print("\nDNSPod:")
        print("  DP_Id         - API ID")
        print("  DP_Key        - API令牌")
        print("  获取令牌: https://console.dnspod.cn/account/token/token")
        print("\n示例:")
        print("  export CF_Token='your_cloudflare_token'")
        print("  python setup_ssl.py myserver example.com cloudflare --wildcard --email admin@example.com")
        sys.exit(1)

    # 解析参数
    alias = sys.argv[1]
    domain = sys.argv[2]
    dns_provider = sys.argv[3].lower()

    # 验证域名格式
    if not validate_domain(domain):
        print(f"✗ 无效的域名: {domain}")
        sys.exit(1)

    if dns_provider not in DNS_PROVIDERS:
        print(f"✗ 未知DNS提供商: {dns_provider}")
        print(f"支持的提供商: {', '.join(DNS_PROVIDERS.keys())}")
        sys.exit(1)

    # 解析选项
    wildcard = '--wildcard' in sys.argv
    email = 'admin@' + domain
    web_server = 'nginx'

    for i, arg in enumerate(sys.argv):
        if arg == '--email' and i + 1 < len(sys.argv):
            email = sys.argv[i + 1]
        if arg == '--server' and i + 1 < len(sys.argv):
            web_server = sys.argv[i + 1]

    # 从环境变量收集凭证
    import os
    provider_info = DNS_PROVIDERS[dns_provider]
    credentials = {}

    print(f"\n🔍 正在检查 {provider_info['name']} 的DNS提供商凭证...")
    missing_vars = []

    for var in provider_info['env_vars']:
        value = os.environ.get(var)
        if value:
            credentials[var] = value
            print(f"  ✓ {var} 已找到")
        else:
            missing_vars.append(var)
            print(f"  ✗ {var} 缺失")

    for var in provider_info['optional_vars']:
        value = os.environ.get(var)
        if value:
            credentials[var] = value
            print(f"  ✓ {var} 已找到（可选）")

    if missing_vars:
        print(f"\n✗ 缺少必需的凭证: {', '.join(missing_vars)}")
        print(f"\n如何获取凭证:")
        print(f"  {provider_info['docs']}")
        print(f"\n将它们设置为环境变量:")
        for var in missing_vars:
            print(f"  export {var}='your_value'")
        sys.exit(1)

    print("\n" + "="*60)
    print("SSL证书设置")
    print("="*60)
    print(f"服务器:       {alias}")
    print(f"域名:       {domain}")
    print(f"通配符:     {'是 (*.{})'.format(domain) if wildcard else '否'}")
    print(f"DNS提供商: {provider_info['name']}")
    print(f"邮箱:        {email}")
    print(f"Web服务器:   {web_server}")
    print("="*60 + "\n")

    # 步骤1: 检查/安装acme.sh
    if check_acme_installed(alias):
        print("✓ acme.sh已安装")
    else:
        if not install_acme(alias, email):
            sys.exit(1)

    # 步骤2: 颁发证书
    if not issue_certificate(alias, domain, wildcard, dns_provider, credentials):
        sys.exit(1)

    # 步骤3: 安装证书
    if not install_certificate(alias, domain, web_server):
        sys.exit(1)

    # 步骤4: 验证自动续期
    verify_auto_renewal(alias)

    print("\n" + "="*60)
    print("✅ SSL证书设置完成！")
    print("="*60)
    print(f"\n证书文件:")
    print(f"  /etc/{web_server}/ssl/{domain}.key")
    print(f"  /etc/{web_server}/ssl/{domain}.crt")
    print(f"\n后续步骤:")
    print(f"  1. 配置{web_server}使用这些证书文件")
    print(f"  2. 运行: python configure_nginx_ssl.py {alias} {domain}")
    print(f"  3. 测试HTTPS: https://{domain}")
    print(f"\n证书将在到期前60天自动续期。")


if __name__ == "__main__":
    main()
