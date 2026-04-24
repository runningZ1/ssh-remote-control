"""
SSH远控 - Nginx SSL配置
生成并应用具有最佳实践的安全Nginx SSL配置。
"""

import sys
import subprocess
import tempfile
import os

# 导入共享工具
try:
    from utils import run_ssh_command, validate_domain
except ImportError:
    print("✗ 无法导入utils模块，请确保utils.py在同一目录")
    sys.exit(1)


NGINX_SSL_CONFIG_TEMPLATE = """
server {{
    listen 80;
    listen [::]:80;
    server_name {domain}{wildcard_domain};

    # HTTP重定向到HTTPS
    return 301 https://$server_name$request_uri;
}}

server {{
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name {domain}{wildcard_domain};

    # SSL证书
    ssl_certificate /etc/nginx/ssl/{domain}.crt;
    ssl_certificate_key /etc/nginx/ssl/{domain}.key;

    # SSL安全设置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;

    # SSL会话
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;

    # OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;

    # 安全头
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # 文档根目录
    root {document_root};
    index index.html index.htm index.php;

    # 日志
    access_log /var/log/nginx/{domain}_access.log;
    error_log /var/log/nginx/{domain}_error.log;

    # 默认位置
    location / {{
        try_files $uri $uri/ =404;
    }}

    # PHP-FPM（如果使用PHP则取消注释）
    # location ~ \\.php$ {{
    #     include snippets/fastcgi-php.conf;
    #     fastcgi_pass unix:/var/run/php/php8.1-fpm.sock;
    # }}

    # 拒绝访问隐藏文件
    location ~ /\\. {{
        deny all;
    }}
}}
"""


def check_nginx_installed(alias):
    """检查远程服务器上是否安装了Nginx。"""
    result = run_ssh_command(alias, 'command -v nginx', timeout=10)
    return result.returncode == 0


def check_certificate_exists(alias, domain):
    """检查SSL证书文件是否存在。"""
    result = run_ssh_command(
        alias,
        f'test -f /etc/nginx/ssl/{domain}.crt && test -f /etc/nginx/ssl/{domain}.key && echo "exists"',
        timeout=10
    )
    return 'exists' in result.stdout


def generate_config(domain, wildcard=False, document_root='/var/www/html'):
    """生成Nginx SSL配置。"""
    wildcard_domain = f' *.{domain}' if wildcard else ''

    config = NGINX_SSL_CONFIG_TEMPLATE.format(
        domain=domain,
        wildcard_domain=wildcard_domain,
        document_root=document_root
    )

    return config


def backup_existing_config(alias, domain):
    """如果现有Nginx配置存在则备份。"""
    config_path = f"/etc/nginx/sites-available/{domain}"

    result = run_ssh_command(alias, f'test -f {config_path} && echo "exists"', timeout=10)

    if 'exists' in result.stdout:
        print(f"📦 正在备份现有配置...")
        backup_path = f"{config_path}.backup.$(date +%Y%m%d_%H%M%S)"
        run_ssh_command(alias, f'sudo cp {config_path} {backup_path}', timeout=10)
        print(f"✓ 备份已创建: {backup_path}")
        return True

    return False


def apply_config(alias, domain, config_content):
    """将Nginx配置应用到远程服务器（使用SFTP上传）。"""
    config_path = f"/etc/nginx/sites-available/{domain}"
    enabled_path = f"/etc/nginx/sites-enabled/{domain}"

    print(f"\n📝 正在应用Nginx SSL配置...")

    # 创建本地临时文件
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.conf') as f:
        f.write(config_content)
        local_config_file = f.name

    try:
        # 上传到远程临时位置
        remote_temp_file = f'/tmp/nginx_{domain}_{int(os.times().elapsed)}.conf'
        result = subprocess.run(
            ['scp', '-q', local_config_file, f'{alias}:{remote_temp_file}'],
            capture_output=True,
            timeout=30
        )

        if result.returncode != 0:
            print("✗ 上传配置文件失败")
            return False

        # 移动到正确位置
        result = run_ssh_command(
            alias,
            f'sudo mv {remote_temp_file} {config_path}',
            timeout=10
        )

        if result.returncode != 0:
            print("✗ 写入配置文件失败")
            return False

        print(f"✓ 配置已写入 {config_path}")

        # 创建到sites-enabled的符号链接
        run_ssh_command(alias, f'sudo rm -f {enabled_path}', timeout=10)
        result = run_ssh_command(alias, f'sudo ln -s {config_path} {enabled_path}', timeout=10)

        if result.returncode != 0:
            print("✗ 启用站点失败")
            return False

        print(f"✓ 站点已启用: {enabled_path}")
        return True

    finally:
        # 清理本地临时文件
        if os.path.exists(local_config_file):
            os.remove(local_config_file)


def test_nginx_config(alias):
    """测试Nginx配置语法错误。"""
    print("\n🔍 正在测试Nginx配置...")

    result = run_ssh_command(alias, 'sudo nginx -t', capture=False, timeout=30)

    if result.returncode != 0:
        print("\n✗ Nginx配置测试失败")
        print("配置存在语法错误，请查看上方输出。")
        return False

    print("✓ Nginx配置测试通过")
    return True


def reload_nginx(alias):
    """重载Nginx以应用新配置。"""
    print("\n🔄 正在重载Nginx...")

    result = run_ssh_command(alias, 'sudo systemctl reload nginx', timeout=30)

    if result.returncode != 0:
        print("✗ 重载Nginx失败")
        print("尝试: ssh <别名> 'sudo systemctl status nginx'")
        return False

    print("✓ Nginx重载成功")
    return True


def verify_ssl(alias, domain):
    """验证SSL证书是否正常工作。"""
    print(f"\n🔐 正在验证SSL证书...")

    result = run_ssh_command(
        alias,
        f'curl -sI https://{domain} | head -1',
        timeout=30
    )

    if 'HTTP' in result.stdout:
        print(f"✓ HTTPS正常工作: {result.stdout.strip()}")
        return True
    else:
        print("⚠️  无法验证HTTPS（如果DNS尚未配置则正常）")
        return False


def main():
    if len(sys.argv) < 3:
        print("Nginx SSL配置生成器")
        print("\n用法:")
        print("  python configure_nginx_ssl.py <别名> <域名> [选项]")
        print("\n参数:")
        print("  别名   - 来自~/.ssh/config的SSH别名")
        print("  域名  - 域名（例如：example.com）")
        print("\n选项:")
        print("  --wildcard           - 配置通配符证书")
        print("  --root 路径          - 文档根目录路径（默认：/var/www/html）")
        print("  --skip-reload        - 配置后不重载Nginx")
        print("\n示例:")
        print("  python configure_nginx_ssl.py myserver example.com --wildcard --root /var/www/example")
        print("\n前提条件:")
        print("  - SSL证书必须已安装在 /etc/nginx/ssl/<域名>.crt")
        print("  - 先运行 setup_ssl.py 颁发和安装证书")
        sys.exit(1)

    alias = sys.argv[1]
    domain = sys.argv[2]

    # 验证域名格式
    if not validate_domain(domain):
        print(f"✗ 无效的域名: {domain}")
        sys.exit(1)

    # 解析选项
    wildcard = '--wildcard' in sys.argv
    skip_reload = '--skip-reload' in sys.argv
    document_root = '/var/www/html'

    for i, arg in enumerate(sys.argv):
        if arg == '--root' and i + 1 < len(sys.argv):
            document_root = sys.argv[i + 1]

    print("\n" + "="*60)
    print("Nginx SSL配置")
    print("="*60)
    print(f"服务器:        {alias}")
    print(f"域名:        {domain}")
    print(f"通配符:      {'是' if wildcard else '否'}")
    print(f"文档根目录: {document_root}")
    print("="*60 + "\n")

    # 步骤1: 检查Nginx
    print("1️⃣ 正在检查Nginx安装...")
    if not check_nginx_installed(alias):
        print("✗ 服务器上未安装Nginx")
        print("安装: ssh <别名> 'sudo apt-get install -y nginx'")
        sys.exit(1)
    print("✓ Nginx已安装")

    # 步骤2: 检查证书
    print("\n2️⃣ 正在检查SSL证书...")
    if not check_certificate_exists(alias, domain):
        print(f"✗ 在 /etc/nginx/ssl/{domain}.crt 未找到SSL证书")
        print(f"先运行setup_ssl.py颁发和安装证书:")
        print(f"  python setup_ssl.py {alias} {domain} <dns提供商>")
        sys.exit(1)
    print(f"✓ SSL证书已找到")

    # 步骤3: 备份现有配置
    print("\n3️⃣ 正在检查现有配置...")
    backup_existing_config(alias, domain)

    # 步骤4: 生成配置
    print("\n4️⃣ 正在生成Nginx配置...")
    config = generate_config(domain, wildcard, document_root)
    print("✓ 配置已生成")

    # 步骤5: 应用配置
    if not apply_config(alias, domain, config):
        sys.exit(1)

    # 步骤6: 测试配置
    if not test_nginx_config(alias):
        print("\n⚠️  配置存在错误，正在回滚...")
        run_ssh_command(alias, f'sudo rm -f /etc/nginx/sites-enabled/{domain}', timeout=10)
        sys.exit(1)

    # 步骤7: 重载Nginx
    if not skip_reload:
        if not reload_nginx(alias):
            sys.exit(1)
    else:
        print("\n⏭️  跳过Nginx重载（--skip-reload标志）")

    # 步骤8: 验证SSL
    verify_ssl(alias, domain)

    print("\n" + "="*60)
    print("✅ Nginx SSL配置完成！")
    print("="*60)
    print(f"\n配置文件: /etc/nginx/sites-available/{domain}")
    print(f"\n后续步骤:")
    print(f"  1. 确保DNS A记录指向服务器IP")
    print(f"  2. 测试HTTPS: https://{domain}")
    print(f"  3. 检查日志: ssh {alias} 'sudo tail -f /var/log/nginx/{domain}_error.log'")
    print(f"\n已启用的安全功能:")
    print(f"  ✓ 仅TLS 1.2和1.3")
    print(f"  ✓ 强密码套件")
    print(f"  ✓ HTTP到HTTPS重定向")
    print(f"  ✓ HSTS头（有效期：2年）")
    print(f"  ✓ 安全头（X-Frame-Options、X-Content-Type-Options等）")
    print(f"  ✓ OCSP stapling")


if __name__ == "__main__":
    main()
