"""Unit tests for the read-only helper functions of the ORVANTA Control Center.

Run with:  QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v
"""
import importlib.util
import os
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC = Path(__file__).resolve().parents[1] / "orvanta-control-center" / "src" / "orvanta_control_center.py"
spec = importlib.util.spec_from_file_location("orvanta_control_center", SRC)
occ = importlib.util.module_from_spec(spec)
spec.loader.exec_module(occ)


class HelperTests(unittest.TestCase):
    def test_human_bytes(self):
        self.assertEqual(occ.human_bytes(0), "0.0 B")
        self.assertEqual(occ.human_bytes(1536), "1.5 KB")
        self.assertEqual(occ.human_bytes(5 * 1024 ** 3), "5.0 GB")
        self.assertEqual(occ.human_bytes(3 * 1024 ** 5), "3072.0 TB")

    def test_read_text_missing_file_returns_default(self):
        self.assertEqual(occ.read_text("/nonexistent/orvanta", "fallback"), "fallback")

    def test_os_name_parsing(self):
        with mock.patch.object(occ, "read_text", return_value='NAME="X"\nPRETTY_NAME="ORVANTA OS 0.1"\n'):
            self.assertEqual(occ.get_os_name(), "ORVANTA OS 0.1")
        with mock.patch.object(occ, "read_text", return_value=""):
            self.assertEqual(occ.get_os_name(), "Linux")

    def test_memory_parsing(self):
        meminfo = "MemTotal: 1000 kB\nMemAvailable: 250 kB\n"
        with mock.patch.object(occ, "read_text", return_value=meminfo):
            used, total, pct = occ.get_memory()
        self.assertEqual((used, total, pct), (750 * 1024, 1000 * 1024, 75))
        with mock.patch.object(occ, "read_text", return_value=""):
            self.assertEqual(occ.get_memory(), (0, 0, 0))

    def test_uptime_format(self):
        with mock.patch.object(occ, "read_text", return_value="90061.5 1.0"):
            self.assertEqual(occ.get_uptime(), "1d 1h 1m")
        with mock.patch.object(occ, "read_text", return_value="garbage"):
            self.assertEqual(occ.get_uptime(), "Unavailable")

    def test_main_window_builds_offscreen(self):
        app = occ.QApplication.instance() or occ.QApplication([])
        window = occ.MainWindow()
        self.assertEqual(window.windowTitle(), occ.APP_NAME)
        self.assertEqual(window.nav.count(), 10)
        window.timer.stop()
        window.close()
        app.processEvents()


if __name__ == "__main__":
    unittest.main()
