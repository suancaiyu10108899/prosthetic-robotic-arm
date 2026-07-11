#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dense SDK CUDA environment check.

This script verifies that ONNX Runtime can load the dense model with
CUDAExecutionProvider and execute one dummy inference on GPU.
"""

from __future__ import annotations

import argparse
import os
import sys
import warnings
from pathlib import Path

import numpy as np

_script_dir = Path(__file__).resolve().parent
DEFAULT_DENSE_MODEL_PATH = _script_dir / "models" / "dense_3ch.enc"
EXPECTED_ORT_VERSION = "1.23.2"

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-touch-glove")
os.environ.setdefault("ORT_LOG_SEVERITY_LEVEL", "3")

from dense_preflight import run_rust_dense_preflight


def derive_model_key():
    part_a = bytes([
        0x4f, 0x1c, 0x8a, 0x33, 0xb7, 0x52, 0xe9, 0x0d, 0x6a, 0xf3, 0x21, 0x95, 0xc4, 0x78, 0x3e,
        0x16, 0x80, 0xd2, 0x5b, 0x47, 0x13, 0xa8, 0xfe, 0x69, 0x2c, 0x94, 0xb1, 0x07, 0xe5, 0x3a,
        0xdc, 0x6f,
    ])
    part_b = bytes([
        0x3b, 0x73, 0xff, 0x50, 0xdf, 0x0d, 0x8e, 0x61, 0x05, 0x85, 0x44, 0xca, 0xb7, 0x1c, 0x55,
        0x49, 0xed, 0xbd, 0x3f, 0x22, 0x7f, 0xf7, 0x8d, 0x0c, 0x4f, 0xe6, 0xd4, 0x73, 0xba, 0x51,
        0xb9, 0x16,
    ])
    return bytes(a ^ b for a, b in zip(part_a, part_b))


def load_model_for_ort(path):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    model_path = Path(path).expanduser()
    if not model_path.is_absolute():
        model_path = _script_dir / model_path
    data = model_path.read_bytes()
    if str(model_path).lower().endswith(".enc"):
        if len(data) < 12:
            raise ValueError("加密模型文件无效。")
        return AESGCM(derive_model_key()).decrypt(data[:12], data[12:], None)
    return str(model_path)


def concrete_input_shape(shape):
    defaults = [5, 3, 192, 192]
    out = []
    for i, dim in enumerate(shape):
        if isinstance(dim, int) and dim > 0:
            out.append(dim)
        else:
            out.append(defaults[i] if i < len(defaults) else 1)
    return out


def quiet_session_options(ort):
    options = ort.SessionOptions()
    options.log_severity_level = 3
    return options


def main() -> int:
    parser = argparse.ArgumentParser(description="Check TouchGlove Dense SDK CUDA environment.")
    parser.add_argument("--model", default=str(DEFAULT_DENSE_MODEL_PATH), help="dense .enc/.onnx model path")
    parser.add_argument("--skip-inference", action="store_true", help="Only check provider availability/session load")
    parser.add_argument("--skip-rust", action="store_true", help="Skip Rust SDK CUDA initialization check")
    parser.add_argument("--rust-timeout", default=60.0, type=float, help="Rust SDK preflight timeout seconds")
    parser.add_argument("--verbose", action="store_true", help="Print detailed environment information")
    args = parser.parse_args()

    print("TouchGlove Dense CUDA 环境检测")

    try:
        import touch_glove_rust  # noqa: F401
    except Exception as exc:
        print("[FAIL] SDK runtime: touch_glove_rust 导入失败")
        print("       请确认当前环境为 Python 3.10，并且 dist_dense/touch_glove_rust/_rust*.so 存在。")
        if args.verbose:
            print(f"       详细错误: {exc}")
        return 1
    print("[ OK ] SDK runtime: 已加载随包 ONNX Runtime 并预加载 CUDA/cuDNN 运行库")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import onnxruntime as ort
    except Exception as exc:
        print("[FAIL] Python 依赖: 缺少 onnxruntime")
        print("       建议安装: pip install onnxruntime-gpu")
        if args.verbose:
            print(f"       详细错误: {exc}")
        return 1

    print("[ OK ] Python 依赖: onnxruntime 已安装")
    if getattr(ort, "__version__", "") != EXPECTED_ORT_VERSION:
        print(
            f"[WARN] onnxruntime 版本: 当前 {getattr(ort, '__version__', 'unknown')}，"
            f"SDK 固定验证版本为 {EXPECTED_ORT_VERSION}"
        )
        print("       建议安装: pip install onnxruntime-gpu==1.23.2")
    else:
        print(f"[ OK ] onnxruntime 版本: {EXPECTED_ORT_VERSION}")
    if args.verbose:
        print(f"       Python: {sys.executable}")
        print(f"       onnxruntime: {ort.__version__}")
        print(f"       providers: {ort.get_available_providers()}")

    if "CUDAExecutionProvider" not in ort.get_available_providers():
        print("[FAIL] CUDA Provider: 缺少 CUDAExecutionProvider")
        print("       常见原因: 安装了 CPU 版 onnxruntime，或 CUDA/cuDNN 动态库不可见。")
        print("       建议确认: pip install onnxruntime-gpu，并检查 NVIDIA 驱动、CUDA/cuDNN。")
        return 1
    print("[ OK ] CUDA Provider: CUDAExecutionProvider 可用")

    try:
        session = ort.InferenceSession(
            load_model_for_ort(args.model),
            providers=["CUDAExecutionProvider"],
            sess_options=quiet_session_options(ort),
        )
    except Exception as exc:
        print("[FAIL] Dense 模型: 无法用 CUDA 加载")
        print("       请确认模型文件存在、未损坏，并且 CUDA/cuDNN 版本与 onnxruntime-gpu 匹配。")
        print("       若错误包含 libcublasLt.so.12，请安装: pip install \"nvidia-cublas-cu12>=12,<13\"")
        if args.verbose:
            print(f"       详细错误: {exc}")
        return 1

    active = session.get_providers()
    if "CUDAExecutionProvider" not in active:
        print("[FAIL] CUDA Session: 未启用 CUDAExecutionProvider")
        print("       若上方日志包含 libcublasLt.so.12，请安装: pip install \"nvidia-cublas-cu12>=12,<13\"")
        if args.verbose:
            print(f"       active providers: {active}")
        return 1
    print("[ OK ] Dense 模型: CUDA session 加载成功")

    if args.skip_inference:
        if not args.skip_rust:
            print("Rust SDK CUDA 初始化检测")
            ok, detail = run_rust_dense_preflight(args.model, timeout_s=args.rust_timeout)
            if not ok:
                print(f"[FAIL] {detail}")
                return 1
            print(f"[ OK ] {detail}")
        print("[PASS] 环境检测通过")
        return 0

    input_meta = session.get_inputs()[0]
    input_shape = concrete_input_shape(input_meta.shape)
    dtype = np.float16 if input_meta.type == "tensor(float16)" else np.float32
    dummy = np.zeros(input_shape, dtype=dtype)
    output_names = [o.name for o in session.get_outputs()]

    try:
        outputs = session.run(output_names, {input_meta.name: dummy})
    except Exception as exc:
        print("[FAIL] CUDA 推理: 执行失败")
        print("       请确认 GPU 显存充足，并检查 CUDA/cuDNN 与 onnxruntime-gpu 的兼容性。")
        if args.verbose:
            print(f"       详细错误: {exc}")
        return 1

    if args.verbose:
        print(f"       active providers: {active}")
        print(f"       input: {input_meta.name} shape={input_shape} dtype={dummy.dtype}")
        for name, value in zip(output_names, outputs):
            print(f"       output: {name} shape={np.asarray(value).shape} dtype={np.asarray(value).dtype}")

    print("[ OK ] CUDA 推理: dense 模型推理成功")
    if not args.skip_rust:
        print("Rust SDK CUDA 初始化检测")
        ok, detail = run_rust_dense_preflight(args.model, timeout_s=args.rust_timeout)
        if not ok:
            print(f"[FAIL] {detail}")
            return 1
        print(f"[ OK ] {detail}")
    print("[PASS] 环境检测通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
