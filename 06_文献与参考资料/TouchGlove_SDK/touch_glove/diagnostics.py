"""Runtime diagnostics for Touch Glove SDK delivery packages."""

from __future__ import annotations

import argparse
import ctypes
import os
import platform
import shutil
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


TARGET_CHANNELS = 5
DEFAULT_TARGET_HZ = 30.0


@dataclass
class Check:
    status: str
    name: str
    detail: str = ""
    critical: bool = False


class Reporter:
    def __init__(self) -> None:
        self.checks: list[Check] = []

    def section(self, title: str) -> None:
        print(f"\n{'=' * 72}")
        print(title)
        print(f"{'=' * 72}", flush=True)

    def add(self, status: str, name: str, detail: str = "", *, critical: bool = False) -> None:
        self.checks.append(Check(status, name, detail, critical))
        prefix = f"[{status}]".ljust(8)
        print(f"{prefix} {name}")
        if detail:
            for line in detail.splitlines():
                print(f"         {line}")
        sys.stdout.flush()

    def has_critical_failure(self) -> bool:
        return any(c.critical and c.status == "FAIL" for c in self.checks)


def _run_command(args: list[str], timeout: float = 8.0) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError as exc:
        return 127, "", str(exc)
    except subprocess.TimeoutExpired as exc:
        return 124, exc.stdout or "", f"timeout after {timeout:.1f}s"


def _loadable_library(names: Iterable[str]) -> tuple[bool, str]:
    errors: list[str] = []
    for name in names:
        try:
            ctypes.CDLL(name)
            return True, name
        except OSError as exc:
            errors.append(f"{name}: {exc}")
    return False, "; ".join(errors[-2:])


def check_system_cuda(reporter: Reporter) -> dict[str, object]:
    reporter.section("1. CUDA / NVIDIA Driver")

    info: dict[str, object] = {"gpu_count": 0, "old_gpu": False}
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        reporter.add(
            "FAIL",
            "nvidia-smi",
            "未找到 nvidia-smi。系统未安装 NVIDIA 驱动，或当前环境无法访问 GPU。",
            critical=True,
        )
    else:
        code, out, err = _run_command(
            [
                nvidia_smi,
                "--query-gpu=index,name,driver_version,memory.total,compute_cap",
                "--format=csv,noheader,nounits",
            ]
        )
        if code != 0:
            code, out, err = _run_command(
                [
                    nvidia_smi,
                    "--query-gpu=index,name,driver_version,memory.total",
                    "--format=csv,noheader,nounits",
                ]
            )

        if code == 0 and out:
            lines = [line.strip() for line in out.splitlines() if line.strip()]
            info["gpu_count"] = len(lines)
            reporter.add("PASS", "NVIDIA GPU detected", "\n".join(lines))

            warnings: list[str] = []
            for line in lines:
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 4:
                    try:
                        memory_mb = float(parts[3])
                        if memory_mb < 2048:
                            warnings.append(f"GPU {parts[0]} 显存小于 2GB，可能影响推理稳定性。")
                    except ValueError:
                        pass
                if len(parts) >= 5:
                    try:
                        compute_cap = float(parts[4])
                        if compute_cap < 6.0:
                            info["old_gpu"] = True
                            warnings.append(
                                f"GPU {parts[0]} compute capability={compute_cap:.1f} 偏旧，后续以实测 30Hz 结果为准。"
                            )
                    except ValueError:
                        pass
            if warnings:
                reporter.add("WARN", "GPU capability note", "\n".join(warnings))
        else:
            reporter.add(
                "FAIL",
                "nvidia-smi query",
                err or out or "nvidia-smi 无法查询 GPU。",
                critical=True,
            )

    ok, detail = _loadable_library(["libcuda.so.1", "libcuda.so"])
    reporter.add(
        "PASS" if ok else "WARN",
        "CUDA driver library",
        f"可加载: {detail}" if ok else f"无法直接加载 libcuda: {detail}",
        critical=not ok,
    )

    runtime_ok, runtime_detail = _loadable_library(["libcudart.so.12", "libcudart.so"])
    reporter.add(
        "PASS" if runtime_ok else "INFO",
        "CUDA runtime library",
        f"可加载: {runtime_detail}"
        if runtime_ok
        else "未直接找到 libcudart；如果 onnxruntime-gpu 通过 Python wheel 自带 CUDA 运行库，这一项可以忽略。",
    )

    return info


def _varint(value: int) -> bytes:
    out = bytearray()
    while True:
        to_write = value & 0x7F
        value >>= 7
        if value:
            out.append(to_write | 0x80)
        else:
            out.append(to_write)
            break
    return bytes(out)


def _key(field_number: int, wire_type: int) -> bytes:
    return _varint((field_number << 3) | wire_type)


def _varint_field(field_number: int, value: int) -> bytes:
    return _key(field_number, 0) + _varint(value)


def _bytes_field(field_number: int, value: bytes) -> bytes:
    return _key(field_number, 2) + _varint(len(value)) + value


def _str_field(field_number: int, value: str) -> bytes:
    return _bytes_field(field_number, value.encode("utf-8"))


def _msg_field(field_number: int, value: bytes) -> bytes:
    return _bytes_field(field_number, value)


def _tensor_type(shape: list[int]) -> bytes:
    # TypeProto.tensor_type.elem_type = FLOAT(1), shape.dim[*].dim_value = shape
    dims = b"".join(_msg_field(1, _varint_field(1, dim)) for dim in shape)
    tensor_shape = dims
    tensor_type = _varint_field(1, 1) + _msg_field(2, tensor_shape)
    return _msg_field(1, tensor_type)


def _value_info(name: str, shape: list[int]) -> bytes:
    return _str_field(1, name) + _msg_field(2, _tensor_type(shape))


def _node(op_type: str, inputs: list[str], outputs: list[str], name: str) -> bytes:
    msg = b"".join(_str_field(1, item) for item in inputs)
    msg += b"".join(_str_field(2, item) for item in outputs)
    msg += _str_field(3, name)
    msg += _str_field(4, op_type)
    return msg


def build_add_model(shape: list[int]) -> bytes:
    """Build a tiny ONNX Add model without depending on the onnx Python package."""
    add_node = _node("Add", ["x", "y"], ["z"], "add")
    graph = _msg_field(1, add_node)
    graph += _str_field(2, "touch_glove_ort_cuda_smoke")
    graph += _msg_field(11, _value_info("x", shape))
    graph += _msg_field(11, _value_info("y", shape))
    graph += _msg_field(12, _value_info("z", shape))

    opset = _varint_field(2, 13)
    model = _varint_field(1, 7)
    model += _str_field(2, "touch_glove_sdk_diagnostics")
    model += _msg_field(7, graph)
    model += _msg_field(8, opset)
    return model


def check_python_onnxruntime(reporter: Reporter, ort_runs: int) -> dict[str, object]:
    reporter.section("2. Python ONNX Runtime")

    info: dict[str, object] = {"ort_cuda_ok": False}
    try:
        import numpy as np
    except Exception as exc:  # pragma: no cover - depends on customer machine
        reporter.add("FAIL", "numpy import", repr(exc), critical=True)
        return info

    try:
        import onnxruntime as ort
    except Exception as exc:
        reporter.add(
            "FAIL",
            "onnxruntime import",
            (
                f"{exc!r}\n"
                "建议安装 GPU 版: pip install onnxruntime-gpu\n"
                "注意: 当前 Rust SDK 的推理在原生扩展中完成，Python 层看不到显式 import onnxruntime 是正常现象。"
            ),
            critical=True,
        )
        return info

    providers = list(ort.get_available_providers())
    device = getattr(ort, "get_device", lambda: "unknown")()
    reporter.add(
        "PASS",
        "onnxruntime import",
        f"version={getattr(ort, '__version__', 'unknown')}, get_device()={device}",
    )
    reporter.add("INFO", "available providers", ", ".join(providers) or "(empty)")

    model = build_add_model([1, 36864])
    x = np.ones((1, 36864), dtype=np.float32)
    y = np.full((1, 36864), 2.0, dtype=np.float32)

    try:
        cpu_session = ort.InferenceSession(model, providers=["CPUExecutionProvider"])
        z = cpu_session.run(None, {"x": x, "y": y})[0]
        if np.allclose(z, 3.0):
            reporter.add("PASS", "CPUExecutionProvider smoke test", "1x36864 Add 输出正确。")
        else:
            reporter.add("FAIL", "CPUExecutionProvider smoke test", "输出不符合预期。", critical=True)
    except Exception as exc:
        reporter.add("FAIL", "CPUExecutionProvider smoke test", repr(exc), critical=True)

    if "CUDAExecutionProvider" not in providers:
        reporter.add(
            "FAIL",
            "CUDAExecutionProvider",
            "Python ONNX Runtime 未列出 CUDAExecutionProvider。请确认安装的是 onnxruntime-gpu 且 CUDA/cuDNN 版本匹配。",
            critical=True,
        )
        return info

    try:
        cuda_session = ort.InferenceSession(
            model,
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
        )
        active = list(cuda_session.get_providers())
        z = cuda_session.run(None, {"x": x, "y": y})[0]
        if not np.allclose(z, 3.0):
            raise RuntimeError("CUDA session output mismatch")

        warmup = min(20, max(3, ort_runs // 10))
        for _ in range(warmup):
            cuda_session.run(None, {"x": x, "y": y})
        start = time.perf_counter()
        for _ in range(ort_runs):
            cuda_session.run(None, {"x": x, "y": y})
        elapsed = max(time.perf_counter() - start, 1e-9)
        ms_per_run = elapsed * 1000.0 / max(ort_runs, 1)
        runs_per_sec = ort_runs / elapsed
        info["ort_cuda_ok"] = True
        reporter.add(
            "PASS",
            "CUDAExecutionProvider smoke test",
            (
                f"session providers={active}\n"
                f"dummy Add benchmark: {ms_per_run:.3f} ms/run, {runs_per_sec:.1f} runs/s\n"
                "该基准只验证 CUDA EP 可创建和运行，不代表手套 CNN 模型的真实速度。"
            ),
        )
    except Exception as exc:
        reporter.add(
            "FAIL",
            "CUDAExecutionProvider smoke test",
            (
                f"{exc!r}\n"
                "这通常表示 onnxruntime-gpu 与本机 NVIDIA driver / CUDA / cuDNN 运行库不匹配。"
            ),
            critical=True,
        )

    return info


def check_sdk_binary(reporter: Reporter, base_dir: Path) -> dict[str, object]:
    reporter.section("3. Touch Glove SDK Binary")

    info: dict[str, object] = {"sdk_onnx_marker": False}
    so_files = sorted((base_dir / "touch_glove_rust").glob("_rust*.so"))
    if not so_files:
        reporter.add("FAIL", "Rust native extension", "未找到 touch_glove_rust/_rust*.so", critical=True)
        return info

    so_path = so_files[0]
    reporter.add("PASS", "Rust native extension", str(so_path))
    try:
        data = so_path.read_bytes()
    except Exception as exc:
        reporter.add("WARN", "binary scan", repr(exc))
        return info

    markers = {
        "onnxruntime": b"onnxruntime",
        "CPUExecutionProvider": b"CPUExecutionProvider",
        "CUDAExecutionProvider": b"CUDAExecutionProvider",
    }
    found = [name for name, marker in markers.items() if marker in data]
    info["sdk_onnx_marker"] = "onnxruntime" in found
    reporter.add(
        "PASS" if info["sdk_onnx_marker"] else "WARN",
        "SDK ONNX Runtime marker",
        ", ".join(found) if found else "未在二进制中扫描到明显 ORT 字符串。",
    )

    if b"The execution provider could not be registered because its corresponding Cargo feature is not enabled" in data:
        reporter.add(
            "INFO",
            "SDK provider note",
            "二进制中包含 ort 的通用 provider 错误字符串；脚本无法仅通过扫描证明 SDK 当前实际使用 CPU 还是 CUDA。",
        )

    code, out, err = _run_command(["ldd", str(so_path)])
    if code == 0:
        ort_lines = [line for line in out.splitlines() if "onnxruntime" in line.lower()]
        detail = "\n".join(ort_lines) if ort_lines else "ldd 未显示外部 libonnxruntime，通常表示 ORT 被静态打进了原生扩展。"
        reporter.add("INFO", "ldd on native extension", detail)
    else:
        reporter.add("INFO", "ldd on native extension", err or out)

    try:
        import touch_glove_rust
        from touch_glove.sdk import IMAGE_HEIGHT, IMAGE_WIDTH, TS_IMAGE_CHANNELS

        reporter.add(
            "PASS",
            "SDK import",
            (
                f"touch_glove_rust version={getattr(touch_glove_rust, '__version__', 'unknown')}\n"
                f"channels={TS_IMAGE_CHANNELS}, image={IMAGE_WIDTH}x{IMAGE_HEIGHT}"
            ),
        )
    except Exception as exc:
        reporter.add("FAIL", "SDK import", repr(exc), critical=True)

    return info


def _port_access_hint(port: str) -> Optional[str]:
    if not os.path.exists(port):
        return f"设备不存在: {port}"
    if not os.access(port, os.R_OK | os.W_OK):
        return (
            f"权限不足: {port}\n"
            "可尝试: sudo usermod -aG dialout $USER 后重新登录，或使用 sg dialout -c 'python3 get_force_data_test.py'"
        )
    return None


def _seq_delta(prev: int, cur: int) -> int:
    if cur >= prev:
        return cur - prev
    return (cur + (1 << 32)) - prev


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(round((len(ordered) - 1) * pct / 100.0))
    return ordered[max(0, min(idx, len(ordered) - 1))]


def run_device_rate_test(reporter: Reporter, args: argparse.Namespace) -> Optional[bool]:
    reporter.section("4. Five-Finger SDK Rate Test")

    if args.skip_device:
        reporter.add("SKIP", "device test", "命令行指定 --skip-device，已跳过真实手套测速。")
        return None

    try:
        from touch_glove.sdk import TouchGlove, list_ports
    except Exception as exc:
        reporter.add("FAIL", "SDK import for device test", repr(exc), critical=True)
        return False

    ports = list_ports()
    port = args.port or (ports[0] if ports else "")
    if not port:
        reporter.add("FAIL", "serial port", "未找到串口设备。请检查 USB 连接。", critical=True)
        return False

    hint = _port_access_hint(port)
    if hint:
        reporter.add("FAIL", "serial port access", hint, critical=True)
        return False

    reporter.add("INFO", "selected port", port)
    glove = TouchGlove(port=None, auto_init=False)
    opened = False
    started = False

    try:
        t0 = time.perf_counter()
        opened = bool(glove.open(port))
        open_elapsed = time.perf_counter() - t0
        if not opened:
            reporter.add("FAIL", "open glove", "glove.open() returned False", critical=True)
            return False
        reporter.add("PASS", "open glove", f"{open_elapsed:.3f}s")

        glove.start()
        started = True
        reporter.add("PASS", "start stream", f"warming up {args.warmup:.1f}s")
        warmup_end = time.perf_counter() + args.warmup
        while time.perf_counter() < warmup_end:
            glove.poll()
            time.sleep(args.poll_sleep)

        if not args.no_calibrate:
            try:
                glove.calibrate()
                reporter.add("PASS", "calibrate", "已执行基准校准。")
            except Exception as exc:
                reporter.add("WARN", "calibrate", repr(exc))

        first_seq: list[Optional[int]] = [None] * TARGET_CHANNELS
        last_seq: list[Optional[int]] = [None] * TARGET_CHANNELS
        seq_frames = [0] * TARGET_CHANNELS
        returned_frames = [0] * TARGET_CHANNELS
        seq_jumps = [0] * TARGET_CHANNELS
        poll_ms: list[float] = []
        force_samples: dict[int, tuple[float, float, float, float, float]] = {}

        reporter.add("INFO", "measure", f"duration={args.duration:.1f}s, target={args.target_hz:.1f}Hz/channel")
        measure_start = time.perf_counter()
        deadline = measure_start + args.duration
        while time.perf_counter() < deadline:
            poll_start = time.perf_counter()
            batch = glove.poll()
            poll_ms.append((time.perf_counter() - poll_start) * 1000.0)

            for frame in batch:
                ch = int(frame.channel)
                if ch < 0 or ch >= TARGET_CHANNELS:
                    continue
                returned_frames[ch] += 1
                seq = int(frame.seq_id)
                if first_seq[ch] is None:
                    first_seq[ch] = seq
                    last_seq[ch] = seq
                else:
                    assert last_seq[ch] is not None
                    delta = _seq_delta(last_seq[ch], seq)
                    if delta > 1:
                        seq_jumps[ch] += delta - 1
                    seq_frames[ch] += delta
                    last_seq[ch] = seq
                force_samples[ch] = (
                    float(getattr(frame, "fx", 0.0)),
                    float(getattr(frame, "fy", 0.0)),
                    float(getattr(frame, "fz", 0.0)),
                    float(getattr(frame, "x", 0.0)),
                    float(getattr(frame, "y", 0.0)),
                )

            time.sleep(args.poll_sleep)

        elapsed = max(time.perf_counter() - measure_start, 1e-9)
        returned_hz = [count / elapsed for count in returned_frames]
        seq_hz = [count / elapsed for count in seq_frames]
        active_channels = sum(1 for hz in returned_hz if hz > 0)
        min_returned = min(returned_hz) if returned_hz else 0.0
        avg_returned = statistics.mean(returned_hz) if returned_hz else 0.0
        min_seq = min(seq_hz) if seq_hz else 0.0
        avg_seq = statistics.mean(seq_hz) if seq_hz else 0.0

        lines = [
            "ch | app_returned_hz | observed_seq_hz | returned | seq_delta | skipped_by_poll | last(force xyz, pos xy)",
            "---+-----------------+-----------------+----------+-----------+-----------------+--------------------------",
        ]
        for ch in range(TARGET_CHANNELS):
            sample = force_samples.get(ch)
            sample_text = (
                f"({sample[0]:.2f}, {sample[1]:.2f}, {sample[2]:.2f}), ({sample[3]:.2f}, {sample[4]:.2f})"
                if sample
                else "(no sample)"
            )
            lines.append(
                f"{ch:2d} | {returned_hz[ch]:15.2f} | {seq_hz[ch]:15.2f} | "
                f"{returned_frames[ch]:8d} | {seq_frames[ch]:9d} | {seq_jumps[ch]:15d} | {sample_text}"
            )

        bytes_per_sec = 0.0
        try:
            bytes_per_sec = float(glove.get_bytes_per_second())
        except Exception:
            pass

        p50 = statistics.median(poll_ms) if poll_ms else 0.0
        p95 = _percentile(poll_ms, 95.0)
        max_poll = max(poll_ms) if poll_ms else 0.0
        lines.extend(
            [
                "",
                f"active_channels={active_channels}/{TARGET_CHANNELS}",
                f"app_returned_hz: min={min_returned:.2f}, avg={avg_returned:.2f}",
                f"observed_seq_hz: min={min_seq:.2f}, avg={avg_seq:.2f}",
                f"poll latency: p50={p50:.2f}ms, p95={p95:.2f}ms, max={max_poll:.2f}ms",
                f"serial throughput={bytes_per_sec / 1024.0:.1f} KiB/s",
            ]
        )

        pass_rate = active_channels == TARGET_CHANNELS and min_returned >= args.target_hz
        reporter.add(
            "PASS" if pass_rate else "FAIL",
            f"five-finger {args.target_hz:.0f}Hz app-level rate",
            "\n".join(lines),
            critical=not pass_rate,
        )
        if not pass_rate and min_seq >= args.target_hz:
            reporter.add(
                "WARN",
                "rate interpretation",
                (
                    "设备侧 seq 速率达到目标，但 Python 应用实际返回速率不足；"
                    "这通常说明主机推理/轮询处理太慢，或 GPU/CPU 环境不匹配。"
                ),
            )
        return pass_rate

    except KeyboardInterrupt:
        reporter.add("WARN", "device test interrupted", "用户中断。")
        return False
    except Exception as exc:
        reporter.add("FAIL", "device test exception", repr(exc), critical=True)
        return False
    finally:
        try:
            if started:
                glove.stop()
                time.sleep(0.1)
        except Exception:
            pass
        try:
            if opened:
                glove.close()
        except Exception:
            pass


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Touch Glove SDK CUDA / ONNX Runtime / five-finger 30Hz diagnostic test."
    )
    parser.add_argument("--port", default="", help="指定串口，例如 /dev/ttyACM0。默认自动选择第一个串口。")
    parser.add_argument("--duration", type=float, default=8.0, help="真实手套测速时长，单位秒。默认 8。")
    parser.add_argument("--warmup", type=float, default=2.0, help="测速前预热时长，单位秒。默认 2。")
    parser.add_argument("--target-hz", type=float, default=DEFAULT_TARGET_HZ, help="每个手指目标输出 Hz。默认 30。")
    parser.add_argument("--poll-sleep", type=float, default=0.001, help="两次 poll 之间的休眠秒数。默认 0.001。")
    parser.add_argument("--ort-runs", type=int, default=200, help="ONNX Runtime CUDA smoke benchmark 运行次数。默认 200。")
    parser.add_argument("--skip-device", action="store_true", help="只做 CUDA/ONNX/SDK 环境检查，不连接真实手套。")
    parser.add_argument("--no-calibrate", action="store_true", help="真实手套测速前不执行 calibrate。")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    base_dir = Path(__file__).resolve().parents[1]
    if str(base_dir) not in sys.path:
        sys.path.insert(0, str(base_dir))

    reporter = Reporter()
    reporter.section("Touch Glove SDK Diagnostic")
    reporter.add("INFO", "time", time.strftime("%Y-%m-%d %H:%M:%S %z"))
    reporter.add("INFO", "python", sys.version.replace("\n", " "))
    reporter.add("INFO", "platform", f"{platform.platform()} ({platform.machine()})")
    reporter.add("INFO", "package dir", str(base_dir))
    reporter.add(
        "INFO",
        "important note",
        (
            "Python 层看不到 import onnxruntime 并不等于 SDK 没有 ONNX；"
            "当前交付包的力/位置推理由 Rust 原生扩展完成。"
        ),
    )

    check_system_cuda(reporter)
    check_python_onnxruntime(reporter, max(1, args.ort_runs))
    check_sdk_binary(reporter, base_dir)
    run_device_rate_test(reporter, args)

    reporter.section("Summary")
    failures = [c for c in reporter.checks if c.critical and c.status == "FAIL"]
    if failures:
        reporter.add(
            "FAIL",
            "overall",
            "\n".join(f"{c.name}: {c.detail.splitlines()[0] if c.detail else ''}" for c in failures),
        )
        return 1

    reporter.add("PASS", "overall", "CUDA/ONNX Runtime/SDK/五指速率测试未发现关键失败。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
