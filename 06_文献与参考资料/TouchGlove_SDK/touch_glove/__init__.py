# touch_glove package shim — 重定向到 Rust 实现
from touch_glove_rust.compat import TouchGlove, list_ports, TS_IMAGE_CHANNELS, IMAGE_WIDTH, IMAGE_HEIGHT

__all__ = ["TouchGlove", "list_ports", "TS_IMAGE_CHANNELS", "IMAGE_WIDTH", "IMAGE_HEIGHT"]
