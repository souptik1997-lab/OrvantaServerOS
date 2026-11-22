#!/usr/bin/python3
"""ORVANTA Control Center — UI prototype.

Read-only prototype: it reports local system information and does not perform
privileged changes. Administrative actions will later use a narrowly-scoped
Polkit-authorised backend.
"""
import os
import sys
import shutil
import socket
import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QFrame, QGridLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMainWindow, QPushButton, QProgressBar, QVBoxLayout,
    QWidget, QMessageBox
)

APP_NAME = "ORVANTA Control Center"


def read_text(path, default="Unavailable"):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return default


def get_os_name():
    data = {}
    for line in read_text("/etc/os-release", "").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            data[k] = v.strip('"')
    return data.get("PRETTY_NAME", "Linux")


def get_memory():
    values = {}
    for line in read_text("/proc/meminfo", "").splitlines():
        parts = line.split()
        if len(parts) >= 2:
            values[parts[0].rstrip(":")] = int(parts[1]) * 1024
    total = values.get("MemTotal", 0)
    available = values.get("MemAvailable", 0)
    used = max(0, total - available)
    pct = int(used * 100 / total) if total else 0
    return used, total, pct


def get_root_disk():
    usage = shutil.disk_usage("/")
    pct = int(usage.used * 100 / usage.total) if usage.total else 0
    return usage.used, usage.total, pct


def human_bytes(n):
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(n)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def get_uptime():
    try:
        seconds = float(read_text("/proc/uptime", "0").split()[0])
        days, rem = divmod(int(seconds), 86400)
        hours, rem = divmod(rem, 3600)
        minutes = rem // 60
        return f"{days}d {hours}h {minutes}m"
    except (ValueError, IndexError):
        return "Unavailable"


def card(title, value="—", detail=""):
    frame = QFrame()
    frame.setObjectName("metricCard")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(18, 16, 18, 16)
    title_label = QLabel(title.upper())
    title_label.setObjectName("eyebrow")
    value_label = QLabel(value)
    value_label.setObjectName("metricValue")
    detail_label = QLabel(detail)
    detail_label.setObjectName("muted")
    layout.addWidget(title_label)
    layout.addWidget(value_label)
    layout.addWidget(detail_label)
    frame.value_label = value_label
    frame.detail_label = detail_label
    return frame


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1120, 720)
        self.setMinimumSize(900, 600)

        central = QWidget()
        self.setCentralWidget(central)
        outer = QHBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(235)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(18, 24, 18, 20)
        side.setSpacing(12)

        brand = QLabel("◉  ORVANTA")
        brand.setObjectName("brand")
        side.addWidget(brand)
        edition = QLabel("CONTROL CENTER  •  PREVIEW")
        edition.setObjectName("sidebarCaption")
        side.addWidget(edition)
        side.addSpacing(20)

        self.nav = QListWidget()
        self.nav.setObjectName("navigation")
        for name in ["Overview", "System", "Storage", "Network", "Security",
                     "Updates", "Applications", "Users", "Backup", "About"]:
            item = QListWidgetItem(name)
            self.nav.addItem(item)
        self.nav.setCurrentRow(0)
        self.nav.currentRowChanged.connect(self.navigate)
        side.addWidget(self.nav, 1)

        version = QLabel("ORVANTA OS 0.1\nFoundation Edition")
        version.setObjectName("sidebarCaption")
        side.addWidget(version)
        outer.addWidget(sidebar)

        content = QWidget()
        content.setObjectName("content")
        body = QVBoxLayout(content)
        body.setContentsMargins(34, 28, 34, 28)
        body.setSpacing(18)

        top = QHBoxLayout()
        heading_box = QVBoxLayout()
        self.heading = QLabel("Overview")
        self.heading.setObjectName("pageTitle")
        self.subtitle = QLabel("Your system at a glance")
        self.subtitle.setObjectName("muted")
        heading_box.addWidget(self.heading)
        heading_box.addWidget(self.subtitle)
        top.addLayout(heading_box)
        top.addStretch(1)
        self.refresh_button = QPushButton("↻  Refresh")
        self.refresh_button.clicked.connect(self.refresh)
        top.addWidget(self.refresh_button)
        body.addLayout(top)

        self.status = QLabel("●  SYSTEM STATUS: INFORMATION ONLY")
        self.status.setObjectName("statusPill")
        body.addWidget(self.status)

        grid = QGridLayout()
        grid.setSpacing(14)
        self.cpu_card = card("Processor", "—", "Load average")
        self.mem_card = card("Memory", "—", "Used / total")
        self.disk_card = card("System storage", "—", "Used / total on /")
        self.uptime_card = card("Uptime", "—", "Since last boot")
        self.os_card = card("Operating system", get_os_name(), "Distribution")
        self.host_card = card("Device", socket.gethostname(), "Hostname")
        cards = [self.cpu_card, self.mem_card, self.disk_card,
                 self.uptime_card, self.os_card, self.host_card]
        for i, widget in enumerate(cards):
            grid.addWidget(widget, i // 3, i % 3)
        body.addLayout(grid)

        note = QFrame()
        note.setObjectName("notice")
        note_layout = QVBoxLayout(note)
        note_layout.setContentsMargins(18, 14, 18, 14)
        note_title = QLabel("Development preview")
        note_title.setObjectName("noticeTitle")
        note_text = QLabel(
            "This first Control Center build is read-only. Storage changes, "
            "firewall rules, user administration and updates are intentionally "
            "not wired up until their permission model and recovery paths are tested."
        )
        note_text.setWordWrap(True)
        note_text.setObjectName("muted")
        note_layout.addWidget(note_title)
        note_layout.addWidget(note_text)
        body.addWidget(note)
        body.addStretch(1)

        footer = QLabel("ORVANTA • Built on Debian • Local system information")
        footer.setObjectName("footer")
        body.addWidget(footer)
        outer.addWidget(content, 1)

        self.setStyleSheet("""
            QWidget { background: #101827; color: #e8eef7; font-family: 'Noto Sans', 'Segoe UI'; font-size: 10pt; }
            #sidebar { background: #0b1220; border-right: 1px solid #263449; }
            #brand { font-size: 21pt; font-weight: 700; letter-spacing: 1px; color: #f4f7fb; }
            #sidebarCaption { color: #8da1bb; font-size: 8pt; letter-spacing: 1px; }
            #navigation { background: transparent; border: 0; outline: 0; }
            #navigation::item { padding: 12px 12px; border-radius: 7px; color: #bdc9d9; }
            #navigation::item:selected { background: #1d3554; color: white; }
            #content { background: #101827; }
            #pageTitle { font-size: 25pt; font-weight: 650; }
            #muted { color: #9aabc0; }
            #eyebrow { color: #91a6c1; font-size: 8pt; letter-spacing: 1px; }
            #metricCard { background: #172438; border: 1px solid #293c55; border-radius: 12px; }
            #metricValue { font-size: 18pt; font-weight: 650; color: #f5f8fc; }
            QPushButton { background: #244a75; color: white; border: 0; border-radius: 7px; padding: 10px 16px; }
            QPushButton:hover { background: #306397; }
            #statusPill { color: #a9d8c0; background: #15372f; border: 1px solid #285b4d; border-radius: 12px; padding: 8px 12px; }
            #notice { background: #192a40; border: 1px solid #304965; border-radius: 10px; }
            #noticeTitle { font-weight: 650; color: #dce9f8; }
            #footer { color: #71839a; font-size: 8pt; }
        """)

        self.refresh()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(5000)

    def navigate(self, row):
        names = ["Overview", "System", "Storage", "Network", "Security",
                 "Updates", "Applications", "Users", "Backup", "About"]
        name = names[row] if 0 <= row < len(names) else "Overview"
        self.heading.setText(name)
        if row == 0:
            self.subtitle.setText("Your system at a glance")
        else:
            self.subtitle.setText(f"{name} module — planned for a future build")
            QMessageBox.information(
                self, "Module not implemented",
                f"The {name} module is not connected in this read-only preview."
            )

    def refresh(self):
        try:
            load = os.getloadavg()[0]
            self.cpu_card.value_label.setText(f"{load:.2f}")
            self.cpu_card.detail_label.setText("1-minute system load average")
        except (AttributeError, OSError):
            self.cpu_card.value_label.setText("N/A")
        used, total, pct = get_memory()
        self.mem_card.value_label.setText(f"{pct}%")
        self.mem_card.detail_label.setText(f"{human_bytes(used)} / {human_bytes(total)}")
        used, total, pct = get_root_disk()
        self.disk_card.value_label.setText(f"{pct}%")
        self.disk_card.detail_label.setText(f"{human_bytes(used)} / {human_bytes(total)}")
        self.uptime_card.value_label.setText(get_uptime())
        self.os_card.value_label.setText(get_os_name())
        self.host_card.value_label.setText(socket.gethostname())


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setFont(QFont("Noto Sans", 10))
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
