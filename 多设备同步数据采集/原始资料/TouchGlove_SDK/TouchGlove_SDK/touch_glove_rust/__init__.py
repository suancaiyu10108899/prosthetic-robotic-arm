"""
touch_glove_rust — Touch Glove SDK (Rust 实现)

高性能触觉手套数据采集 SDK，Rust 核心 + PyO3 绑定。

使用方法:
    from touch_glove_rust import TouchGlove, list_ports

    ports = list_ports()
    with TouchGlove(ports[0]) as glove:
        for batch in glove.stream(timeout=10.0):
            for frame in batch:
                print(f"ch={frame.channel} seq={frame.seq_id}")
"""
import os
import sys
import glob

import ctypes

_this_dir = os.path.dirname(os.path.abspath(__file__))


def _try_load(path: str) -> bool:
    try:
        ctypes.CDLL(path, mode=ctypes.RTLD_GLOBAL)
        return True
    except Exception:
        return False


def _configure_ort_dylib_path():
    for libname in ["libonnxruntime.so.1.23.2", "libonnxruntime.so"]:
        candidate = os.path.join(_this_dir, libname)
        if os.path.exists(candidate):
            os.environ["ORT_DYLIB_PATH"] = candidate
            return


def _preload_cuda_libs():
    cuda_roots = [
        "/usr/local/cuda/lib64",
        "/usr/local/cuda/targets/x86_64-linux/lib",
    ]
    cuda_roots.extend(glob.glob("/usr/local/cuda-*/lib64"))
    cuda_roots.extend(glob.glob("/usr/local/cuda-*/targets/x86_64-linux/lib"))

    roots = []

    def add_site_packages_nvidia_libs(site_packages: str):
        roots.extend(glob.glob(os.path.join(site_packages, "nvidia", "*", "lib")))

    for base in [sys.prefix, sys.base_prefix, os.path.expanduser("~/.local")]:
        for site_packages in glob.glob(os.path.join(base, "lib", "python*", "site-packages")):
            add_site_packages_nvidia_libs(site_packages)
        roots.append(os.path.join(base, "lib"))
    for p in sys.path:
        if p.endswith("site-packages"):
            add_site_packages_nvidia_libs(p)
    for p in os.environ.get("LD_LIBRARY_PATH", "").split(os.pathsep):
        if p:
            roots.append(p)

    roots = sorted(set(cuda_roots + roots))
    cuda_patterns = [
        "libnvJitLink.so.12",
        "libcudart.so.12",
        "libcublasLt.so.12",
        "libcublas.so.12",
        "libnvrtc.so.12",
        "libnvrtc-builtins.so.*",
        "libcurand.so.10",
        "libcufft.so.11",
    ]
    cudnn_patterns = [
        "libcudnn.so.9",
        "libcudnn_graph.so.9",
        "libcudnn_ops.so.9",
        "libcudnn_heuristic.so.9",
        "libcudnn_adv.so.9",
        "libcudnn_cnn.so.9",
        "libcudnn_engines_precompiled.so.9",
        "libcudnn_engines_runtime_compiled.so.9",
    ]
    for pattern in cuda_patterns + cudnn_patterns:
        loaded = False
        for root in roots:
            for path in sorted(glob.glob(os.path.join(root, pattern))):
                if _try_load(path):
                    loaded = True
                    break
            if loaded:
                break


# Pre-load local ONNX Runtime and provider shared libraries to process scope using
# RTLD_GLOBAL so that the Rust extension can resolve CUDA provider libraries.
_configure_ort_dylib_path()
_preload_cuda_libs()
for libname in [
    "libonnxruntime.so.1.23.2",
    "libonnxruntime.so",
    "libonnxruntime_providers_shared.so",
]:
    candidate = os.path.join(_this_dir, libname)
    if os.path.exists(candidate):
        _try_load(candidate)

try:
    from ._rust import (  # type: ignore[import]
        TouchGlove,
        Frame,
        FrameBatch,
        list_ports,
        IMAGE_WIDTH,
        IMAGE_HEIGHT,
        IMAGE_CHANNELS,
        IMAGE_BYTES,
    )
except ImportError as e:
    platform_info = f"Python {sys.version_info.major}.{sys.version_info.minor} on {sys.platform}"
    raise ImportError(
        "touch_glove_rust 原生扩展未找到或加载失败。\n"
        f"当前环境: {platform_info}\n"
        "请确认已编译安装适用于当前系统的原生二进制包 (Windows 下为 .pyd, Linux 下为 .so)。\n"
        "你可以通过在项目根目录下运行 `maturin develop --release` 来为当前环境重新编译并安装扩展。\n"
        f"原始错误: {e}"
    ) from e

__all__ = [
    "TouchGlove",
    "Frame",
    "FrameBatch",
    "list_ports",
    "IMAGE_WIDTH",
    "IMAGE_HEIGHT",
    "IMAGE_CHANNELS",
    "IMAGE_BYTES",
]

__version__ = "1.0.0"
