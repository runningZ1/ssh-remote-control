"""
SSH远控 - Tmux助手
用于在持久化tmux会话中运行长时间运行命令的工具。
"""

import sys
import subprocess
import time


def run_in_tmux(alias, session_name, command):
    """
    在远程服务器上的分离tmux会话中执行命令。

    参数:
        alias: 来自~/.ssh/config的SSH别名
        session_name: tmux会话名称
        command: 要执行的命令

    返回:
        成功返回0，失败返回1
    """
    print(f"🚀 正在在tmux会话 '{session_name}' 中启动命令...")

    # 如果会话已存在则终止
    subprocess.run(
        ['ssh', alias, f'tmux kill-session -t {session_name} 2>/dev/null || true'],
        capture_output=True,
        timeout=10
    )

    # 启动带有命令的新tmux会话
    result = subprocess.run(
        ['ssh', alias, f'tmux new-session -d -s {session_name} "{command}"'],
        capture_output=True,
        text=True,
        timeout=30
    )

    if result.returncode != 0:
        print(f"✗ 启动tmux会话失败: {result.stderr}")
        return 1

    print(f"✓ 命令已在后台会话 '{session_name}' 中启动")
    print(f"\n查看状态: python tmux_helper.py check {alias} {session_name}")
    print(f"附加会话: ssh {alias} -t \"tmux attach -t {session_name}\"")
    print(f"终止会话: python tmux_helper.py kill {alias} {session_name}")
    return 0


def check_tmux_session(alias, session_name, full=False):
    """
    检查tmux会话是否存在并显示其输出。

    参数:
        alias: 来自~/.ssh/config的SSH别名
        session_name: tmux会话名称
        full: 是否显示完整输出

    返回:
        会话存在返回0，不存在返回1
    """
    # 检查会话是否存在
    result = subprocess.run(
        ['ssh', alias, f'tmux has-session -t {session_name} 2>/dev/null'],
        capture_output=True,
        timeout=10
    )

    if result.returncode != 0:
        print(f"✗ 会话 '{session_name}' 不存在或已完成")
        return 1

    print(f"✓ 会话 '{session_name}' 正在运行")

    # 捕获并显示输出
    if full:
        # 显示完整输出
        result = subprocess.run(
            ['ssh', alias, f'tmux capture-pane -t {session_name} -p -S -'],
            capture_output=True,
            text=True,
            timeout=30
        )
    else:
        # 显示最后50行
        result = subprocess.run(
            ['ssh', alias, f'tmux capture-pane -t {session_name} -p | tail -50'],
            capture_output=True,
            text=True,
            timeout=30
        )

    print(f"\n--- 来自 '{session_name}' 的输出 ---")
    print(result.stdout)
    print("--- 输出结束 ---\n")
    return 0


def list_tmux_sessions(alias):
    """
    列出远程服务器上的所有tmux会话。

    参数:
        alias: 来自~/.ssh/config的SSH别名

    返回:
        成功返回0，失败返回1
    """
    print(f"📋 正在列出 {alias} 上的tmux会话...")

    result = subprocess.run(
        ['ssh', alias, 'tmux ls 2>/dev/null'],
        capture_output=True,
        text=True,
        timeout=10
    )

    if result.returncode != 0:
        print("✗ 没有活动的tmux会话")
        return 1

    print("\n活动会话:")
    print(result.stdout)
    return 0


def kill_tmux_session(alias, session_name):
    """
    终止指定的tmux会话。

    参数:
        alias: 来自~/.ssh/config的SSH别名
        session_name: tmux会话名称

    返回:
        成功返回0，失败返回1
    """
    print(f"🛑 正在终止会话 '{session_name}'...")

    # 检查会话是否存在
    result = subprocess.run(
        ['ssh', alias, f'tmux has-session -t {session_name} 2>/dev/null'],
        capture_output=True,
        timeout=10
    )

    if result.returncode != 0:
        print(f"✗ 会话 '{session_name}' 不存在")
        return 1

    # 终止会话
    result = subprocess.run(
        ['ssh', alias, f'tmux kill-session -t {session_name}'],
        capture_output=True,
        text=True,
        timeout=10
    )

    if result.returncode != 0:
        print(f"✗ 终止会话失败: {result.stderr}")
        return 1

    print(f"✓ 会话 '{session_name}' 已终止")
    return 0


def main():
    if len(sys.argv) < 2:
        print("Tmux助手 - 管理远程tmux会话")
        print("\n用法:")
        print("  运行命令:     python tmux_helper.py run <别名> <会话名> <命令>")
        print("  检查会话:     python tmux_helper.py check <别名> <会话名> [--full]")
        print("  列出会话:     python tmux_helper.py list <别名>")
        print("  终止会话:     python tmux_helper.py kill <别名> <会话名>")
        print("\n选项:")
        print("  --full        显示完整输出（用于check命令）")
        print("\n示例:")
        print("  python tmux_helper.py run myserver deploy 'cd /app && npm install'")
        print("  python tmux_helper.py check myserver deploy")
        print("  python tmux_helper.py check myserver deploy --full")
        print("  python tmux_helper.py list myserver")
        print("  python tmux_helper.py kill myserver deploy")
        sys.exit(1)

    action = sys.argv[1]

    try:
        if action == 'run':
            if len(sys.argv) != 5:
                print("用法: python tmux_helper.py run <别名> <会话名> <命令>")
                sys.exit(1)
            alias = sys.argv[2]
            session_name = sys.argv[3]
            command = sys.argv[4]
            sys.exit(run_in_tmux(alias, session_name, command))

        elif action == 'check':
            if len(sys.argv) < 4:
                print("用法: python tmux_helper.py check <别名> <会话名> [--full]")
                sys.exit(1)
            alias = sys.argv[2]
            session_name = sys.argv[3]
            full = '--full' in sys.argv
            sys.exit(check_tmux_session(alias, session_name, full))

        elif action == 'list':
            if len(sys.argv) != 3:
                print("用法: python tmux_helper.py list <别名>")
                sys.exit(1)
            alias = sys.argv[2]
            sys.exit(list_tmux_sessions(alias))

        elif action == 'kill':
            if len(sys.argv) != 4:
                print("用法: python tmux_helper.py kill <别名> <会话名>")
                sys.exit(1)
            alias = sys.argv[2]
            session_name = sys.argv[3]
            sys.exit(kill_tmux_session(alias, session_name))

        else:
            print(f"✗ 未知操作: {action}")
            print("有效操作: run, check, list, kill")
            sys.exit(1)

    except subprocess.TimeoutExpired:
        print("✗ 操作超时")
        sys.exit(1)
    except Exception as e:
        print(f"✗ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
