"""Installed demo entrypoint for touch-glove."""

from __future__ import annotations

import errno
import os
import grp
import pwd
import time

from touch_glove.sdk import TouchGlove, list_ports


def _port_access_hint(port: str) -> str | None:
    if not os.path.exists(port):
        return f"设备不存在: {port}"

    try:
        fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        os.close(fd)
        return None
    except OSError as e:
        if e.errno == errno.EACCES:
            user = pwd.getpwuid(os.getuid()).pw_name
            active_groups = {grp.getgrgid(g).gr_name for g in os.getgroups()}
            dialout_members = set(grp.getgrnam("dialout").gr_mem)

            if user in dialout_members and "dialout" not in active_groups:
                return (
                    f"权限不足: {port} (EACCES)。\n"
                    "检测到你已在 dialout 组，但当前会话尚未加载该组。\n"
                    "可立即使用: sg dialout -c 'python scripts/get_force_data.py'\n"
                    "或执行 newgrp dialout / 重新登录后再运行。"
                )
            return (
                f"权限不足: {port} (EACCES)。\n"
                "请执行: sudo usermod -aG dialout $USER\n"
                "然后重新登录，或在当前终端执行: newgrp dialout"
            )
        if e.errno == errno.EBUSY:
            return (
                f"设备被占用: {port} (EBUSY)。\n"
                "请执行: fuser -v /dev/ttyACM0 以定位占用进程"
            )
        return f"无法访问设备 {port}: {e}"


def main() -> int:
    ports = list_ports()
    if not ports:
        print("No serial ports found.")
        return 1

    port = ports[0]
    hint = _port_access_hint(port)
    if hint is not None:
        print(hint)
        return 2

    print(f"Connecting to {port}... (重启后首次连接可能需要数秒，请勿立即 Ctrl+C)")

    glove = None
    for attempt in (1, 2):
        try:
            glove = TouchGlove(port)
            break
        except Exception as e:
            msg = str(e)
            if "device init timeout" in msg and attempt == 1:
                print("设备初始化超时，1 秒后自动重试一次...")
                time.sleep(1.0)
                continue
            print(f"Open failed: {e}")
            print("排查建议: 1) groups 检查是否包含 dialout 2) fuser -v /dev/ttyACM0 检查占用")
            return 2

    if glove is None:
        print("Open failed: unknown initialization error")
        return 2

    with glove:
        if not glove.is_open:
            print("设备未打开，退出。")
            return 2
        tare_offsets = {}
        do_calibrate = True
        do_tare = True

        while True:
            glove.start()
            if do_calibrate:
                print("Stream started. Calibrating in 2 seconds...")
                cal_end = time.time() + 2.0
                while time.time() < cal_end:
                    glove.poll()
                    time.sleep(0.01)
                glove.calibrate()
            else:
                print("Stream restarted. Using previous calibration.")

            if do_tare:
                print("提示: 使用1s内的平均力进行去皮，然后再启动输出。")
                tare_sums = {}
                tare_cnts = {}
                tare_end = time.time() + 1.0
                while time.time() < tare_end:
                    batch = glove.poll()
                    for frame in batch:
                        ch = int(frame.channel)
                        if ch not in tare_sums:
                            tare_sums[ch] = [0.0, 0.0, 0.0]
                            tare_cnts[ch] = 0
                        tare_sums[ch][0] += float(frame.fx)
                        tare_sums[ch][1] += float(frame.fy)
                        tare_sums[ch][2] += float(frame.fz)
                        tare_cnts[ch] += 1
                    time.sleep(0.002)

                tare_offsets = {}
                for ch, sums in tare_sums.items():
                    n = max(tare_cnts.get(ch, 0), 1)
                    tare_offsets[ch] = (sums[0] / n, sums[1] / n, sums[2] / n)
            elif not tare_offsets:
                print("提示: 未执行去皮，当前输出为原始力值。")

            print("Calibrated! Press Ctrl+C to stop.")

            try:
                while True:
                    batch = glove.poll()
                    for frame in batch:
                        ch = int(frame.channel)
                        off = tare_offsets.get(ch, (0.0, 0.0, 0.0))
                        fx = float(frame.fx) - off[0]
                        fy = float(frame.fy) - off[1]
                        fz = float(frame.fz) - off[2]
                        print(
                            f"CH {frame.channel} | "
                            f"Force: ({fx:5.1f}, {fy:5.1f}, {fz:5.1f}) N | "
                            f"Pos: ({frame.x:4.1f}, {frame.y:4.1f}) mm"
                        )
                    time.sleep(0.02)
            except KeyboardInterrupt:
                import sys
                print("Stopping...", file=sys.stderr)
                glove.stop()
                choice = input("回车=快速重启(不重校准), c=重新校准, q=退出: ").strip().lower()
                if choice == "q":
                    break
                do_calibrate = choice == "c"
                do_tare = do_calibrate
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
