#!/usr/bin/env python3
"""Canon IJ Printer Assistant-style maintenance window for a Canon G2000
series printer on Linux.

Only the actions the Linux Canon driver (cnijfilter2) can send are enabled:
cleaning, nozzle check and head alignment. The rest of the Windows tool's
entries are shown greyed out because no command exists for them here.

Also has helpers for everyday trouble: a setup check banner, live queue
status, a test page, cancel-all-jobs and re-enable-printer.

Needs: cnijfilter2, PyQt6, and the CUPS queues named below.
"""
import subprocess
import sys

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (QApplication, QFrame, QGridLayout, QHBoxLayout,
                             QLabel, QMessageBox, QPlainTextEdit,
                             QPushButton, QVBoxLayout, QWidget, QDialog,
                             QStyle)

QUEUE = "G2000-canon"          # Canon-driver queue, used for maintenance jobs
NORMAL_QUEUE = "G2000-series"  # your everyday printing queue (Gutenprint)
TEST_PAGE = "/usr/share/cups/data/testprint"
CMD_DIR = "/usr/share/cmdtocanonij3"

# (title, description, command file or None, confirmation text or None)
LEFT = [
    ("Cleaning", "Eliminates unwanted smudges and lines in the print result.",
     "cleaning.utl", "Cleaning uses a little ink.", "SP_BrowserReload"),
    ("Deep Cleaning", "Unclogs nozzles that cannot be cleared by regular Cleaning.",
     None, None, "SP_DialogResetButton"),
    ("Print Head Alignment", "Fixes print head alignment to correct the misalignment of colors and lines.",
     "autoalign.utl", "Load plain paper first. This prints an alignment pattern.",
     "SP_FileDialogDetailedView"),
    ("Nozzle Check", "Prints a pattern to check whether the print head nozzles are clogged.",
     "nozzlecheck.utl", None, "SP_FileDialogContentsView"),
    ("Ink Flush", "Fills the ink tubes and the print head with ink.",
     None, None, "SP_DriveHDIcon"),
    ("Remaining Ink Notification Settings",
     "Sets the function for notifying the remaining ink level and resets the remaining ink level count.",
     None, None, "SP_MessageBoxWarning"),
]
RIGHT = [
    ("Bottom Plate Cleaning", "Prevents paper smudges during printing.",
     None, None, "SP_DialogResetButton"),
    ("Roller Cleaning", "Performs Roller Cleaning for smoother paper feeding.",
     None, None, "SP_BrowserReload"),
    ("Power Off", "Turns the printer off.", None, None, "SP_DialogCloseButton"),
    ("Auto Power", "Allows you to set the auto power settings.",
     None, None, "SP_MediaPlay"),
    ("Quiet Settings", "Allows you to reduce the printer's operating noise.",
     None, None, "SP_MediaVolumeMuted"),
    ("Custom Settings", "Customize printer mode settings.",
     None, None, "SP_FileDialogInfoView"),
]


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


class Entry(QWidget):
    def __init__(self, window, title, desc, cmdfile, confirm, icon_name):
        super().__init__()
        self.window_ref = window
        self.title, self.cmdfile, self.confirm = title, cmdfile, confirm
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 8, 4, 8)
        icon = QLabel()
        sp = getattr(QStyle.StandardPixmap, icon_name)
        icon.setPixmap(self.style().standardIcon(sp).pixmap(40, 40))
        icon.setFixedWidth(52)
        text = QVBoxLayout()
        self.link = QPushButton(title)
        self.link.setFlat(True)
        self.link.setCursor(Qt.CursorShape.PointingHandCursor if cmdfile
                            else Qt.CursorShape.ForbiddenCursor)
        self.link.setStyleSheet(
            "text-align:left; border:none; padding:0;"
            + ("color:#1a5fb4; text-decoration:underline;" if cmdfile
               else "color:gray;"))
        d = QLabel(desc if cmdfile else desc + "\n(Not available on Linux)")
        d.setWordWrap(True)
        if not cmdfile:
            d.setStyleSheet("color:gray;")
            icon.setEnabled(False)
        text.addWidget(self.link)
        text.addWidget(d)
        lay.addWidget(icon)
        lay.addLayout(text, 1)
        if cmdfile:
            self.link.clicked.connect(self.activate)
        else:
            self.link.setEnabled(False)

    def activate(self):
        if self.confirm:
            ok = QMessageBox.question(
                self, self.title, self.confirm + "\n\nContinue?")
            if ok != QMessageBox.StandardButton.Yes:
                return
        code, out = run(["lp", "-d", QUEUE, "-o",
                         "document-format=application/vnd.cups-command",
                         f"{CMD_DIR}/{self.cmdfile}"])
        if code:
            QMessageBox.warning(self, self.title, out or "Command failed")
        else:
            self.window_ref.statusBar_text(f"Sent: {self.title}")


class TextDialog(QDialog):
    def __init__(self, parent, title, text):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(560, 320)
        lay = QVBoxLayout(self)
        box = QPlainTextEdit(text)
        box.setReadOnly(True)
        lay.addWidget(box)


class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Canon IJ Printer Assistant Tool (Linux)")
        self.setMinimumWidth(780)
        root = QVBoxLayout(self)

        self.banner = QLabel()
        self.banner.setWordWrap(True)
        self.banner.setStyleSheet(
            "background:#fde8e8; color:#8a1c1c; padding:8px; border-radius:4px;")
        self.banner.hide()
        root.addWidget(self.banner)

        top = QFrame()
        top.setFrameShape(QFrame.Shape.StyledPanel)
        tl = QHBoxLayout(top)
        tl.addWidget(QLabel("Printer Name:  Canon G2000 series"))
        tl.addStretch()
        root.addWidget(top)

        grid = QGridLayout()
        for row, (l, r) in enumerate(zip(LEFT, RIGHT)):
            grid.addWidget(Entry(self, *l), row, 0)
            grid.addWidget(Entry(self, *r), row, 1)
        root.addLayout(grid)

        bottom = QHBoxLayout()
        for label, fn in (("View Printer Status", self.show_status),
                          ("View Printer Information", self.show_info)):
            b = QPushButton(label)
            b.setFlat(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet("border:none; color:#1a5fb4; text-decoration:underline;")
            b.clicked.connect(fn)
            bottom.addWidget(b)
        bottom.addStretch()
        root.addLayout(bottom)

        tools = QHBoxLayout()
        for label, fn in (("Print test page", self.print_test_page),
                          ("Cancel all jobs", self.cancel_jobs),
                          ("Re-enable printer", self.reenable)):
            b = QPushButton(label)
            b.clicked.connect(fn)
            tools.addWidget(b)
        tools.addStretch()
        root.addLayout(tools)

        self.status = QLabel("")
        root.addWidget(self.status)
        self.live = QLabel("")
        root.addWidget(self.live)

        self.refresh()
        timer = QTimer(self)
        timer.timeout.connect(self.refresh)
        timer.start(3000)

    def statusBar_text(self, t):
        self.status.setText(t)

    def queue_exists(self, name):
        return run(["lpstat", "-p", name])[0] == 0

    def problems(self):
        """List setup problems with a fix for each, or an empty list."""
        out = []
        if run(["sh", "-c", "lsusb | grep -qi canon"])[0] != 0:
            out.append("The printer isn't detected on USB. Check it is "
                       "powered on and the cable is plugged straight into "
                       "the PC.")
        if not self.queue_exists(QUEUE):
            out.append(f"The maintenance queue '{QUEUE}' doesn't exist. "
                       "See the README's Setup section to create it.")
        if not self.queue_exists(NORMAL_QUEUE):
            out.append(f"The everyday queue '{NORMAL_QUEUE}' doesn't exist, "
                       "so the test page button won't work.")
        return out

    def refresh(self):
        probs = self.problems()
        self.banner.setText("\n".join(probs))
        self.banner.setVisible(bool(probs))
        parts = []
        for q in (NORMAL_QUEUE, QUEUE):
            if self.queue_exists(q):
                line = run(["lpstat", "-p", q])[1].splitlines()[0]
                parts.append(line.split(" since")[0].replace("printer ", ""))
        self.live.setText("Status: " + "  |  ".join(parts) if parts else "")

    def print_test_page(self):
        code, out = run(["lp", "-d", NORMAL_QUEUE, TEST_PAGE])
        self.status.setText(out if code else "Test page sent")

    def cancel_jobs(self):
        ok = QMessageBox.question(
            self, "Cancel all jobs",
            "Cancel every queued print job on both queues?")
        if ok != QMessageBox.StandardButton.Yes:
            return
        for q in (NORMAL_QUEUE, QUEUE):
            run(["cancel", "-a", q])
        self.status.setText("Cancelled all jobs")

    def reenable(self):
        failed = []
        for q in (NORMAL_QUEUE, QUEUE):
            for cmd in ("cupsenable", "cupsaccept"):
                code, out = run([cmd, q])
                if code:
                    failed.append(out)
        if failed:
            QMessageBox.warning(
                self, "Re-enable printer",
                "Some steps need administrator rights:\n" + "\n".join(failed))
        else:
            self.status.setText("Queues enabled and accepting jobs")
        self.refresh()

    def show_status(self):
        _, out = run(["lpstat", "-l", "-p", QUEUE])
        _, jobs = run(["lpstat", "-o", QUEUE])
        TextDialog(self, "Printer Status",
                   out + "\n\nQueued jobs:\n" + (jobs or "none")).exec()

    def show_info(self):
        _, dev = run(["lpstat", "-v", QUEUE])
        _, lsusb = run(["sh", "-c", "lsusb | grep -i canon"])
        TextDialog(self, "Printer Information",
                   f"{dev}\n\nUSB:\n{lsusb or 'Canon device not found on USB'}"
                   ).exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Window()
    w.show()
    sys.exit(app.exec())
