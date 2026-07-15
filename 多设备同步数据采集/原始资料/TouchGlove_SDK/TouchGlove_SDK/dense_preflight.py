#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Runtime preflight for TouchGlove dense CUDA inference.

The realtime programs load the encrypted dense model in Rust.  This helper runs
that exact Rust initialization path in a short-lived child process so CUDA
driver/provider hangs or crashes do not freeze the GUI or ROS2 node.
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DENSE_MODEL_PATH = SCRIPT_DIR / "models" / "dense_3ch.enc"
DEFAULT_TIMEOUT_S = 60.0
OK_MARKER = "RUST_DENSE_PREFLIGHT_OK"


def resolve_model_path(model_path: str | os.PathLike[str]) -> Path:
    path = Path(model_path).expanduser()
    if not path.is_absolute():
        path = SCRIPT_DIR / path
    return path.resolve()


def _build_child_env() -> dict[str, str]:
    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH", "")
    parts = [str(SCRIPT_DIR)]
    if pythonpath:
        parts.append(pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(parts)
    env.setdefault("ORT_LOG_SEVERITY_LEVEL", "3")
    env.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-touch-glove")
    return env


def _trim_output(text: str, max_chars: int = 4000) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def _terminate_process(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=2.0)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
        try:
            proc.wait(timeout=2.0)
        except Exception:
            pass


def _returncode_text(returncode: int) -> str:
    if returncode < 0:
        signum = -returncode
        try:
            name = signal.Signals(signum).name
        except Exception:
            name = f"signal {signum}"
        return f"{returncode} ({name})"
    return str(returncode)


def _format_failure(reason: str, output: str = "") -> str:
    message = (
        f"Rust dense CUDA 自检失败: {reason}\n\n"
        "请先确认当前命令使用 Python 3.10:\n"
        "python3 --version\n\n"
        "然后在当前 Python 环境中执行以下配置后重试:\n"
        "pip install numpy PySide6 matplotlib cryptography onnxruntime-gpu==1.23.2 "
        "\"nvidia-cuda-runtime-cu12>=12,<13\" \"nvidia-cuda-nvrtc-cu12>=12,<13\" "
        "\"nvidia-cublas-cu12>=12,<13\" \"nvidia-cufft-cu12>=11,<12\" "
        "\"nvidia-curand-cu12>=10,<11\" \"nvidia-cudnn-cu12>=9,<10\"\n\n"
        "然后运行:\n"
        "python3 dense_preflight.py\n"
        "python3 check_cuda_env.py --verbose\n\n"
        "如果仍失败，请确认 nvidia-smi 正常，并把上面两条检测命令的完整输出发给维护者。"
    )
    if output:
        message += f"\n\n子进程输出:\n{_trim_output(output)}"
    return message


def run_rust_dense_preflight(
    model_path: str | os.PathLike[str] = DEFAULT_DENSE_MODEL_PATH,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    cancel_event=None,
) -> tuple[bool, str]:
    model = resolve_model_path(model_path)
    if not model.exists():
        return False, _format_failure(f"模型文件不存在: {model}")

    code = (
        "import sys\n"
        "from touch_glove.sdk import TouchGlove\n"
        "model = sys.argv[1]\n"
        "g = TouchGlove(None, auto_init=False, dense_model=model, enable_inference=True)\n"
        "print('RUST_DENSE_PREFLIGHT_OK', flush=True)\n"
    )
    cmd = [sys.executable, "-c", code, str(model)]
    proc = subprocess.Popen(
        cmd,
        cwd=str(SCRIPT_DIR),
        env=_build_child_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    deadline = time.monotonic() + max(float(timeout_s), 1.0)
    while True:
        if proc.poll() is not None:
            output = proc.communicate()[0] if proc.stdout is not None else ""
            if proc.returncode == 0 and OK_MARKER in output:
                return True, "Rust dense CUDA 初始化通过。"
            return False, _format_failure(
                f"子进程退出码 {_returncode_text(int(proc.returncode or 0))}",
                output,
            )

        if cancel_event is not None and cancel_event.is_set():
            _terminate_process(proc)
            return False, "Rust dense CUDA 自检已取消。"

        if time.monotonic() >= deadline:
            _terminate_process(proc)
            output = proc.communicate()[0] if proc.stdout is not None else ""
            return False, _format_failure(
                f"CUDAExecutionProvider 注册超过 {int(timeout_s)} 秒无响应",
                output,
            )

        time.sleep(0.1)


def main() -> int:
    parser = argparse.ArgumentParser(description="TouchGlove Rust dense CUDA preflight.")
    parser.add_argument("--model", default=str(DEFAULT_DENSE_MODEL_PATH), help="dense .enc model path")
    parser.add_argument("--timeout", default=DEFAULT_TIMEOUT_S, type=float, help="timeout seconds")
    args = parser.parse_args()

    print("TouchGlove Rust dense CUDA 自检")
    ok, detail = run_rust_dense_preflight(args.model, timeout_s=args.timeout)
    if ok:
        print(f"[PASS] {detail}")
        return 0
    print(f"[FAIL] {detail}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
