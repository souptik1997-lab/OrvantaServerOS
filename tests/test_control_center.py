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

    def test_firewall_status(self):
        def fake(states):
            return lambda verb, unit: states[(verb, unit)]
        on = {("is-active", "nftables.service"): "active",
              ("is-enabled", "nftables.service"): "enabled"}
        with mock.patch.object(occ, "systemctl_state", side_effect=fake(on)):
            self.assertEqual(occ.get_firewall_status(),
                             ("On", "nftables · inbound default-deny"))
        not_at_boot = dict(on); not_at_boot[("is-enabled", "nftables.service")] = "disabled"
        with mock.patch.object(occ, "systemctl_state", side_effect=fake(not_at_boot)):
            self.assertEqual(occ.get_firewall_status()[0], "On")
            self.assertIn("not enabled at boot", occ.get_firewall_status()[1])
        off = {("is-active", "nftables.service"): "inactive",
               ("is-enabled", "nftables.service"): "enabled"}
        with mock.patch.object(occ, "systemctl_state", side_effect=fake(off)):
            self.assertEqual(occ.get_firewall_status(), ("Off", "nftables.service is inactive"))
        with mock.patch.object(occ, "systemctl_state", return_value="unknown"):
            self.assertEqual(occ.get_firewall_status()[0], "Unknown")

    def test_remote_access_status(self):
        with mock.patch.object(occ, "systemctl_state", return_value="inactive"):
            self.assertEqual(occ.get_remote_access_status()[0], "Off")
        running = lambda verb, unit: "active" if unit == "cockpit.socket" else "inactive"
        with mock.patch.object(occ, "systemctl_state", side_effect=running):
            self.assertEqual(occ.get_remote_access_status(), ("On", "Running: cockpit"))

    def test_systemctl_unavailable(self):
        with mock.patch.object(occ.subprocess, "run", side_effect=FileNotFoundError):
            self.assertEqual(occ.systemctl_state("is-active", "nftables.service"), "unknown")

    def test_desktop_entry_and_icon_match(self):
        root = Path(__file__).resolve().parents[1]
        desktop = root / "orvanta-control-center" / "data" / f"{occ.DESKTOP_FILE_NAME}.desktop"
        self.assertTrue(desktop.is_file())
        self.assertIn(f"Icon={occ.ICON_NAME}", desktop.read_text().splitlines())
        # the package icon and the image's branding icon must be the same logo
        packaged = root / "orvanta-control-center" / "data" / f"{occ.ICON_NAME}.svg"
        branding = (root / "config" / "includes.chroot" / "usr" / "share" / "icons" /
                    "hicolor" / "scalable" / "apps" / f"{occ.ICON_NAME}.svg")
        self.assertEqual(packaged.read_bytes(), branding.read_bytes())

    def test_main_window_builds_offscreen(self):
        app = occ.QApplication.instance() or occ.QApplication([])
        with mock.patch.object(occ, "systemctl_state", return_value="inactive"):
            window = occ.MainWindow()
        self.assertEqual(window.windowTitle(), occ.APP_NAME)
        self.assertEqual(window.nav.count(), 10)
        self.assertEqual(window.fw_card.value_label.text(), "Off")
        window.timer.stop()
        window.close()
        app.processEvents()


if __name__ == "__main__":
    unittest.main()
