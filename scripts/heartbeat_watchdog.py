#!/usr/bin/env python3
import subprocess
import time

# 配置区
PROBE_MESSAGE = "🦞 [心跳检测] 龙虾拍了拍网关，还在喘气吗？"
SESSION_KEY = "agent:main:main"  # 默认主会话
CHECK_INTERVAL = 300  # 5分钟检测一次
RETRY_TIMINGS = [30, 40, 50]  # 递增等待时间


def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip(), result.returncode
    except Exception as e:
        return str(e), 1


def send_probe():
    print(f"[{time.ctime()}] 发送心跳探测...")
    cmd = f'openclaw message send --message "{PROBE_MESSAGE}"'
    run_command(cmd)


def check_for_reply(since_ts):
    """检查自 since_ts 之后是否有 assistant 的回复"""
    # 使用 openclaw sessions history 获取最近消息
    # 逻辑：查找最近的一条消息，如果是 assistant 且时间在 since_ts 之后，认为活跃
    cmd = f"openclaw sessions history --sessionKey {SESSION_KEY} --limit 5 --json"
    output, code = run_command(cmd)
    if code != 0:
        return False

    import json

    try:
        history = json.loads(output)
        for msg in history:
            # 简化逻辑：只要有任何消息产生（或者是特定回复），即认为网关存活
            # 这里我们检测是否有 timestamp 大于 since_ts 的消息
            # 注意：openclaw 返回的通常是 ISO 格式，需要转换或简单对比
            return True  # 只要能拿到 history，说明 Gateway 至少响应了 API
    except:
        return False
    return False


def restart_gateway():
    print(f"[{time.ctime()}] 🚨 连续三次无响应，正在重启网关...")
    run_command("openclaw gateway restart")


def main():
    print(f"🦞 龙虾守护进程启动！每 {CHECK_INTERVAL}s 巡逻一次。")
    while True:
        send_probe()
        start_wait = time.time()

        success = False
        for i, wait_time in enumerate(RETRY_TIMINGS):
            print(f"等待 {wait_time}s 确认回复...")
            time.sleep(wait_time)

            # 检查网关是否还能吐出历史记录（最基本的心跳）
            _, code = run_command("openclaw status --json")
            if code == 0:
                print("✅ 网关响应正常。")
                success = True
                break
            else:
                if i < len(RETRY_TIMINGS) - 1:
                    print(f"⚠️ 无响应，尝试第 {i + 2} 次提醒...")
                    send_probe()
                else:
                    restart_gateway()
                    # 重启后多等一会儿让它缓过来
                    time.sleep(60)

        if success:
            time.sleep(CHECK_INTERVAL)
        else:
            # 如果走到了重启逻辑，循环会继续，下一轮在 5 分钟后
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
