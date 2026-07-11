#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dense_dashboard.py
================================================================================
TouchGlove dense field dashboard.

Open the full dashboard:
    python dense_dashboard.py

Offline shortcut:
    python dense_dashboard.py --force_npy npy/force_xxxx.npy --disp_npy npy/disp_xxxx.npy

Realtime shortcut:
    python dense_dashboard.py --realtime
================================================================================
"""

import argparse
import datetime
import os
import sys
import threading
import time
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-touch-glove")
for _qt_var in ("QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH"):
    _qt_path = os.environ.get(_qt_var, "")
    if "cv2/qt/plugins" in _qt_path:
        os.environ.pop(_qt_var, None)

import numpy as np
import matplotlib

matplotlib.rcParams["font.sans-serif"] = ["DejaVu Sans", "Noto Sans CJK JP", "Droid Sans Fallback"]
matplotlib.rcParams["axes.unicode_minus"] = False

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from PySide6 import QtCore, QtGui, QtWidgets

_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

try:
    from touch_glove.sdk import TouchGlove, list_ports
    SDK_IMPORT_ERROR = None
except Exception as exc:
    TouchGlove = None
    list_ports = None
    SDK_IMPORT_ERROR = exc

from dense_preflight import run_rust_dense_preflight

DEFAULT_DENSE_MODEL_PATH = os.path.join(_script_dir, "models", "dense_3ch.enc")
NORMAL_DISP_ZERO_THRESHOLD_MM = 0.3
CJK_FONT = FontProperties(fname="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")


def auto_select_port():
    if list_ports is None:
        return "/dev/ttyACM0"
    ports = list_ports()
    acm_ports = sorted([p for p in ports if "ttyACM" in p])
    preferred = acm_ports or ports
    return preferred[0] if preferred else "/dev/ttyACM0"


def normalize_dense_array(arr):
    arr = np.asarray(arr, dtype=np.float32)
    if arr.ndim == 4:
        arr = arr[:, None, :, :, :]
    if arr.ndim != 5 or arr.shape[-1] != 3:
        raise ValueError(f"Expected dense data shape (T, C, H, W, 3), got {arr.shape}")
    if arr.shape[1] == 1:
        pad = np.zeros((arr.shape[0], 4, arr.shape[2], arr.shape[3], 3), dtype=arr.dtype)
        arr = np.concatenate([arr, pad], axis=1)
    return arr[:, :5]


def dense_metrics(disp_frame, force_frame):
    disp_mag = np.linalg.norm(disp_frame, axis=-1)
    force_mag = np.linalg.norm(force_frame, axis=-1)
    force_sum = np.sum(force_frame, axis=(0, 1))
    return {
        "disp_max": float(np.max(np.abs(disp_frame))),
        "disp_mean": float(np.mean(disp_mag)),
        "force_max": float(np.max(np.abs(force_frame))),
        "force_mean": float(np.mean(force_mag)),
        "force_sum_x": float(force_sum[0]),
        "force_sum_y": float(force_sum[1]),
        "force_sum_z": float(force_sum[2]),
    }


def apply_zero_threshold(disp_frame, force_frame, threshold=NORMAL_DISP_ZERO_THRESHOLD_MM):
    disp = np.asarray(disp_frame, dtype=np.float32).copy()
    force = np.asarray(force_frame, dtype=np.float32).copy()
    cutoff = float(threshold)
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


class MetricCard(QtWidgets.QFrame):
    def __init__(self, title, value="0.000", unit="", accent="#1f8a70"):
        super().__init__()
        self.setObjectName("metricCard")
        self.setMinimumHeight(92)
        self.title = QtWidgets.QLabel(title)
        self.title.setObjectName("metricTitle")
        self.value = QtWidgets.QLabel(value)
        self.value.setObjectName("metricValue")
        self.unit = QtWidgets.QLabel(unit)
        self.unit.setObjectName("metricUnit")

        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.value)
        row.addWidget(self.unit)
        row.addStretch()

        accent_bar = QtWidgets.QFrame()
        accent_bar.setFixedWidth(4)
        accent_bar.setStyleSheet(f"background:{accent}; border-radius:2px;")

        content = QtWidgets.QVBoxLayout()
        content.setContentsMargins(14, 12, 14, 12)
        content.setSpacing(6)
        content.addWidget(self.title)
        content.addLayout(row)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(accent_bar)
        layout.addLayout(content)

    def set_value(self, value):
        self.value.setText(value)


class FieldCanvas(FigureCanvas):
    def __init__(self, title, cmap):
        self.fig = Figure(figsize=(5, 4), dpi=100, facecolor="#ffffff")
        super().__init__(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title(title, fontsize=11, color="#17202a", pad=10, fontproperties=CJK_FONT)
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.ax.set_facecolor("#f6f8fb")
        for spine in self.ax.spines.values():
            spine.set_visible(False)
        self.image = self.ax.imshow(np.zeros((32, 32), dtype=np.float32), cmap=cmap, vmin=0.0, vmax=1.0)
        self.quiver = None
        self.fig.tight_layout(pad=1.2)

    def set_title(self, title):
        if self.ax.get_title() == title:
            return
        self.ax.set_title(title, fontsize=11, color="#17202a", pad=10, fontproperties=CJK_FONT)

    def _clear_quiver(self):
        if self.quiver is not None:
            self.quiver.remove()
            self.quiver = None

    def _set_image_data(self, data, vmax=None):
        data = np.asarray(data, dtype=np.float32)
        vmax = float(vmax if vmax is not None else max(np.max(data), 1e-6))
        h, w = data.shape
        self.image.set_data(data)
        self.image.set_extent((-0.5, w - 0.5, h - 0.5, -0.5))
        self.ax.set_xlim(-0.5, w - 0.5)
        self.ax.set_ylim(h - 0.5, -0.5)
        self.image.set_clim(0.0, max(vmax, 1e-6))

    def update_heatmap(self, data, vmax=None):
        self._clear_quiver()
        self._set_image_data(data, vmax)
        self.draw_idle()

    def update_force(self, force_frame):
        force_frame = np.asarray(force_frame, dtype=np.float32)
        magnitude = np.linalg.norm(force_frame, axis=-1)
        self._clear_quiver()
        self._set_image_data(magnitude)
        self.draw_idle()

    def update_tangential(self, vector_frame):
        vector_frame = np.asarray(vector_frame, dtype=np.float32)
        tangent = vector_frame[:, :, :2]
        magnitude = np.linalg.norm(tangent, axis=-1)
        self._clear_quiver()
        self._set_image_data(magnitude)

        h, w = magnitude.shape
        yy, xx = np.mgrid[0:h, 0:w]
        direction = np.zeros_like(tangent)
        np.divide(
            tangent,
            magnitude[:, :, None],
            out=direction,
            where=magnitude[:, :, None] > 1e-6,
        )
        self.quiver = self.ax.quiver(
            xx,
            yy,
            direction[:, :, 0],
            -direction[:, :, 1],
            color="#101820",
            alpha=0.58,
            angles="xy",
            scale_units="xy",
            scale=2.7,
            pivot="middle",
            width=0.0024,
            headwidth=2.8,
            headlength=3.4,
            headaxislength=3.0,
            minlength=0.0,
        )
        self.draw_idle()


class ChannelStrip(QtWidgets.QFrame):
    channel_selected = QtCore.Signal(int)

    def __init__(self):
        super().__init__()
        self.setObjectName("strip")
        self.buttons = []
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        for ch in range(5):
            btn = QtWidgets.QPushButton(f"通道 {ch}")
            btn.setCheckable(True)
            btn.setObjectName("channelButton")
            btn.clicked.connect(lambda checked, c=ch: self.channel_selected.emit(c))
            self.buttons.append(btn)
            layout.addWidget(btn)
        self.buttons[0].setChecked(True)

    def set_channel(self, ch):
        for i, btn in enumerate(self.buttons):
            btn.setChecked(i == ch)

    def update_levels(self, disp_frame, force_frame):
        for ch, btn in enumerate(self.buttons):
            m = dense_metrics(disp_frame[ch], force_frame[ch])
            btn.setText(f"通道 {ch}\n位移 {m['disp_max']:.2f}  力 {m['force_max']:.2f}")


class RealtimeEngine:
    def __init__(self, port, model):
        self.port = port
        self.model = model
        self.uses_sdk_dense = True
        self.lock = threading.Lock()
        self.running = False
        self.thread = None
        self.stop_event = threading.Event()
        self.sensor = None
        self.status = "Idle"
        self.error = ""
        self.latest_disp = np.zeros((5, 32, 32, 3), dtype=np.float32)
        self.latest_force = np.zeros((5, 32, 32, 3), dtype=np.float32)
        self.latest_seq_ids = [-1] * 5
        self.baseline_ready = False
        self.calibrate_event = threading.Event()
        self.poll_count = 0
        self.dense_count = 0
        self.last_seq_ch0 = None
        self.stat_t0 = time.time()
        self.poll_fps = 0.0
        self.dense_fps = 0.0
        self.last_dense_seq_ch0 = None

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.running = True
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        self.stop_event.set()
        self.calibrate_event.set()
        sensor = self.sensor
        if sensor is not None:
            try:
                sensor.stop()
            except Exception:
                pass
            try:
                sensor.close()
            except Exception:
                pass
        if self.thread:
            self.thread.join(timeout=5.0)
            if self.thread.is_alive():
                self._set_status("Error", "实时线程未能及时退出，请拔插手套后重试。")
            else:
                self.thread = None
        self.sensor = None

    def request_calibrate(self):
        self.calibrate_event.set()

    def snapshot(self):
        with self.lock:
            return {
                "disp": self.latest_disp.copy(),
                "force": self.latest_force.copy(),
                "status": self.status,
                "error": self.error,
                "poll_fps": self.poll_fps,
                "dense_fps": self.dense_fps,
                "baseline_ready": self.baseline_ready,
            }

    def _set_status(self, status, error=""):
        with self.lock:
            self.status = status
            self.error = error

    def _load_session(self):
        if not os.path.exists(self.model):
            raise FileNotFoundError(self.model)

    def _ingest_batch(self, batch):
        dense_updated = False
        for frame in batch:
            ch = int(frame.channel)
            if 0 <= ch < 5:
                seq_id = int(getattr(frame, "seq_id", 0))
                self.latest_seq_ids[ch] = seq_id
                if ch == 0:
                    if self.last_seq_ch0 is None:
                        self.poll_count += 1
                    else:
                        delta = (seq_id - self.last_seq_ch0) & 0xFFFFFFFF
                        self.poll_count += max(delta, 1)
                    self.last_seq_ch0 = seq_id
                if self.uses_sdk_dense and frame.disp is not None and frame.force_field is not None:
                    disp_ch, force_ch = apply_zero_threshold(frame.disp, frame.force_field)
                    with self.lock:
                        self.latest_disp[ch] = disp_ch
                        self.latest_force[ch] = force_ch
                    if ch == 0 and seq_id != self.last_dense_seq_ch0:
                        dense_updated = True
                        self.last_dense_seq_ch0 = seq_id
        if dense_updated:
            self.dense_count += 1

    def _calibrate(self):
        self._set_status("Calibrating")
        if self.uses_sdk_dense:
            self.sensor.calibrate()
            with self.lock:
                self.baseline_ready = True
                self.latest_disp.fill(0.0)
                self.latest_force.fill(0.0)
            self._set_status("Streaming")
            return

    def _update_fps(self):
        now = time.time()
        elapsed = now - self.stat_t0
        if elapsed < 1.0:
            return
        with self.lock:
            self.poll_fps = self.poll_count / elapsed
            self.dense_fps = self.dense_count / elapsed
        self.poll_count = 0
        self.dense_count = 0
        self.stat_t0 = now

    def _run(self):
        try:
            self._set_status("Loading model")
            self._load_session()
            self._set_status("Checking CUDA")
            ok, detail = run_rust_dense_preflight(
                self.model,
                timeout_s=60.0,
                cancel_event=self.stop_event,
            )
            if not ok:
                if not self.running or self.stop_event.is_set():
                    return
                raise RuntimeError(detail)
            if TouchGlove is None:
                raise RuntimeError(f"touch_glove SDK is not importable: {SDK_IMPORT_ERROR}")
            self._set_status("Connecting")
            self.sensor = TouchGlove(
                self.port,
                auto_init=False,
                dense_model=self.model,
                enable_inference=True,
            )
            if not self.sensor.open(self.port):
                raise RuntimeError(f"Failed to open port {self.port}")
            self.sensor.start()
            self._set_status("Waiting calibration")
            self.calibrate_event.set()

            while self.running:
                self._ingest_batch(self.sensor.poll())

                if self.calibrate_event.is_set():
                    self.calibrate_event.clear()
                    self._calibrate()

                self._update_fps()
                time.sleep(0.001)
        except Exception as exc:
            self._set_status("Error", str(exc))
        finally:
            if self.sensor is not None:
                try:
                    self.sensor.stop()
                except Exception:
                    pass
                try:
                    self.sensor.close()
                except Exception:
                    pass
                self.sensor = None


class DenseDashboard(QtWidgets.QMainWindow):
    def __init__(self, args):
        super().__init__()
        self.args = args
        self.active_mode = "idle"
        self.current_channel = 0
        self.field_mode = "normal"
        self.frame_idx = 0
        self.playing = False
        self.disp_data = None
        self.force_data = None
        self.num_frames = 0
        self.engine = None
        self.last_save_time = 0.0
        self._shutting_down = False
        self.recording = False
        self.recorded_disp = []
        self.recorded_force = []
        self.last_record_time = 0.0
        self._build_ui()
        self._load_mode()

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(33)

    def _build_ui(self):
        self.setWindowTitle("TouchGlove 触觉控制台")
        self.resize(1480, 880)
        self.setMinimumSize(1280, 760)

        root = QtWidgets.QWidget()
        self.setCentralWidget(root)
        root_layout = QtWidgets.QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        header = QtWidgets.QFrame()
        header.setObjectName("header")
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(24, 16, 24, 16)
        title_box = QtWidgets.QVBoxLayout()
        title = QtWidgets.QLabel("TouchGlove 触觉控制台")
        title.setObjectName("appTitle")
        subtitle = QtWidgets.QLabel("离线回放、实时可视化与数据录制")
        subtitle.setObjectName("appSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        self.mode_badge = QtWidgets.QLabel("待机")
        self.mode_badge.setObjectName("modeBadge")
        self.status_badge = QtWidgets.QLabel("就绪")
        self.status_badge.setObjectName("statusBadge")
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        header_layout.addWidget(self.mode_badge)
        header_layout.addWidget(self.status_badge)

        body = QtWidgets.QHBoxLayout()
        body.setContentsMargins(18, 18, 18, 18)
        body.setSpacing(16)

        sidebar = QtWidgets.QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(390)
        sidebar_layout = QtWidgets.QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 20, 20, 20)
        sidebar_layout.setSpacing(14)

        control_title = QtWidgets.QLabel("控制")
        control_title.setObjectName("sectionTitle")
        sidebar_layout.addWidget(control_title)

        self.open_btn = QtWidgets.QPushButton("打开离线数据")
        self.open_btn.setObjectName("secondaryButton")
        self.open_btn.clicked.connect(self._open_offline_dialog)
        sidebar_layout.addWidget(self.open_btn)

        self.realtime_btn = QtWidgets.QPushButton("连接手套")
        self.realtime_btn.setObjectName("primaryButton")
        self.realtime_btn.clicked.connect(self._toggle_realtime)
        sidebar_layout.addWidget(self.realtime_btn)

        self.record_btn = QtWidgets.QPushButton("开始录制")
        self.record_btn.setObjectName("dangerButton")
        self.record_btn.clicked.connect(self._toggle_recording)
        sidebar_layout.addWidget(self.record_btn)

        self.play_btn = QtWidgets.QPushButton("播放")
        self.play_btn.setObjectName("primaryButton")
        self.play_btn.clicked.connect(self._toggle_play)
        sidebar_layout.addWidget(self.play_btn)

        self.calibrate_btn = QtWidgets.QPushButton("基准校准")
        self.calibrate_btn.setObjectName("secondaryButton")
        self.calibrate_btn.clicked.connect(self._calibrate)
        sidebar_layout.addWidget(self.calibrate_btn)

        self.save_btn = QtWidgets.QPushButton("保存截图")
        self.save_btn.setObjectName("secondaryButton")
        self.save_btn.clicked.connect(self._save_snapshot)
        sidebar_layout.addWidget(self.save_btn)

        self.port_edit = QtWidgets.QLineEdit(self.args.port or auto_select_port())
        sidebar_layout.addWidget(self._labeled("设备端口", self.port_edit))

        self.model_edit = QtWidgets.QLineEdit(self.args.model)
        self.model_edit.setToolTip(self.args.model)
        self.model_edit.setCursorPosition(len(self.args.model))
        sidebar_layout.addWidget(self._labeled("实时模型", self.model_edit))

        self.channel_combo = QtWidgets.QComboBox()
        self.channel_combo.addItems([f"通道 {i}" for i in range(5)])
        self.channel_combo.currentIndexChanged.connect(self._set_channel)
        sidebar_layout.addWidget(self._labeled("当前通道", self.channel_combo))

        self.field_mode_combo = QtWidgets.QComboBox()
        self.field_mode_combo.addItem("法向", "normal")
        self.field_mode_combo.addItem("切向", "tangential")
        self.field_mode_combo.currentIndexChanged.connect(self._set_field_mode)
        sidebar_layout.addWidget(self._labeled("显示模式", self.field_mode_combo))

        self.fps_spin = QtWidgets.QSpinBox()
        self.fps_spin.setRange(1, 60)
        self.fps_spin.setValue(int(self.args.fps))
        sidebar_layout.addWidget(self._labeled("回放帧率", self.fps_spin))

        self.frame_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.frame_slider.valueChanged.connect(self._slider_changed)
        sidebar_layout.addWidget(self._labeled("帧位置", self.frame_slider))

        self.info_label = QtWidgets.QLabel("请选择离线数据，或连接手套。")
        self.info_label.setObjectName("infoText")
        self.info_label.setWordWrap(True)
        sidebar_layout.addWidget(self.info_label)
        sidebar_layout.addStretch()

        self.fps_card = MetricCard("设备 / 推理帧率", "0 / 0", "Hz", "#1f8a70")
        self.frame_card = MetricCard("当前帧", "-", "", "#e76f51")
        sidebar_cards = QtWidgets.QHBoxLayout()
        sidebar_cards.setContentsMargins(0, 0, 0, 0)
        sidebar_cards.setSpacing(10)
        sidebar_cards.addWidget(self.fps_card)
        sidebar_cards.addWidget(self.frame_card)
        sidebar_layout.addLayout(sidebar_cards)

        main_area = QtWidgets.QVBoxLayout()
        main_area.setSpacing(14)

        metric_row = QtWidgets.QHBoxLayout()
        metric_row.setSpacing(12)
        self.cards = {
            "disp_max": MetricCard("最大位移", "0.000", "mm", "#1f8a70"),
            "disp_mean": MetricCard("平均位移", "0.000", "mm", "#2a9d8f"),
            "force_max": MetricCard("最大力", "0.000", "N", "#e76f51"),
            "force_mean": MetricCard("平均力", "0.000", "N", "#264653"),
            "force_sum_x": MetricCard("合力 X", "0.000", "N", "#457b9d"),
            "force_sum_y": MetricCard("合力 Y", "0.000", "N", "#8d5a97"),
            "force_sum_z": MetricCard("合力 Z", "0.000", "N", "#bc6c25"),
        }
        for key in ("disp_max", "disp_mean", "force_max", "force_mean"):
            metric_row.addWidget(self.cards[key])
        main_area.addLayout(metric_row)

        force_sum_row = QtWidgets.QHBoxLayout()
        force_sum_row.setSpacing(12)
        for key in ("force_sum_x", "force_sum_y", "force_sum_z"):
            force_sum_row.addWidget(self.cards[key])
        main_area.addLayout(force_sum_row)

        plots = QtWidgets.QHBoxLayout()
        plots.setSpacing(14)
        self.disp_canvas = FieldCanvas("位移幅值", "viridis")
        self.force_canvas = FieldCanvas("力场分布", "magma")
        plots.addWidget(self._plot_card(self.disp_canvas), 1)
        plots.addWidget(self._plot_card(self.force_canvas), 1)
        main_area.addLayout(plots, 1)

        self.strip = ChannelStrip()
        self.strip.channel_selected.connect(self._set_channel)
        main_area.addWidget(self.strip)

        sidebar_scroll = QtWidgets.QScrollArea()
        sidebar_scroll.setObjectName("sidebarScroll")
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sidebar_scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        sidebar_scroll.setFixedWidth(410)
        sidebar_scroll.setWidget(sidebar)

        body.addWidget(sidebar_scroll)
        body.addLayout(main_area, 1)

        root_layout.addWidget(header)
        root_layout.addLayout(body, 1)
        self._apply_style()

    def _labeled(self, label, widget):
        box = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        lab = QtWidgets.QLabel(label)
        lab.setObjectName("fieldLabel")
        lab.setMinimumHeight(22)
        layout.addWidget(lab)
        layout.addWidget(widget)
        return box

    def _plot_card(self, canvas):
        card = QtWidgets.QFrame()
        card.setObjectName("plotCard")
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(canvas)
        return card

    def _apply_style(self):
        self.setStyleSheet(
            """
            QMainWindow { background: #eef2f6; }
            #sidebarScroll { background: transparent; border: none; }
            #header { background: #ffffff; border-bottom: 1px solid #dce3ea; }
            #appTitle { color: #101820; font-size: 24px; font-weight: 700; }
            #appSubtitle { color: #607080; font-size: 12px; }
            #modeBadge, #statusBadge {
                padding: 7px 12px;
                border-radius: 13px;
                font-weight: 700;
                color: #17202a;
                background: #e8f3f0;
            }
            #statusBadge { background: #f7eadf; }
            #sidebar, #metricCard, #plotCard, #strip {
                background: #ffffff;
                border: 1px solid #dce3ea;
                border-radius: 8px;
            }
            #sectionTitle { color: #17202a; font-size: 17px; font-weight: 700; }
            #fieldLabel, #metricTitle { color: #566575; font-size: 13px; font-weight: 700; }
            #metricValue { color: #101820; font-size: 22px; font-weight: 700; }
            #metricUnit { color: #566575; font-size: 12px; padding-top: 8px; }
            #infoText { color: #52616f; font-size: 13px; line-height: 1.45; }
            QPushButton {
                border-radius: 7px;
                min-height: 42px;
                padding: 8px 14px;
                font-size: 14px;
                font-weight: 700;
            }
            #primaryButton { background: #1f8a70; color: white; border: none; }
            #primaryButton:hover { background: #176d59; }
            #secondaryButton { background: #ffffff; color: #17202a; border: 1px solid #cbd5df; }
            #secondaryButton:hover { background: #f4f7fa; }
            #dangerButton { background: #e76f51; color: white; border: none; }
            #dangerButton:hover { background: #c85c42; }
            #channelButton {
                background: #f7f9fb;
                border: 1px solid #dce3ea;
                color: #17202a;
                min-height: 58px;
                font-size: 13px;
                font-weight: 700;
            }
            #channelButton:checked {
                background: #e8f3f0;
                border: 2px solid #1f8a70;
                color: #0f4f41;
            }
            QComboBox, QSpinBox, QLineEdit {
                background: #ffffff;
                border: 1px solid #cbd5df;
                border-radius: 7px;
                min-height: 40px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #dce3ea;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 16px;
                margin: -6px 0;
                background: #1f8a70;
                border-radius: 8px;
            }
            """
        )

    def _load_mode(self):
        if self.args.realtime:
            self._start_realtime()
            return

        if self.args.force_npy and self.args.disp_npy:
            self._load_offline_files(self.args.force_npy, self.args.disp_npy)
            return

        self._enter_idle()

    def _enter_idle(self):
        self.active_mode = "idle"
        self.playing = False
        self.mode_badge.setText("待机")
        self.status_badge.setText("就绪")
        self.play_btn.setText("播放")
        self.play_btn.setEnabled(False)
        self.calibrate_btn.setEnabled(False)
        self.record_btn.setEnabled(False)
        self.frame_slider.setEnabled(False)
        self.fps_spin.setEnabled(True)
        self.realtime_btn.setText("连接手套")
        self.info_label.setText("请选择离线数据，或连接手套。")

    def _load_offline_files(self, force_path, disp_path):
        self._stop_realtime()
        self.force_data = normalize_dense_array(np.load(force_path))
        self.disp_data = normalize_dense_array(np.load(disp_path))
        self.num_frames = int(min(len(self.force_data), len(self.disp_data)))
        if self.num_frames <= 0:
            raise ValueError("离线数据为空。")
        self.active_mode = "offline"
        self.mode_badge.setText("离线回放")
        self.status_badge.setText("已加载")
        self.playing = self.args.frame is None
        self.play_btn.setEnabled(True)
        self.play_btn.setText("暂停" if self.playing else "播放")
        self.calibrate_btn.setEnabled(False)
        self.record_btn.setEnabled(False)
        self.realtime_btn.setText("连接手套")
        self.frame_slider.setEnabled(True)
        self.fps_spin.setEnabled(True)
        self.frame_slider.setRange(0, max(self.num_frames - 1, 0))
        if self.args.frame is not None:
            self.frame_idx = max(0, min(int(self.args.frame), self.num_frames - 1))
        else:
            self.frame_idx = 0
        self.frame_slider.blockSignals(True)
        self.frame_slider.setValue(self.frame_idx)
        self.frame_slider.blockSignals(False)
        self.info_label.setText(
            f"力场文件: {Path(force_path).name}\n"
            f"位移文件: {Path(disp_path).name}\n"
            f"总帧数: {self.num_frames}"
        )
        self._render_frame(self.disp_data[self.frame_idx], self.force_data[self.frame_idx])

    def _open_offline_dialog(self):
        start_dir = str(Path(_script_dir) / "npy")
        force_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "选择 force_*.npy",
            start_dir,
            "NumPy 数据 (*.npy)",
        )
        if not force_path:
            return
        suggested = str(Path(force_path).with_name(Path(force_path).name.replace("force_", "disp_", 1)))
        if Path(suggested).exists():
            disp_path = suggested
        else:
            disp_path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self,
                "选择对应的 disp_*.npy",
                start_dir,
                "NumPy 数据 (*.npy)",
            )
            if not disp_path:
                return
        try:
            self._load_offline_files(force_path, disp_path)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "加载失败", str(exc))

    def _start_realtime(self):
        self._stop_realtime()
        self.active_mode = "realtime"
        self.mode_badge.setText("实时")
        self.status_badge.setText("连接中")
        self.playing = False
        self.play_btn.setEnabled(False)
        self.calibrate_btn.setEnabled(True)
        self.record_btn.setEnabled(True)
        self.frame_slider.setEnabled(False)
        self.fps_spin.setEnabled(False)
        self.realtime_btn.setText("断开手套")
        port = self.port_edit.text().strip() or auto_select_port()
        model = self.model_edit.text().strip() or DEFAULT_DENSE_MODEL_PATH
        self.info_label.setText(f"设备端口: {port}\n模型: {Path(model).name}")
        self.engine = RealtimeEngine(port, model)
        self.engine.start()

    def _stop_realtime(self):
        if self.recording:
            self._finish_recording()
        if self.engine:
            self.engine.stop()
            self.engine = None
        if self.active_mode == "realtime":
            self.status_badge.setText("已断开")
            self.realtime_btn.setText("连接手套")

    def _shutdown(self):
        if self._shutting_down:
            return
        self._shutting_down = True
        if hasattr(self, "timer"):
            self.timer.stop()
        self._stop_realtime()

    def _toggle_realtime(self):
        if self.engine:
            self._stop_realtime()
            self._enter_idle()
        else:
            self._start_realtime()

    def _toggle_play(self):
        if self.active_mode != "offline":
            return
        self.playing = not self.playing
        self.play_btn.setText("暂停" if self.playing else "播放")

    def _calibrate(self):
        if self.engine:
            self.engine.request_calibrate()

    def _set_channel(self, ch):
        self.current_channel = int(ch)
        self.channel_combo.blockSignals(True)
        self.channel_combo.setCurrentIndex(self.current_channel)
        self.channel_combo.blockSignals(False)
        self.strip.set_channel(self.current_channel)
        if self.active_mode == "offline" and self.num_frames:
            self._render_frame(self.disp_data[self.frame_idx], self.force_data[self.frame_idx])
        elif self.active_mode == "realtime" and self.engine:
            snap = self.engine.snapshot()
            self._render_frame(snap["disp"], snap["force"])

    def _set_field_mode(self, _index=None):
        self.field_mode = self.field_mode_combo.currentData() or "normal"
        if self.active_mode == "offline" and self.num_frames:
            self._render_frame(self.disp_data[self.frame_idx], self.force_data[self.frame_idx])
        elif self.active_mode == "realtime" and self.engine:
            snap = self.engine.snapshot()
            self._render_frame(snap["disp"], snap["force"])

    def _slider_changed(self, value):
        if self.active_mode != "offline":
            return
        self.frame_idx = int(value)
        self.playing = False
        self.play_btn.setText("播放")
        if self.num_frames:
            self._render_frame(self.disp_data[self.frame_idx], self.force_data[self.frame_idx])

    def _tick(self):
        if self.active_mode == "realtime" and self.engine:
            snap = self.engine.snapshot()
            status = self._translate_status(snap["status"])
            if snap["error"]:
                status = "错误"
                self.info_label.setText(snap["error"])
            self.status_badge.setText(status)
            self.fps_card.set_value(f"{snap['poll_fps']:.0f} / {snap['dense_fps']:.0f}")
            self._render_frame(snap["disp"], snap["force"])
            self._record_realtime_frame(snap)
            return

        if self.active_mode != "offline" or not self.playing or self.num_frames <= 0:
            return
        step_ms = max(1, int(1000 / max(self.fps_spin.value(), 1)))
        if not hasattr(self, "_last_step"):
            self._last_step = 0.0
        now_ms = time.time() * 1000
        if now_ms - self._last_step < step_ms:
            return
        self._last_step = now_ms
        self.frame_idx = (self.frame_idx + 1) % self.num_frames
        self.frame_slider.blockSignals(True)
        self.frame_slider.setValue(self.frame_idx)
        self.frame_slider.blockSignals(False)
        self._render_frame(self.disp_data[self.frame_idx], self.force_data[self.frame_idx])

    def _translate_status(self, status):
        return {
            "Idle": "待机",
            "Loading model": "加载模型",
            "Checking CUDA": "检测 CUDA",
            "Connecting": "连接中",
            "Waiting calibration": "等待校准",
            "Calibrating": "校准中",
            "Streaming": "实时中",
            "Error": "错误",
        }.get(status, status)

    def _render_frame(self, disp_frame, force_frame):
        ch = self.current_channel
        disp_frame, force_frame = apply_zero_threshold(disp_frame, force_frame)
        disp_ch = disp_frame[ch]
        force_ch = force_frame[ch]
        if self.field_mode == "tangential":
            self.disp_canvas.set_title("切向位移")
            self.force_canvas.set_title("切向力")
            self.disp_canvas.update_tangential(disp_ch)
            self.force_canvas.update_tangential(force_ch)
        else:
            self.disp_canvas.set_title("法向位移")
            self.force_canvas.set_title("法向力")
            self.disp_canvas.update_heatmap(np.abs(disp_ch[:, :, 2]))
            self.force_canvas.update_heatmap(np.abs(force_ch[:, :, 2]))
        self.strip.update_levels(disp_frame, force_frame)

        m = dense_metrics(disp_ch, force_ch)
        self.cards["disp_max"].set_value(f"{m['disp_max']:.3f}")
        self.cards["disp_mean"].set_value(f"{m['disp_mean']:.3f}")
        self.cards["force_max"].set_value(f"{m['force_max']:.3f}")
        self.cards["force_mean"].set_value(f"{m['force_mean']:.3f}")
        self.cards["force_sum_x"].set_value(f"{m['force_sum_x']:.3f}")
        self.cards["force_sum_y"].set_value(f"{m['force_sum_y']:.3f}")
        self.cards["force_sum_z"].set_value(f"{m['force_sum_z']:.3f}")
        self.frame_card.set_value(str(self.frame_idx if self.active_mode == "offline" else len(self.recorded_force)))
        if self.active_mode == "offline":
            self.status_badge.setText("回放中" if self.playing else "已暂停")
            self.fps_card.set_value(f"{self.fps_spin.value()} / -")

    def _toggle_recording(self):
        if self.active_mode != "realtime" or not self.engine:
            QtWidgets.QMessageBox.information(self, "无法录制", "请先连接手套。")
            return
        if self.recording:
            self._finish_recording()
            return
        snap = self.engine.snapshot()
        if not snap["baseline_ready"]:
            QtWidgets.QMessageBox.information(self, "等待校准", "请等待自动校准完成，或点击“基准校准”。")
            return
        self.recording = True
        self.recorded_disp = []
        self.recorded_force = []
        self.last_record_time = 0.0
        self.record_btn.setText("停止并保存")
        self.record_btn.setObjectName("dangerButton")
        self.record_btn.style().unpolish(self.record_btn)
        self.record_btn.style().polish(self.record_btn)
        self.status_badge.setText("录制中")
        self.info_label.setText("正在录制实时 dense 数据。")

    def _record_realtime_frame(self, snap):
        if not self.recording or not snap["baseline_ready"] or snap["error"]:
            return
        now = time.time()
        target_interval = 1.0 / max(float(self.fps_spin.value()), 1.0)
        if now - self.last_record_time < target_interval:
            return
        self.last_record_time = now
        disp, force = apply_zero_threshold(snap["disp"], snap["force"])
        self.recorded_disp.append(disp.astype(np.float32).copy())
        self.recorded_force.append(force.astype(np.float32).copy())
        self.info_label.setText(f"正在录制实时 dense 数据。\n已录制: {len(self.recorded_force)} 帧")

    def _finish_recording(self):
        if not self.recording:
            return
        self.recording = False
        self.record_btn.setText("开始录制")
        if not self.recorded_force:
            self.info_label.setText("没有录到有效帧。")
            return
        save_dir = Path(_script_dir) / "npy"
        save_dir.mkdir(exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        force_file = save_dir / f"force_{ts}.npy"
        disp_file = save_dir / f"disp_{ts}.npy"
        force_arr = np.asarray(self.recorded_force, dtype=np.float32)
        disp_arr = np.asarray(self.recorded_disp, dtype=np.float32)
        for idx in range(len(disp_arr)):
            disp_arr[idx], force_arr[idx] = apply_zero_threshold(disp_arr[idx], force_arr[idx])
        np.save(force_file, force_arr)
        np.save(disp_file, disp_arr)
        self.info_label.setText(
            f"录制已保存。\n"
            f"力场: {force_file.name} {force_arr.shape}\n"
            f"位移: {disp_file.name} {disp_arr.shape}"
        )

    def _save_snapshot(self):
        now = time.time()
        if now - self.last_save_time < 0.5:
            return
        self.last_save_time = now
        out_dir = Path(_script_dir) / "snapshots"
        out_dir.mkdir(exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = out_dir / f"dense_dashboard_{ts}.png"
        pixmap = self.grab()
        pixmap.save(str(path))
        self.info_label.setText(f"截图已保存:\n{path}")

    def closeEvent(self, event):
        self._shutdown()
        event.accept()


def parse_args():
    parser = argparse.ArgumentParser(description="TouchGlove 触觉控制台。")
    parser.add_argument("--force_npy", default=None, type=str, help="离线回放的 force_*.npy 路径。")
    parser.add_argument("--disp_npy", default=None, type=str, help="离线回放的 disp_*.npy 路径。")
    parser.add_argument("--frame", default=None, type=int, help="离线模式下固定显示的帧序号。")
    parser.add_argument("--fps", default=30, type=int, help="离线回放帧率，也是实时录制采样帧率。")
    parser.add_argument("--realtime", action="store_true", help="启动后直接连接手套。")
    parser.add_argument("--port", default=None, type=str, help="实时模式设备端口。")
    parser.add_argument("--model", default=DEFAULT_DENSE_MODEL_PATH, type=str, help="实时模式 dense 模型路径，默认使用 models/dense_3ch.enc。")
    return parser.parse_args()


def main():
    args = parse_args()
    app = QtWidgets.QApplication(sys.argv)
    app.setFont(QtGui.QFont("Noto Sans CJK SC", 10))
    window = DenseDashboard(args)
    app.aboutToQuit.connect(window._shutdown)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
