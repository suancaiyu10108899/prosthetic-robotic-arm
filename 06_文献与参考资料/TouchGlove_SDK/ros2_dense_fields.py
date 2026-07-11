#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROS2 publisher for TouchGlove dense displacement and force fields.

Publishes:
    disp  std_msgs/Float32MultiArray  shape=(5, 32, 32, 3)
    force std_msgs/Float32MultiArray  shape=(5, 32, 32, 3)
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import numpy as np

_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray, MultiArrayDimension

from dense_preflight import run_rust_dense_preflight
from touch_glove.sdk import TouchGlove, list_ports, TS_IMAGE_CHANNELS


DEFAULT_DENSE_MODEL_PATH = os.path.join(_script_dir, "models", "dense_3ch.enc")
DEFAULT_HEIGHT = 32
DEFAULT_WIDTH = 32
VECTOR_SIZE = 3
NORMAL_DISP_ZERO_THRESHOLD_MM = 0.3


def auto_select_port() -> str:
    ports = list_ports()
    acm_ports = sorted([p for p in ports if "ttyACM" in p])
    preferred = acm_ports or ports
    return preferred[0] if preferred else "/dev/ttyACM0"


def apply_dense_protection(
    disp_frame,
    force_frame,
    normal_disp_zero_threshold_mm=NORMAL_DISP_ZERO_THRESHOLD_MM,
    clip_force_z=True,
):
    disp = np.asarray(disp_frame, dtype=np.float32).copy()
    force = np.asarray(force_frame, dtype=np.float32).copy()

    if clip_force_z and force.shape[-1] >= 3:
        force[..., 2] = np.clip(force[..., 2], 0.0, None)

    cutoff = float(normal_disp_zero_threshold_mm)
    if disp.ndim == 4:
        for ch in range(disp.shape[0]):
            normal_max = float(np.max(np.abs(disp[ch, :, :, 2])))
            if normal_max < cutoff:
                disp[ch] = 0.0
                force[ch] = 0.0
    elif disp.ndim == 3:
        normal_max = float(np.max(np.abs(disp[:, :, 2])))
        if normal_max < cutoff:
            disp[...] = 0.0
            force[...] = 0.0

    return disp, force


def make_dense_msg(arr):
    arr = np.asarray(arr, dtype=np.float32)
    if arr.ndim != 4 or arr.shape[-1] != VECTOR_SIZE:
        raise ValueError(f"Expected dense field shape (C, H, W, 3), got {arr.shape}")

    channels, height, width, vector = arr.shape
    msg = Float32MultiArray()
    msg.layout.dim = [
        MultiArrayDimension(label="channel", size=channels, stride=height * width * vector),
        MultiArrayDimension(label="height", size=height, stride=width * vector),
        MultiArrayDimension(label="width", size=width, stride=vector),
        MultiArrayDimension(label="xyz", size=vector, stride=1),
    ]
    msg.layout.data_offset = 0
    msg.data = arr.reshape(-1).tolist()
    return msg


class TouchGloveDenseFieldsNode(Node):
    def __init__(self) -> None:
        super().__init__("touch_glove_dense_fields_node")

        self.declare_parameter("port", "")
        self.declare_parameter("disp_topic", "disp")
        self.declare_parameter("force_topic", "force")
        self.declare_parameter("pub_interval_s", 0.02)
        self.declare_parameter("auto_calibrate", True)
        self.declare_parameter("settle_seconds", 1.0)
        self.declare_parameter("dense_model", DEFAULT_DENSE_MODEL_PATH)
        self.declare_parameter("normal_disp_zero_threshold_mm", NORMAL_DISP_ZERO_THRESHOLD_MM)
        self.declare_parameter("clip_force_z", True)
        self.declare_parameter("open_retry_count", 4)
        self.declare_parameter("open_retry_interval_s", 0.3)
        self.declare_parameter("post_close_wait_s", 0.4)

        port = self.get_parameter("port").get_parameter_value().string_value
        disp_topic = self.get_parameter("disp_topic").get_parameter_value().string_value
        force_topic = self.get_parameter("force_topic").get_parameter_value().string_value
        self.pub_interval = self.get_parameter("pub_interval_s").get_parameter_value().double_value
        self.auto_calibrate = self.get_parameter("auto_calibrate").get_parameter_value().bool_value
        self.settle_seconds = self.get_parameter("settle_seconds").get_parameter_value().double_value
        self.dense_model = self.get_parameter("dense_model").get_parameter_value().string_value
        self.normal_disp_zero_threshold_mm = (
            self.get_parameter("normal_disp_zero_threshold_mm").get_parameter_value().double_value
        )
        self.clip_force_z = self.get_parameter("clip_force_z").get_parameter_value().bool_value
        self.open_retry_count = self.get_parameter("open_retry_count").get_parameter_value().integer_value
        self.open_retry_interval_s = (
            self.get_parameter("open_retry_interval_s").get_parameter_value().double_value
        )
        self.post_close_wait_s = self.get_parameter("post_close_wait_s").get_parameter_value().double_value

        if not port:
            port = auto_select_port()
            self.get_logger().info(f"Auto-detected port: {port}")

        self.latest_disp = np.zeros(
            (TS_IMAGE_CHANNELS, DEFAULT_HEIGHT, DEFAULT_WIDTH, VECTOR_SIZE), dtype=np.float32
        )
        self.latest_force = np.zeros_like(self.latest_disp)
        self.latest_seq_ids = [-1] * TS_IMAGE_CHANNELS

        dense_model_path = Path(self.dense_model).expanduser()
        if not dense_model_path.is_absolute():
            dense_model_path = Path(_script_dir) / dense_model_path
        dense_model = str(dense_model_path)
        self.get_logger().info(f"Loading dense model in Rust: {dense_model}")
        self.get_logger().info("Checking Rust dense CUDA initialization")
        ok, detail = run_rust_dense_preflight(dense_model, timeout_s=60.0)
        if not ok:
            raise RuntimeError(detail)
        self.get_logger().info(detail)

        self.glove = TouchGlove(port, auto_init=False, dense_model=dense_model, enable_inference=True)
        try:
            if not self._open_with_retry(port):
                raise RuntimeError(f"Failed to open glove on {port}")

            self.glove.start()
            self.get_logger().info("Glove streaming started")

            if self.auto_calibrate:
                self.get_logger().info(f"Settling for {self.settle_seconds:.1f}s before calibrate")
                self._spin_poll_for(self.settle_seconds)
                self.glove.calibrate()
                self.latest_disp.fill(0.0)
                self.latest_force.fill(0.0)
                self.get_logger().info("Calibration completed")
        except BaseException:
            self._safe_stop_close()
            raise

        self.disp_pub = self.create_publisher(Float32MultiArray, disp_topic, 10)
        self.force_pub = self.create_publisher(Float32MultiArray, force_topic, 10)
        self.create_timer(self.pub_interval, self._timer_cb)
        self.get_logger().info(
            f"Publishing dense fields on '{disp_topic}' and '{force_topic}' every "
            f"{self.pub_interval:.3f}s"
        )

    def _open_with_retry(self, port: str) -> bool:
        attempts = max(int(self.open_retry_count), 1)
        for i in range(attempts):
            self.get_logger().info(f"Opening port attempt {i + 1}/{attempts}: {port}")
            try:
                if self.glove.open(port):
                    return True
            except Exception as exc:
                self.get_logger().warn(f"Open attempt {i + 1}/{attempts} failed: {exc}")

            self._safe_stop_close()
            if i + 1 < attempts:
                time.sleep(max(float(self.open_retry_interval_s), 0.0))
        return False

    def _spin_poll_for(self, seconds: float) -> None:
        end_t = self.get_clock().now().nanoseconds + int(max(float(seconds), 0.0) * 1e9)
        while self.get_clock().now().nanoseconds < end_t:
            self._poll_once()
            rclpy.spin_once(self, timeout_sec=0.001)

    def _poll_once(self) -> None:
        batch = self.glove.poll()
        for frame in batch:
            ch = int(frame.channel)
            if ch < 0 or ch >= TS_IMAGE_CHANNELS:
                continue
            if frame.disp is None or frame.force_field is None:
                continue

            disp_ch, force_ch = apply_dense_protection(
                frame.disp,
                frame.force_field,
                normal_disp_zero_threshold_mm=self.normal_disp_zero_threshold_mm,
                clip_force_z=self.clip_force_z,
            )
            self.latest_disp[ch] = disp_ch
            self.latest_force[ch] = force_ch
            self.latest_seq_ids[ch] = int(getattr(frame, "seq_id", 0))

        self.latest_disp, self.latest_force = apply_dense_protection(
            self.latest_disp,
            self.latest_force,
            normal_disp_zero_threshold_mm=self.normal_disp_zero_threshold_mm,
            clip_force_z=self.clip_force_z,
        )

    def _timer_cb(self) -> None:
        self._poll_once()
        self.disp_pub.publish(make_dense_msg(self.latest_disp))
        self.force_pub.publish(make_dense_msg(self.latest_force))

    def destroy_node(self) -> bool:
        self._safe_stop_close()
        return super().destroy_node()

    def _safe_stop_close(self) -> None:
        try:
            self.glove.stop()
        except Exception:
            pass
        try:
            self.glove.close()
        except Exception:
            pass
        time.sleep(max(float(self.post_close_wait_s), 0.0))


def main(args=None) -> None:
    rclpy.init(args=args)
    node = None
    try:
        node = TouchGloveDenseFieldsNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except ModuleNotFoundError as exc:
        if exc.name in ("rclpy", "std_msgs"):
            print("错误: 缺少 ROS2 Python 环境。请先执行: source /opt/ros/humble/setup.bash")
            return
        raise
    except Exception as exc:
        print(f"Error: {exc}")
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
