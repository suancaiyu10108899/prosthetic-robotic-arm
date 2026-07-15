#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROS2 publisher for Touch Glove force/position state (Rust SDK backend).

This module is intentionally packaged inside the wheel to reduce logic exposure
in customer-facing script wrappers.
"""

from __future__ import annotations

import math
import sys
import time
from typing import Dict, List

import rclpy
from rclpy.node import Node
from touch_glove_msgs.msg import FingerData, GloveState

from touch_glove.sdk import TouchGlove, list_ports, TS_IMAGE_CHANNELS


class TouchGloveForcePosNode(Node):
    def __init__(self) -> None:
        super().__init__("touch_glove_force_pos_node")

        self.declare_parameter("port", "")
        self.declare_parameter("topic", "state")
        self.declare_parameter("pub_interval_s", 0.02)
        self.declare_parameter("auto_calibrate", True)
        self.declare_parameter("settle_seconds", 2.0)
        self.declare_parameter("no_touch_force_threshold", 0.5)
        self.declare_parameter("tare_window_s", 1.0)
        self.declare_parameter("open_retry_count", 4)
        self.declare_parameter("open_retry_interval_s", 0.3)
        self.declare_parameter("post_close_wait_s", 0.4)

        port = self.get_parameter("port").get_parameter_value().string_value
        topic = self.get_parameter("topic").get_parameter_value().string_value
        self.pub_interval = self.get_parameter("pub_interval_s").get_parameter_value().double_value
        self.auto_calibrate = self.get_parameter("auto_calibrate").get_parameter_value().bool_value
        self.settle_seconds = self.get_parameter("settle_seconds").get_parameter_value().double_value
        self.no_touch_force_threshold = (
            self.get_parameter("no_touch_force_threshold").get_parameter_value().double_value
        )
        self.tare_window_s = self.get_parameter("tare_window_s").get_parameter_value().double_value
        self.open_retry_count = (
            self.get_parameter("open_retry_count").get_parameter_value().integer_value
        )
        self.open_retry_interval_s = (
            self.get_parameter("open_retry_interval_s").get_parameter_value().double_value
        )
        self.post_close_wait_s = (
            self.get_parameter("post_close_wait_s").get_parameter_value().double_value
        )

        if not port:
            ports = list_ports()
            acm_ports = [p for p in ports if "ttyACM" in p]
            preferred = acm_ports or ports
            if not preferred:
                raise RuntimeError("No serial ports found")
            port = preferred[0]
            self.get_logger().info(f"Auto-detected port: {port}")

        self.glove = TouchGlove(port, auto_init=False)
        try:
            if not self._open_with_retry(port):
                raise RuntimeError(f"Failed to open glove on {port}")

            self.glove.start()
            self.get_logger().info("Glove streaming started")

            if self.auto_calibrate:
                self.get_logger().info(f"Settling for {self.settle_seconds:.1f}s before calibrate")
                self._spin_poll_for(self.settle_seconds, write_latest=False)
                self.glove.calibrate()
                self.get_logger().info("Calibration completed")

            self.tare_offsets: Dict[int, Dict[str, float]] = {
                ch: {"fx": 0.0, "fy": 0.0, "fz": 0.0} for ch in range(TS_IMAGE_CHANNELS)
            }
            self._force_tare()
        except BaseException:
            self._safe_stop_close()
            raise

        self.pub = self.create_publisher(GloveState, topic, 10)
        self.latest: Dict[int, Dict[str, float]] = {
            ch: {"fx": 0.0, "fy": 0.0, "fz": 0.0, "x": 0.0, "y": 0.0}
            for ch in range(TS_IMAGE_CHANNELS)
        }
        self.create_timer(self.pub_interval, self._timer_cb)
        self.get_logger().info(f"Publishing GloveState on '{topic}' every {self.pub_interval:.3f}s")

    def _spin_poll_for(self, seconds: float, write_latest: bool) -> None:
        end_t = self.get_clock().now().nanoseconds + int(seconds * 1e9)
        while self.get_clock().now().nanoseconds < end_t:
            self._poll_once(write_latest=write_latest)
            rclpy.spin_once(self, timeout_sec=0.001)

    def _open_with_retry(self, port: str) -> bool:
        attempts = max(int(self.open_retry_count), 1)
        for i in range(attempts):
            self.get_logger().info(f"Opening port attempt {i + 1}/{attempts}: {port}")
            try:
                if self.glove.open(port):
                    if i > 0:
                        self.get_logger().info(f"Port open succeeded on retry {i + 1}/{attempts}")
                    return True
            except Exception as exc:
                self.get_logger().warn(f"Open attempt {i + 1}/{attempts} failed: {exc}")

            self.get_logger().warn(
                f"Open attempt {i + 1}/{attempts} not ready, retrying after "
                f"{self.open_retry_interval_s:.2f}s"
            )
            self._safe_stop_close()
            if i + 1 < attempts:
                time.sleep(max(float(self.open_retry_interval_s), 0.0))
        return False

    def _force_tare(self) -> None:
        self.get_logger().info(
            f"提示: 使用{self.tare_window_s:.1f}s内的平均力进行去皮，然后再启动稳定发布。"
        )
        sums = {ch: [0.0, 0.0, 0.0] for ch in range(TS_IMAGE_CHANNELS)}
        cnts = {ch: 0 for ch in range(TS_IMAGE_CHANNELS)}

        end_t = self.get_clock().now().nanoseconds + int(self.tare_window_s * 1e9)
        while self.get_clock().now().nanoseconds < end_t:
            batch = self.glove.poll()
            for frame in batch:
                ch = int(frame.channel)
                if ch < 0 or ch >= TS_IMAGE_CHANNELS:
                    continue
                sums[ch][0] += float(frame.fx)
                sums[ch][1] += float(frame.fy)
                sums[ch][2] += float(frame.fz)
                cnts[ch] += 1
            rclpy.spin_once(self, timeout_sec=0.001)

        for ch in range(TS_IMAGE_CHANNELS):
            n = max(cnts[ch], 1)
            self.tare_offsets[ch] = {
                "fx": sums[ch][0] / n,
                "fy": sums[ch][1] / n,
                "fz": sums[ch][2] / n,
            }

    def _poll_once(self, write_latest: bool) -> None:
        batch = self.glove.poll()
        if not write_latest:
            return
        for frame in batch:
            ch = int(frame.channel)
            if ch < 0 or ch >= TS_IMAGE_CHANNELS:
                continue
            fx = float(frame.fx) - self.tare_offsets[ch]["fx"]
            fy = float(frame.fy) - self.tare_offsets[ch]["fy"]
            fz = float(frame.fz) - self.tare_offsets[ch]["fz"]
            x = float(frame.x)
            y = float(frame.y)

            force_mag = math.sqrt(fx * fx + fy * fy + fz * fz)
            if force_mag < self.no_touch_force_threshold:
                x, y = 0.0, 0.0

            self.latest[ch] = {"fx": fx, "fy": fy, "fz": fz, "x": x, "y": y}

    def _timer_cb(self) -> None:
        self._poll_once(write_latest=True)

        msg = GloveState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "touch_glove"

        finger_attrs: List[str] = ["ch1", "ch2", "ch3", "ch4", "ch5"]
        for idx, attr in enumerate(finger_attrs):
            f = FingerData()
            d = self.latest.get(idx, {"fx": 0.0, "fy": 0.0, "fz": 0.0, "x": 0.0, "y": 0.0})
            f.fx = d["fx"]
            f.fy = d["fy"]
            f.fz = d["fz"]
            f.x = d["x"]
            f.y = d["y"]
            setattr(msg, attr, f)

        self.pub.publish(msg)

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
        node = TouchGloveForcePosNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        print(f"Error: {exc}")
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
