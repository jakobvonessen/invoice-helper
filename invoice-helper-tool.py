import sys
from PyQt5.QtCore import Qt, QRect, QSize
from PyQt5.QtGui import QFont, QFontMetrics, QPainter
from PyQt5.QtWidgets import QApplication, QWidget, QTextEdit
from PIL import ImageGrab
import pytesseract

class DragSelection(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setWindowOpacity(0.5)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 50);")
        self.start_point = None
        self.end_point = None
        self.showFullScreen()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_point = event.pos()
            self.end_point = self.start_point
            self.update()

    def mouseMoveEvent(self, event):
        if self.start_point:
            self.end_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.close()
            self.display_text()

    def paintEvent(self, event):
        if self.start_point and self.end_point:
            painter = QPainter(self)
            painter.setPen(Qt.white)
            painter.drawRect(QRect(self.start_point, self.end_point))

    def display_text(self):
        rect = QRect(self.start_point, self.end_point).normalized()
        x, y, width, height = rect.x(), rect.y(), rect.width(), rect.height()
        # Capture the screen region
        screen_rect = (x, y, x + width, y + height)
        screenshot = ImageGrab.grab(bbox=screen_rect)
        # Extract text using pytesseract
        extracted_text = pytesseract.image_to_string(screenshot)
        # Calculate new position for the display window just below the selected area
        new_y = y + height
        self.text_display = TextDisplay(x, new_y, width, height, extracted_text.strip())
        self.text_display.show()

class EditableText(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.parent_widget.is_in_resize_zone(event.pos()):
                self.parent_widget.mousePressEvent(event)
            else:
                super().mousePressEvent(event)
        elif event.button() == Qt.RightButton:
            self.parent_widget.mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.parent_widget.resizing or self.parent_widget.dragging:
            self.parent_widget.mouseMoveEvent(event)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.parent_widget.resizing or self.parent_widget.dragging:
            self.parent_widget.mouseReleaseEvent(event)
        else:
            super().mouseReleaseEvent(event)

class TextDisplay(QWidget):
    def __init__(self, x, y, width, height, text):
        super().__init__()
        self.setGeometry(x, y, width, height)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet("background-color: white;")
        self.setMouseTracking(True)
        self.text_font = QFont("Courier New")
        self.rubber_band_size = QSize(10, 10)  # Resizable corner size
        self.dragging = False
        self.resizing = False
        self.drag_start_position = None
        self.resize_start_position = None

        # Add a custom EditableText widget
        self.text_edit = EditableText(self)
        self.text_edit.setGeometry(0, 0, width, height)
        self.text_edit.setFont(self.text_font)
        self.text_edit.setText(text)
        self.text_edit.setAlignment(Qt.AlignCenter)
        self.text_edit.setStyleSheet("border: none; background: transparent;")
        self.text_edit.setFocusPolicy(Qt.StrongFocus)
        self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text_edit.setLineWrapMode(QTextEdit.NoWrap)
        self.text_edit.setContentsMargins(0, 0, 0, 0)
        self.text_edit.document().setDocumentMargin(0)
        self.text_edit.textChanged.connect(self.adjust_font_size)

        self.adjust_font_size()

    def adjust_font_size(self):
        # Adjust the font size to fit the widget
        text = self.text_edit.toPlainText()
        if not text.strip():
            return
        font = QFont(self.text_font.family())
        font.setBold(True)
        rect = self.text_edit.contentsRect()
        target_width = rect.width()
        target_height = rect.height()

        # Binary search for optimal font size
        min_size = 1
        max_size = 500  # Arbitrary large number
        optimal_size = min_size

        while min_size <= max_size:
            mid_size = (min_size + max_size) // 2
            font.setPointSize(mid_size)
            font_metrics = QFontMetrics(font)
            text_size = font_metrics.size(Qt.TextSingleLine, text)

            if text_size.width() <= target_width and text_size.height() <= target_height:
                optimal_size = mid_size
                min_size = mid_size + 1
            else:
                max_size = mid_size - 1

        # Set the optimal font size
        font.setPointSize(optimal_size)
        self.text_edit.setFont(font)

    def resizeEvent(self, event):
        # Ensure the QTextEdit resizes with the widget
        self.text_edit.setGeometry(0, 0, self.width(), self.height())
        self.adjust_font_size()
        super().resizeEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.is_in_resize_zone(event.pos()):
                self.resizing = True
                self.resize_start_position = event.pos()
            else:
                self.dragging = True
                self.drag_start_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.RightButton:
            self.close()  # Close window on right-click

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(event.globalPos() - self.drag_start_position)
            event.accept()
        elif self.resizing:
            delta = event.pos() - self.resize_start_position
            new_width = max(self.width() + delta.x(), 50)  # Minimum width
            new_height = max(self.height() + delta.y(), 50)  # Minimum height
            self.resize(new_width, new_height)
            self.resize_start_position = event.pos()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.resizing = False
            event.accept()

    def is_in_resize_zone(self, pos):
        return (self.width() - self.rubber_band_size.width() <= pos.x() <= self.width() and
                self.height() - self.rubber_band_size.height() <= pos.y() <= self.height())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DragSelection()
    sys.exit(app.exec_())
