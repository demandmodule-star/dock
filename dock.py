import sys
from PyQt6.QtWidgets import QApplication, QWidget, QLabel
from PyQt6.QtCore import Qt, QTimer, QPoint, QRect, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QCursor, QPainter, QColor

EDGE_TOP = 'top'
EDGE_BOTTOM = 'bottom'
EDGE_LEFT = 'left'
EDGE_RIGHT = 'right'

SHOW_TRIGGER_DISTANCE = 20  # Distance from edge to trigger show

class DockWindow(QWidget):
	def __init__(self, edge=EDGE_LEFT, offset=10, size=80):
		super().__init__()
		self.edge = edge
		self.offset = offset
		self.size = size
		self.is_hidden = False
		self.hide_timer = QTimer(self)
		self.hide_timer.setSingleShot(True)
		self.hide_timer.timeout.connect(self.start_hide_animation)

		# Setup animation
		self.animation = QPropertyAnimation(self, b'geometry')
		self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
		self.animation.setDuration(300)  # 300ms duration

		self.setWindowFlags(
			Qt.WindowType.FramelessWindowHint |
			Qt.WindowType.WindowStaysOnTopHint |
			Qt.WindowType.Tool
		)
		self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
		# Ensure dock is visible with a minimum size
		min_length = 120
		min_width = 60
		if edge in [EDGE_TOP, EDGE_BOTTOM]:
			self.setFixedSize(max(400, min_length), max(self.size, min_width))
		else:
			self.setFixedSize(max(self.size, min_width), max(400, min_length))

		# Add placeholder text
		label = QLabel("Dock", self)
		label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		label.setStyleSheet("font-size: 18px; color: white;")
		label.setGeometry(0, 0, self.width(), self.height())
	def paintEvent(self, event):
		painter = QPainter(self)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing)
		
		# Draw translucent background
		painter.setBrush(QColor(0, 0, 0, 100))  # Semi-transparent black
		painter.setPen(Qt.PenStyle.NoPen)
		painter.drawRoundedRect(self.rect(), 16, 16)  # Rounded corners
		painter.end()

	def place_dock(self):
		screen = QApplication.primaryScreen().geometry()
		if self.edge == EDGE_TOP:
			self.move((screen.width() - self.width()) // 2, self.offset)
		elif self.edge == EDGE_BOTTOM:
			self.move((screen.width() - self.width()) // 2, screen.height() - self.height() - self.offset)
		elif self.edge == EDGE_LEFT:
			self.move(self.offset, (screen.height() - self.height()) // 2)
		elif self.edge == EDGE_RIGHT:
			self.move(screen.width() - self.width() - self.offset, (screen.height() - self.height()) // 2)

	def enterEvent(self, event):
		self.hide_timer.stop()
		if self.is_hidden:
			self.start_show_animation()

	def leaveEvent(self, event):
		self.hide_timer.start(500)  # Start hide timer with 500ms delay

	def start_hide_animation(self):
		if not self.is_hidden:
			self.is_hidden = True
			target_geometry = self.get_hidden_geometry()
			self.animation.setStartValue(self.geometry())
			self.animation.setEndValue(target_geometry)
			self.animation.start()

	def start_show_animation(self):
		if self.is_hidden:
			self.is_hidden = False
			screen = QApplication.primaryScreen().geometry()
			target_geometry = self.get_visible_geometry()
			self.animation.setStartValue(self.geometry())
			self.animation.setEndValue(target_geometry)
			self.animation.start()

	def get_hidden_geometry(self):
		current = self.geometry()
		screen = QApplication.primaryScreen().geometry()
		if self.edge == EDGE_LEFT:
			return QRect(-self.width() + 5, current.y(), current.width(), current.height())
		elif self.edge == EDGE_RIGHT:
			return QRect(screen.width() - 5, current.y(), current.width(), current.height())
		elif self.edge == EDGE_TOP:
			return QRect(current.x(), -self.height() + 5, current.width(), current.height())
		else:  # EDGE_BOTTOM
			return QRect(current.x(), screen.height() - 5, current.width(), current.height())

	def get_visible_geometry(self):
		screen = QApplication.primaryScreen().geometry()
		if self.edge == EDGE_TOP:
			return QRect((screen.width() - self.width()) // 2, self.offset, self.width(), self.height())
		elif self.edge == EDGE_BOTTOM:
			return QRect((screen.width() - self.width()) // 2, screen.height() - self.height() - self.offset, self.width(), self.height())
		elif self.edge == EDGE_LEFT:
			return QRect(self.offset, (screen.height() - self.height()) // 2, self.width(), self.height())
		else:  # EDGE_RIGHT
			return QRect(screen.width() - self.width() - self.offset, (screen.height() - self.height()) // 2, self.width(), self.height())


if __name__ == "__main__":
	app = QApplication(sys.argv)
	# Change edge and offset as needed
	dock = DockWindow(edge=EDGE_LEFT, offset=10)
	dock.place_dock()  # Add this line to position the dock
	dock.show()  # Make sure to show the dock
	sys.exit(app.exec())
