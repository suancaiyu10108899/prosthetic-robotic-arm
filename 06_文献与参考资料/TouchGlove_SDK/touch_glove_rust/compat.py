"""
touch_glove_rust.compat — 原版 touch_glove.sdk API 兼容层

该模块提供与原版 `touch_glove.sdk.TouchGlove` 完全兼容的 Python 包装类，
让所有使用旧版 SDK 的脚本无需任何修改即可直接使用 Rust 实现。

兼容的接口：
  - TouchGlove(port, auto_init)
  - glove.open(port)
  - glove.close()
  - glove.start() / glove.stop()
  - glove.poll() -> FrameBatch (可迭代，frame.channel / frame.sensor_id / frame.disp / frame.force_field ...)
  - glove.stream(timeout, max_frames)
  - glove.sensor_ids
  - glove.get_bytes_per_second()
  - glove.get_total_bytes()
  - glove.enable_debug_logs(flag)
  - glove.set_log_callback(fn)
  - glove.set_error_callback(fn)
  - glove._api (兼容 stream.py 的内部 _api 访问)
  - glove._uid_received / glove._rtc_received
  - list_ports()
  - TS_IMAGE_CHANNELS / IMAGE_WIDTH / IMAGE_HEIGHT
"""

from __future__ import annotations
from typing import Callable, List, Optional
import errno
import time

from touch_glove_rust import (
    TouchGlove as _RustGlove,
    list_ports,
    IMAGE_WIDTH,
    IMAGE_HEIGHT,
    IMAGE_CHANNELS,
)

# ── 常量（向后兼容） ─────────────────────────────────────────────────────────

TS_IMAGE_CHANNELS = IMAGE_CHANNELS
# IMAGE_WIDTH / IMAGE_HEIGHT 直接从 touch_glove_rust 重导出，不需要重声明


# ── 内部 _api 代理（兼容 stream.py 直接访问低层接口） ───────────────────────

class _ApiProxy:
    """
    模拟原版 TouchGloveAPI 的低层接口。
    stream.py 通过 glove._api.xxx() 调用底层函数。
    """
    def __init__(self, glove_wrapper: "TouchGlove"):
        self._w = glove_wrapper  # 指向外层 TouchGlove 包装

    # --- 端口管理 ---
    def open_port(self, port: str) -> bool:
        try:
            return self._w.open(port)
        except Exception as e:
            print(f"[_api.open_port] {e}")
            return False

    def close_port(self):
        self._w._rust.close()

    # --- 状态 ---
    def get_state(self) -> int:
        if not self._w._rust.is_open:
            return 0  # CLOSED
        if self._w._rust.is_streaming:
            return 4  # STREAMING
        return 3  # READY

    def get_state_name(self, state: int) -> str:
        _names = {0: "CLOSED", 1: "OPENED", 2: "INITIALIZING", 3: "READY",
                  4: "STREAMING", 5: "ERROR"}
        return _names.get(state, "UNKNOWN")

    # --- UID & RTC ---
    def send_get_unique_id(self) -> bool:
        # Rust 的 open() 已自动完成 UID 请求，这里仅更新标志
        self._w._uid_received = bool(any(s for s in self._w._rust.sensor_ids))
        return True

    def send_rtc_sync(self, year, month, day, hour, minute, second, ms) -> bool:
        self._w._rtc_received = True
        return True

    # --- 轮询 ---
    def poll_read(self):
        # poll() 返回一个 FrameBatch；调用它会触发内部缓冲区消费
        self._w._rust.poll()

    # --- 统计 ---
    def get_total_bytes(self) -> int:
        return self._w._rust.get_total_bytes()

    def get_bytes_per_second(self) -> float:
        return self._w._rust.get_bytes_per_second()

    # --- 回调（兼容 stream.py 的 glove._api.set_log_callback 调用） ---
    def set_log_callback(self, fn: Optional[Callable]):
        self._w._log_cb = fn

    def set_error_callback(self, fn: Optional[Callable]):
        self._w._error_cb = fn


# ── 主兼容包装类 ─────────────────────────────────────────────────────────────

class TouchGlove:
    """
    原版 touch_glove.sdk.TouchGlove 的 Rust 替代实现。

    接口与原版完全兼容，内部转发给 touch_glove_rust.TouchGlove。
    """

    def __init__(
        self,
        port: Optional[str] = None,
        auto_init: bool = True,
        force_model: Optional[str] = None,
        pos_model: Optional[str] = None,
        dense_model: Optional[str] = None,
        enable_inference: bool = True,
    ):
        # 创建不自动初始化的 Rust 对象，手动控制 open()
        self._rust = _RustGlove(
            port=None,
            auto_init=False,
            force_model=force_model,
            pos_model=pos_model,
            dense_model=dense_model,
            enable_inference=enable_inference,
        )
        self._port = port

        # 兼容标志
        self._uid_received: bool = False
        self._rtc_received: bool = False
        self._debug_logs_enabled: bool = False
        self._log_cb: Optional[Callable] = None
        self._error_cb: Optional[Callable] = None
        self._last_open_error: Optional[str] = None

        # 内部 API 代理（供 stream.py 等使用 glove._api.xxx）
        self._api = _ApiProxy(self)

        if port and auto_init:
            ok = self.open(port)
            if not ok:
                detail = self._last_open_error or "unknown error"
                raise RuntimeError(
                    f"Failed to open serial port: {port}. Cause: {detail}"
                )

    # ── 上下文管理器 ─────────────────────────────────────────────────────────

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
        return False

    # ── 端口管理 ─────────────────────────────────────────────────────────────

    def open(self, port: str) -> bool:
        """
        打开串口并初始化设备（发送 UID 请求 + RTC 同步）。
        返回 True 表示成功，False 表示失败。
        """
        self._port = port
        self._last_open_error = None
        max_attempts = 4
        for attempt in range(1, max_attempts + 1):
            try:
                # PyO3 bound 方法：直接调用，不传 self
                result = self._rust.open(port)
                if result:
                    self._uid_received = True
                    self._rtc_received = True
                    return True

                self._last_open_error = (
                    "device init timeout (no UID/RTC ack within 2s)"
                )
                if attempt < max_attempts:
                    self._abort_partial_open()
                    time.sleep(0.25 * attempt)
                    continue

                emsg = (
                    f"Open returned false: {self._last_open_error}. "
                    "Check cable stability/device power and retry."
                )
                if self._error_cb:
                    self._error_cb(emsg)
                else:
                    print(f"[TouchGlove.open] {emsg}")
                return False

            except KeyboardInterrupt:
                self._abort_partial_open()
                emsg = "open interrupted by user (Ctrl+C)"
                self._last_open_error = emsg
                if self._error_cb:
                    self._error_cb(emsg)
                else:
                    print(f"[TouchGlove.open] {emsg}")
                return False

            except Exception as e:
                emsg = str(e)
                # Surface common Linux serial causes with direct next actions.
                if "Permission denied" in emsg or f"Errno {errno.EACCES}" in emsg:
                    emsg = (
                        f"{emsg}\n"
                        "Hint: add current user to dialout and re-login: "
                        "sudo usermod -aG dialout $USER"
                    )
                elif "Resource busy" in emsg or f"Errno {errno.EBUSY}" in emsg:
                    emsg = (
                        f"{emsg}\n"
                        "Hint: the port is occupied by another process. "
                        "Try: fuser -v /dev/ttyACM0"
                    )
                self._last_open_error = emsg

                if attempt < max_attempts:
                    self._abort_partial_open()
                    time.sleep(0.2 * attempt)
                    continue

                if self._error_cb:
                    self._error_cb(emsg)
                else:
                    print(f"[TouchGlove.open] {emsg}")
                return False

        return False

    def close(self):
        """关闭设备（发送 STOP + 关闭串口）。"""
        try:
            self._rust.close()
        except Exception:
            pass

    def _abort_partial_open(self):
        try:
            abort = getattr(self._rust, "abort_open", None)
            if abort is not None:
                abort()
            else:
                self._rust.close()
        except Exception:
            pass

    @property
    def is_open(self) -> bool:
        return self._rust.is_open

    # ── 流控制 ───────────────────────────────────────────────────────────────

    def start(self):
        """开始图像流。"""
        self._rust.start()

    def stop(self):
        """停止图像流。"""
        self._rust.stop()

    def calibrate(self):
        """执行基准校准（捕捉当前图像作为零力的基点）。"""
        self._rust.calibrate()

    # ── 数据采集 ─────────────────────────────────────────────────────────────

    def poll(self):
        """
        轮询一批帧。返回可迭代的 FrameBatch。

        每帧提供:
          frame.channel     : int (0-4)
          frame.sensor_id   : str
          frame.seq_id      : int
          frame.timestamp_us: int
          frame.disp        : np.ndarray shape (32, 32, 3), dtype=float32 | None
          frame.force_field : np.ndarray shape (32, 32, 3), dtype=float32 | None
        """
        return self._rust.poll()

    def stream(self, timeout: Optional[float] = None, max_frames: Optional[int] = None):
        """
        流式采集，返回 FrameBatch 列表。
        建议在循环中调用 poll() 代替此方法以获得更低延迟。
        """
        return self._rust.stream(max_frames=max_frames, timeout=timeout)

    # ── 属性 ─────────────────────────────────────────────────────────────────

    @property
    def sensor_ids(self) -> List[str]:
        """每个通道的传感器 UID（十六进制字符串列表）。"""
        return list(self._rust.sensor_ids)

    def get_bytes_per_second(self) -> float:
        return self._rust.get_bytes_per_second()

    def get_total_bytes(self) -> int:
        return self._rust.get_total_bytes()

    def get_dense_update_count(self) -> int:
        getter = getattr(self._rust, "get_dense_update_count", None)
        if getter is None:
            return 0
        return int(getter())

    # ── 调试 / 回调 ──────────────────────────────────────────────────────────

    def enable_debug_logs(self, flag: bool):
        """原版接口兼容：Rust 版通过 RUST_LOG=touch_glove=debug 环境变量控制。"""
        self._debug_logs_enabled = flag

    def set_log_callback(self, fn: Optional[Callable]):
        """设置日志回调（原版兼容，Rust 层不支持，此处仅记录）。"""
        self._log_cb = fn

    def set_error_callback(self, fn: Optional[Callable]):
        """设置错误回调（原版兼容）。"""
        self._error_cb = fn

    # ── 兼容 stream.py 的 reinit ────────────────────────────────────────────

    def reinit(self) -> bool:
        """不关闭端口重新初始化（错误恢复）。"""
        try:
            result = self._rust.reinit()
            if result:
                self._uid_received = True
                self._rtc_received = True
            return result
        except Exception:
            return False
