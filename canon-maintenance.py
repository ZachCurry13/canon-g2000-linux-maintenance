#!/usr/bin/env python3
"""Canon IJ Printer Assistant-style maintenance window for a Canon G2000
series printer on Linux.

Only the actions the Linux Canon driver (cnijfilter2) can send are enabled:
cleaning, nozzle check and head alignment. The rest of the Windows tool's
entries are shown greyed out because no command exists for them here.

Needs: cnijfilter2, PyQt6, and the CUPS queue named below.
"""
import subprocess
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QApplication, QFrame, QGridLayout, QHBoxLayout,
                             QLabel, QMessageBox, QPlainTextEdit,
                             QPushButton, QVBoxLayout, QWidget, QDialog,
                             QStyle)

QUEUE = "G2000-canon"
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

        self.status = QLabel("")
        root.addWidget(self.status)

    def statusBar_text(self, t):
        self.status.setText(t)

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
