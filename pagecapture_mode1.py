#!/usr/bin/env python3
"""
PageCapture - Mode 1: External Browser Capture

Captures a webpage from the user's normal Firefox/Chrome/Edge window.
This mode is intended for sites that reject embedded QWebEngineView,
such as portals that display "Developer Tools Not Allowed".

Workflow:
    1. Enter URL
    2. Open Browser
    3. Position the browser so the desired webpage is visible
    4. Select Capture Area
    5. Start Capture
    6. The utility scrolls the browser and captures the selected screen area
    7. Screenshots are optionally saved and combined into a PDF

Dependencies:
    py -m pip install PySide6 Pillow pyautogui reportlab

Run:
    py pagecapture_mode1.py

Notes:
    - Designed primarily for Windows.
    - The browser remains a normal user browser; no embedded WebEngine is used.
    - The user must keep the browser unobstructed while capturing.
"""

import os
import sys
import time
import webbrowser
from pathlib import Path

try:
    import pyautogui
    from PIL import Image, ImageChops, ImageStat
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4, LETTER, landscape
except ImportError as exc:
    missing = str(exc)
    raise SystemExit(
        f"Missing dependency: {missing}\n\n"
        "Install with:\n"
        "py -m pip install PySide6 Pillow pyautogui reportlab"
    )

from PySide6.QtCore import Qt, QTimer, QRect, QPoint, Signal
from PySide6.QtGui import QPainter, QPen, QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


APP_NAME = "PageCapture — Mode 1"
DEFAULT_OUTPUT = str(Path.home() / "Documents" / "pagecapture.pdf")


class SelectionOverlay(QWidget):
    areaSelected = Signal(int, int, int, int)
    cancelled = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Select Capture Area")
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)
        self.origin = QPoint()
        self.current = QPoint()
        self.dragging = False

        screen = QApplication.primaryScreen()
        self.setGeometry(screen.geometry())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 90))

        if self.dragging:
            rect = QRect(self.origin, self.current).normalized()
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(rect, Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

            pen = QPen(QColor(0, 220, 255), 3)
            painter.setPen(pen)
            painter.drawRect(rect)

            painter.setPen(Qt.white)
            painter.setFont(QFont("Segoe UI", 11))
            painter.drawText(
                rect.adjusted(8, 8, -8, -8),
                Qt.AlignTop | Qt.AlignLeft,
                f"{rect.width()} × {rect.height()}",
            )

        painter.setPen(Qt.white)
        painter.setFont(QFont("Segoe UI", 12, QFont.Bold))
        painter.drawText(
            self.rect(),
            Qt.AlignTop | Qt.AlignHCenter,
            "Drag a rectangle around the webpage area to capture  •  ESC to cancel",
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.origin = event.position().toPoint()
            self.current = self.origin
            self.dragging = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.current = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton or not self.dragging:
            return

        self.current = event.position().toPoint()
        self.dragging = False
        rect = QRect(self.origin, self.current).normalized()

        if rect.width() < 100 or rect.height() < 100:
            self.cancelled.emit()
            self.close()
            return

        self.areaSelected.emit(
            rect.x(), rect.y(), rect.width(), rect.height()
        )
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.cancelled.emit()
            self.close()


class PageCaptureMode1(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1100, 780)

        self.capture_rect = None
        self.overlay = None
        self.captures = []
        self.positions = []
        self.capturing = False
        self.paused = False
        self.capture_index = 0
        self.stable_count = 0
        self.last_image = None
        self.total_estimate = 100

        self.build_ui()
        self.log("Mode 1 ready — external browser capture.")
        self.log("This mode does not use QWebEngineView.")

    def build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)

        url_row = QHBoxLayout()
        self.url_edit = QLineEdit()
        self.url_edit.setText("https://revenueharyana.gov.in/Home/Jamabandi/")
        self.url_edit.setPlaceholderText("https://...")
        self.open_btn = QPushButton("Open Browser")
        self.open_btn.clicked.connect(self.open_browser)

        url_row.addWidget(QLabel("Page:"))
        url_row.addWidget(self.url_edit, 1)
        url_row.addWidget(self.open_btn)
        root.addLayout(url_row)

        info = QLabel(
            "Mode 1 uses your normal browser. After opening the page, "
            "position the browser and select only the webpage area."
        )
        info.setWordWrap(True)
        root.addWidget(info)

        area_box = QGroupBox("Capture Area")
        area_row = QHBoxLayout(area_box)

        self.area_label = QLabel("Not selected")
        self.select_btn = QPushButton("Select Capture Area")
        self.select_btn.clicked.connect(self.select_area)
        self.clear_area_btn = QPushButton("Clear")
        self.clear_area_btn.clicked.connect(self.clear_area)

        area_row.addWidget(self.area_label, 1)
        area_row.addWidget(self.select_btn)
        area_row.addWidget(self.clear_area_btn)
        root.addWidget(area_box)

        settings_box = QGroupBox("Capture Settings")
        form = QFormLayout(settings_box)

        self.scroll_pixels = QSpinBox()
        self.scroll_pixels.setRange(50, 2000)
        self.scroll_pixels.setValue(600)
        self.scroll_pixels.setSuffix(" px")
        self.scroll_pixels.setToolTip(
            "Approximate vertical scroll movement between screenshots."
        )

        self.delay = QDoubleSpinBox()
        self.delay.setRange(0.2, 20.0)
        self.delay.setSingleStep(0.1)
        self.delay.setValue(1.2)
        self.delay.setSuffix(" sec")

        self.max_captures = QSpinBox()
        self.max_captures.setRange(1, 5000)
        self.max_captures.setValue(300)

        self.scroll_mode = QComboBox()
        self.scroll_mode.addItems([
            "Mouse wheel",
            "Page Down",
        ])

        self.pdf_size = QComboBox()
        self.pdf_size.addItems([
            "A4 Portrait",
            "A4 Landscape",
            "Letter Portrait",
            "Letter Landscape",
        ])

        self.output_edit = QLineEdit(DEFAULT_OUTPUT)
        output_row = QHBoxLayout()
        output_row.addWidget(self.output_edit, 1)
        browse = QPushButton("Browse")
        browse.clicked.connect(self.browse_output)
        output_row.addWidget(browse)

        self.save_images = QCheckBox("Save individual PNG screenshots")
        self.save_images.setChecked(True)

        form.addRow("Scroll method:", self.scroll_mode)
        form.addRow("Scroll amount:", self.scroll_pixels)
        form.addRow("Delay after scroll:", self.delay)
        form.addRow("Maximum captures:", self.max_captures)
        form.addRow("PDF page size:", self.pdf_size)
        form.addRow("PDF output:", output_row)
        form.addRow("", self.save_images)

        root.addWidget(settings_box)

        controls = QHBoxLayout()

        self.start_btn = QPushButton("▶ Start Capture")
        self.start_btn.clicked.connect(self.start_capture)

        self.pause_btn = QPushButton("⏸ Pause")
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.pause_btn.setEnabled(False)

        self.stop_btn = QPushButton("■ Stop")
        self.stop_btn.clicked.connect(self.stop_capture)
        self.stop_btn.setEnabled(False)

        self.pdf_btn = QPushButton("Create PDF")
        self.pdf_btn.clicked.connect(self.create_pdf)
        self.pdf_btn.setEnabled(False)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_captures)

        controls.addWidget(self.start_btn)
        controls.addWidget(self.pause_btn)
        controls.addWidget(self.stop_btn)
        controls.addStretch()
        controls.addWidget(self.pdf_btn)
        controls.addWidget(self.clear_btn)

        root.addLayout(controls)

        progress_row = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setValue(0)

        self.count_label = QLabel("Captures: 0")
        self.state_label = QLabel("Ready")

        progress_row.addWidget(self.progress, 1)
        progress_row.addWidget(self.count_label)
        progress_row.addWidget(self.state_label)
        root.addLayout(progress_row)

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(150)
        root.addWidget(self.log_box)

        self.setCentralWidget(central)

    def log(self, text):
        self.log_box.appendPlainText(
            f"[{time.strftime('%H:%M:%S')}] {text}"
        )

    # ---------------------------------------------------------------
    # Browser
    # ---------------------------------------------------------------

    def open_browser(self):
        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, APP_NAME, "Enter a URL first.")
            return

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        self.log(f"Opening normal browser: {url}")
        webbrowser.open(url)
        self.statusBar().showMessage(
            "Browser opened. Position the page, then select the capture area."
        )

    # ---------------------------------------------------------------
    # Area selection
    # ---------------------------------------------------------------

    def select_area(self):
        self.hide()
        QApplication.processEvents()
        time.sleep(0.5)

        self.overlay = SelectionOverlay()
        self.overlay.areaSelected.connect(self.area_selected)
        self.overlay.cancelled.connect(self.selection_cancelled)
        self.overlay.show()
        self.overlay.raise_()
        self.overlay.activateWindow()

    def area_selected(self, x, y, w, h):
        self.capture_rect = (x, y, w, h)
        self.area_label.setText(
            f"X={x}, Y={y}, Width={w}, Height={h}"
        )
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self.log(f"Capture area selected: {x},{y} {w}×{h}")

    def selection_cancelled(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self.log("Capture-area selection cancelled.")

    def clear_area(self):
        self.capture_rect = None
        self.area_label.setText("Not selected")
        self.log("Capture area cleared.")

    # ---------------------------------------------------------------
    # Capture
    # ---------------------------------------------------------------

    def start_capture(self):
        if not self.capture_rect:
            QMessageBox.warning(
                self,
                APP_NAME,
                "Select the browser webpage capture area first.",
            )
            return

        if self.capturing:
            return

        answer = QMessageBox.information(
            self,
            APP_NAME,
            "Before capture starts:\n\n"
            "1. Make sure the normal browser is visible.\n"
            "2. Make sure the selected rectangle is over the webpage.\n"
            "3. Do not move or cover the browser while capturing.\n\n"
            "Click OK to begin.",
            QMessageBox.Ok | QMessageBox.Cancel,
        )

        if answer != QMessageBox.Ok:
            return

        self.hide()
        QApplication.processEvents()
        time.sleep(0.7)

        self.captures = []
        self.positions = []
        self.capture_index = 0
        self.stable_count = 0
        self.last_image = None
        self.capturing = True
        self.paused = False

        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.pause_btn.setText("⏸ Pause")
        self.stop_btn.setEnabled(True)
        self.pdf_btn.setEnabled(False)
        self.progress.setRange(0, 0)
        self.state_label.setText("Capturing...")
        self.count_label.setText("Captures: 0")

        self.log("Capture started.")
        self.capture_once()

    def capture_once(self):
        if not self.capturing:
            return

        if self.paused:
            return

        x, y, w, h = self.capture_rect

        try:
            image = pyautogui.screenshot(region=(x, y, w, h)).convert("RGB")
        except Exception as exc:
            self.finish_capture(f"Screenshot error: {exc}")
            return

        self.capture_index += 1
        self.captures.append(image)
        self.positions.append(self.capture_index)

        self.count_label.setText(f"Captures: {len(self.captures)}")
        self.state_label.setText(f"Captured {len(self.captures)}")
        self.log(f"Captured screenshot #{len(self.captures)}.")

        # Detect an unchanged viewport. This is the safest generic
        # bottom-of-page test when we cannot inspect browser DOM.
        if self.last_image is not None:
            similarity = self.image_similarity(self.last_image, image)
            self.log(f"Viewport similarity: {similarity:.4f}")

            if similarity >= 0.998:
                self.stable_count += 1
            else:
                self.stable_count = 0

            if self.stable_count >= 2:
                self.finish_capture("Page appears to have reached the bottom.")
                return

        self.last_image = image.copy()

        if len(self.captures) >= self.max_captures.value():
            self.finish_capture("Maximum capture count reached.")
            return

        QTimer.singleShot(
            int(self.delay.value() * 1000),
            self.scroll_and_continue,
        )

    @staticmethod
    def image_similarity(a, b):
        if a.size != b.size:
            return 0.0

        # Compare a reduced image to make the check inexpensive.
        size = (120, 80)
        aa = a.resize(size)
        bb = b.resize(size)

        diff = ImageChops.difference(aa, bb)
        stat = ImageStat.Stat(diff)
        mean = sum(stat.mean) / len(stat.mean)
        return max(0.0, 1.0 - (mean / 255.0))

    def scroll_and_continue(self):
        if not self.capturing or self.paused:
            return

        x, y, w, h = self.capture_rect

        # Place mouse inside the browser content area so wheel events
        # are delivered to the webpage rather than another application.
        pyautogui.moveTo(
            x + max(10, w // 2),
            y + max(10, h // 2),
            duration=0.15,
        )

        if self.scroll_mode.currentText() == "Page Down":
            pyautogui.press("pagedown")
        else:
            # pyautogui scroll units are not pixels. This mapping gives
            # a practical scrolling speed across common browsers.
            clicks = max(1, round(self.scroll_pixels.value() / 100))
            pyautogui.scroll(-clicks)

        QTimer.singleShot(
            int(self.delay.value() * 1000),
            self.capture_once,
        )

    def toggle_pause(self):
        if not self.capturing:
            return

        self.paused = not self.paused

        if self.paused:
            self.pause_btn.setText("▶ Resume")
            self.state_label.setText("Paused")
            self.log("Capture paused.")
        else:
            self.pause_btn.setText("⏸ Pause")
            self.state_label.setText("Capturing...")
            self.log("Capture resumed.")
            QTimer.singleShot(300, self.capture_once)

    def stop_capture(self):
        if not self.capturing:
            return

        self.capturing = False
        self.paused = False

        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.pdf_btn.setEnabled(bool(self.captures))
        self.state_label.setText("Stopped")

        self.log(
            f"Capture stopped. {len(self.captures)} screenshot(s) collected."
        )
        self.showNormal()
        self.raise_()
        self.activateWindow()

        if self.save_images.isChecked() and self.captures:
            self.save_images_to_folder()

    def finish_capture(self, reason):
        self.capturing = False
        self.paused = False

        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.pdf_btn.setEnabled(bool(self.captures))
        self.state_label.setText("Finished")

        self.log(reason)
        self.log(f"Total screenshots: {len(self.captures)}.")

        if self.save_images.isChecked() and self.captures:
            self.save_images_to_folder()

        self.showNormal()
        self.raise_()
        self.activateWindow()

        if self.captures:
            QMessageBox.information(
                self,
                APP_NAME,
                f"Capture finished.\n\n{reason}\n\n"
                f"Screenshots captured: {len(self.captures)}",
            )

    # ---------------------------------------------------------------
    # Saving images
    # ---------------------------------------------------------------

    def save_images_to_folder(self):
        pdf = Path(self.output_edit.text().strip() or DEFAULT_OUTPUT)
        folder = pdf.parent / f"{pdf.stem}_screenshots"
        folder.mkdir(parents=True, exist_ok=True)

        for i, image in enumerate(self.captures, 1):
            image.save(folder / f"page_{i:04d}.png", "PNG")

        self.log(f"PNG screenshots saved to: {folder}")

    # ---------------------------------------------------------------
    # PDF
    # ---------------------------------------------------------------

    def browse_output(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Choose PDF Output",
            self.output_edit.text() or DEFAULT_OUTPUT,
            "PDF files (*.pdf)",
        )

        if path:
            if not path.lower().endswith(".pdf"):
                path += ".pdf"
            self.output_edit.setText(path)

    def selected_page_size(self):
        mode = self.pdf_size.currentText()

        if mode == "A4 Landscape":
            return landscape(A4)
        if mode == "Letter Portrait":
            return LETTER
        if mode == "Letter Landscape":
            return landscape(LETTER)
        return A4

    def create_pdf(self):
        if not self.captures:
            QMessageBox.information(
                self, APP_NAME, "No screenshots are available."
            )
            return

        path = self.output_edit.text().strip() or DEFAULT_OUTPUT
        if not path.lower().endswith(".pdf"):
            path += ".pdf"

        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)

        page_w, page_h = self.selected_page_size()

        try:
            pdf = canvas.Canvas(str(output), pagesize=(page_w, page_h))

            margin = 24

            for index, image in enumerate(self.captures, 1):
                iw, ih = image.size

                usable_w = page_w - (2 * margin)
                usable_h = page_h - (2 * margin)

                scale = min(usable_w / iw, usable_h / ih)
                dw = iw * scale
                dh = ih * scale

                x = (page_w - dw) / 2
                y = (page_h - dh) / 2

                temp = output.parent / f".pagecapture_temp_{index}.jpg"
                image.save(temp, "JPEG", quality=95)

                pdf.drawImage(
                    str(temp),
                    x,
                    y,
                    width=dw,
                    height=dh,
                    preserveAspectRatio=True,
                    mask="auto",
                )

                pdf.setFont("Helvetica", 8)
                pdf.drawCentredString(
                    page_w / 2,
                    10,
                    f"Page {index} of {len(self.captures)}",
                )

                pdf.showPage()

                try:
                    temp.unlink()
                except OSError:
                    pass

            pdf.save()

        except Exception as exc:
            QMessageBox.critical(
                self,
                APP_NAME,
                f"Could not create PDF:\n\n{exc}",
            )
            self.log(f"PDF error: {exc}")
            return

        self.log(f"PDF created: {output}")
        self.state_label.setText("PDF created")

        QMessageBox.information(
            self,
            APP_NAME,
            f"PDF created successfully.\n\n{output}\n\n"
            f"{len(self.captures)} screenshot(s) combined.",
        )

    def clear_captures(self):
        if self.capturing:
            return

        self.captures.clear()
        self.positions.clear()
        self.last_image = None
        self.stable_count = 0
        self.capture_index = 0

        self.count_label.setText("Captures: 0")
        self.state_label.setText("Ready")
        self.progress.setRange(0, 0)
        self.progress.setValue(0)
        self.pdf_btn.setEnabled(False)

        self.log("Captures cleared.")

    # ---------------------------------------------------------------
    # Close
    # ---------------------------------------------------------------

    def closeEvent(self, event):
        if self.capturing:
            reply = QMessageBox.question(
                self,
                APP_NAME,
                "Capture is running. Stop and exit?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                event.ignore()
                return

        self.capturing = False
        event.accept()


def main():
    # Prevent pyautogui's fail-safe from making a normal mouse movement
    # accidentally abort the application.
    pyautogui.PAUSE = 0.05
    pyautogui.FAILSAFE = True

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    window = PageCaptureMode1()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
