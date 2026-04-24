"""
SSH远控 - 远程文件编辑工具
安全可靠地编辑远程服务器文件，避免 PowerShell 转义问题。
"""

import sys
import os
import tempfile
import subprocess
import paramiko


def edit_remote_file_via_scp(alias, remote_path, content):
    """
    通过 SCP 上传方式编辑远程文件（推荐方法）。

    参数:
        alias: SSH别名
        remote_path: 远程文件路径
        content: 新文件内容

    返回:
        成功返回True，失败返回False
    """
    print(f"📝 正在编辑远程文件: {remote_path}")

    # 创建本地临时文件
    with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
        f.write(content)
        local_temp_file = f.name

    try:
        # 上传到远程临时位置
        remote_temp_file = f'/tmp/edit_{os.path.basename(remote_path)}_{int(os.times().elapsed)}'

        result = subprocess.run(
            ['scp', '-q', local_temp_file, f'{alias}:{remote_temp_file}'],
            capture_output=True,
            timeout=30
        )

        if result.returncode != 0:
            print(f"✗ 上传失败: {result.stderr.decode()}")
            return False

        # 移动到目标位置（处理需要 sudo 的情况）
        result = subprocess.run(
            ['ssh', alias, f'sudo mv {remote_temp_file} {remote_path}'],
            capture_output=True,
            timeout=10
        )

        if result.returncode != 0:
            print(f"✗ 移动文件失败: {result.stderr.decode()}")
            return False

        print(f"✓ 文件已更新: {remote_path}")
        return True

    finally:
        # 清理本地临时文件
        if os.path.exists(local_temp_file):
            os.remove(local_temp_file)


def edit_remote_file_via_sftp(server_ip, username, password, remote_path, content):
    """
    通过 SFTP 编辑远程文件（适用于需要密码的场景）。

    参数:
        server_ip: 服务器IP
        username: 用户名
        password: 密码
        remote_path: 远程文件路径
        content: 新文件内容

    返回:
        成功返回True，失败返回False
    """
    print(f"📝 正在通过SFTP编辑远程文件: {remote_path}")

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(server_ip, username=username, password=password, timeout=10)

        sftp = ssh.open_sftp()

        # 写入文件
        with sftp.open(remote_path, 'w') as f:
            f.write(content)

        sftp.close()
        ssh.close()

        print(f"✓ 文件已更新: {remote_path}")
        return True

    except Exception as e:
        print(f"✗ 编辑失败: {e}")
        return False


def read_remote_file(alias, remote_path):
    """
    读取远程文件内容。

    参数:
        alias: SSH别名
        remote_path: 远程文件路径

    返回:
        文件内容字符串，失败返回None
    """
    result = subprocess.run(
        ['ssh', alias, f'cat {remote_path}'],
        capture_output=True,
        text=True,
        timeout=30
    )

    if result.returncode != 0:
        print(f"✗ 读取文件失败: {result.stderr}")
        return None

    return result.stdout


def replace_in_remote_file(alias, remote_path, old_text, new_text):
    """
    在远程文件中替换文本（读取-修改-写回）。

    参数:
        alias: SSH别名
        remote_path: 远程文件路径
        old_text: 要替换的文本
        new_text: 新文本

    返回:
        成功返回True，失败返回False
    """
    print(f"🔄 正在替换文件内容: {remote_path}")

    # 读取原文件
    content = read_remote_file(alias, remote_path)
    if content is None:
        return False

    # 检查是否包含要替换的文本
    if old_text not in content:
        print(f"⚠️  未找到要替换的文本")
        return False

    # 替换
    new_content = content.replace(old_text, new_text)

    # 写回
    return edit_remote_file_via_scp(alias, remote_path, new_content)


def append_to_remote_file(alias, remote_path, content):
    """
    向远程文件追加内容。

    参数:
        alias: SSH别名
        remote_path: 远程文件路径
        content: 要追加的内容

    返回:
        成功返回True，失败返回False
    """
    print(f"➕ 正在追加内容到: {remote_path}")

    # 使用 heredoc 方式追加（避免转义问题）
    escaped_content = content.replace("'", "'\\''")

    result = subprocess.run(
        ['ssh', alias, f"cat >> {remote_path} << 'EOF'\n{content}\nEOF"],
        capture_output=True,
        timeout=30
    )

    if result.returncode != 0:
        print(f"✗ 追加失败: {result.stderr.decode()}")
        return False

    print(f"✓ 内容已追加")
    return True


def main():
    if len(sys.argv) < 2:
        print("远程文件编辑工具 - 避免 PowerShell 转义问题")
        print("\n用法:")
        print("  编辑文件:   python remote_edit.py edit <别名> <远程路径> <本地文件>")
        print("  替换文本:   python remote_edit.py replace <别名> <远程路径> <旧文本> <新文本>")
        print("  追加内容:   python remote_edit.py append <别名> <远程路径> <内容>")
        print("  读取文件:   python remote_edit.py read <别名> <远程路径>")
        print("\n示例:")
        print("  python remote_edit.py edit myserver /etc/nginx/nginx.conf local_config.conf")
        print("  python remote_edit.py replace myserver /opt/app/config.py 'DEBUG=False' 'DEBUG=True'")
        print("  python remote_edit.py append myserver /etc/hosts '192.168.1.100 myhost'")
        print("  python remote_edit.py read myserver /var/log/app.log")
        sys.exit(1)

    action = sys.argv[1]

    try:
        if action == 'edit':
            if len(sys.argv) != 5:
                print("用法: python remote_edit.py edit <别名> <远程路径> <本地文件>")
                sys.exit(1)

            alias = sys.argv[2]
            remote_path = sys.argv[3]
            local_file = sys.argv[4]

            if not os.path.exists(local_file):
                print(f"✗ 本地文件不存在: {local_file}")
                sys.exit(1)

            with open(local_file, 'r', encoding='utf-8') as f:
                content = f.read()

            if edit_remote_file_via_scp(alias, remote_path, content):
                sys.exit(0)
            else:
                sys.exit(1)

        elif action == 'replace':
            if len(sys.argv) != 6:
                print("用法: python remote_edit.py replace <别名> <远程路径> <旧文本> <新文本>")
                sys.exit(1)

            alias = sys.argv[2]
            remote_path = sys.argv[3]
            old_text = sys.argv[4]
            new_text = sys.argv[5]

            if replace_in_remote_file(alias, remote_path, old_text, new_text):
                sys.exit(0)
            else:
                sys.exit(1)

        elif action == 'append':
            if len(sys.argv) != 5:
                print("用法: python remote_edit.py append <别名> <远程路径> <内容>")
                sys.exit(1)

            alias = sys.argv[2]
            remote_path = sys.argv[3]
            content = sys.argv[4]

            if append_to_remote_file(alias, remote_path, content):
                sys.exit(0)
            else:
                sys.exit(1)

        elif action == 'read':
            if len(sys.argv) != 4:
                print("用法: python remote_edit.py read <别名> <远程路径>")
                sys.exit(1)

            alias = sys.argv[2]
            remote_path = sys.argv[3]

            content = read_remote_file(alias, remote_path)
            if content is not None:
                print(content)
                sys.exit(0)
            else:
                sys.exit(1)

        else:
            print(f"✗ 未知操作: {action}")
            print("有效操作: edit, replace, append, read")
            sys.exit(1)

    except subprocess.TimeoutExpired:
        print("✗ 操作超时")
        sys.exit(1)
    except Exception as e:
        print(f"✗ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
