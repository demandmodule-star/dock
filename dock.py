"""
Dynamic Dock Widget - A customizable, auto-hiding dock for desktop applications.

This module provides a configurable dock widget that can be positioned on any screen edge,
with features like auto-hiding, custom styling, and persistent settings.

Author: Demand Module
License: MIT
"""

import os
import sys
import json

from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QDialog, QVBoxLayout, QHBoxLayout,
    QComboBox, QSlider, QSpinBox, QColorDialog, QMessageBox, QLabel
)
from PyQt6.QtCore import Qt, QTimer, QRect, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPainter, QColor

# Dock position constants
EDGE_TOP = 'top'
EDGE_BOTTOM = 'bottom'
EDGE_LEFT = 'left'
EDGE_RIGHT = 'right'

SHOW_TRIGGER_DISTANCE = 20  # Distance from edge to trigger show

class SettingsDialog(QDialog):
    """Settings dialog for configuring dock appearance and behavior.
    
    Provides controls for:
    - Dock position selection
    - Transparency adjustment
    - Color selection
    - Size configuration
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Dock Settings")
        self.setFixedSize(300, 250)
        
        # Center the dialog on screen
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2
        )

        layout = QVBoxLayout()

        # Dock Position
        pos_layout = QHBoxLayout()
        pos_label = QLabel("Dock Position:")
        self.pos_combo = QComboBox()
        self.pos_combo.addItems([EDGE_LEFT, EDGE_RIGHT, EDGE_TOP, EDGE_BOTTOM])
        self.pos_combo.setCurrentText(self.parent.edge)
        pos_layout.addWidget(pos_label)
        pos_layout.addWidget(self.pos_combo)
        layout.addLayout(pos_layout)

        # Transparency
        trans_layout = QHBoxLayout()
        trans_label = QLabel("Transparency:")
        self.trans_slider = QSlider(Qt.Orientation.Horizontal)
        self.trans_slider.setRange(0, 100)
        self.trans_slider.setValue(self.parent.transparency)
        trans_layout.addWidget(trans_label)
        trans_layout.addWidget(self.trans_slider)
        layout.addLayout(trans_layout)

        # Color Picker
        color_layout = QHBoxLayout()
        color_label = QLabel("Dock Color:")
        self.color_button = QPushButton()
        self.color_button.setFixedSize(50, 25)
        self.update_color_button(self.parent.dock_color)
        self.color_button.clicked.connect(self.choose_color)
        color_layout.addWidget(color_label)
        color_layout.addWidget(self.color_button)
        layout.addLayout(color_layout)

        # Size Settings
        size_layout = QHBoxLayout()
        size_label = QLabel("Size:")
        self.width_spin = QSpinBox()
        self.height_spin = QSpinBox()
        self.width_spin.setRange(40, 200)
        self.height_spin.setRange(120, 600)
        self.width_spin.setValue(self.parent.size)
        self.height_spin.setValue(self.parent.dock_height)
        size_layout.addWidget(size_label)
        size_layout.addWidget(QLabel("W:"))
        size_layout.addWidget(self.width_spin)
        size_layout.addWidget(QLabel("H:"))
        size_layout.addWidget(self.height_spin)
        layout.addLayout(size_layout)

        # Apply Button
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.apply_settings)
        layout.addWidget(apply_btn)

        self.setLayout(layout)

    def update_color_button(self, color):
        self.color_button.setStyleSheet(f"background-color: {color};")

    def choose_color(self):
        color_dialog = QColorDialog(QColor(self.parent.dock_color), self)
        color_dialog.setWindowFlags(
            color_dialog.windowFlags() |
            Qt.WindowType.WindowStaysOnTopHint
        )
        color_dialog.setCurrentColor(QColor(self.parent.dock_color))
        
        if color_dialog.exec() == QColorDialog.DialogCode.Accepted:
            color = color_dialog.currentColor()
            if color.isValid():
                self.parent.dock_color = color.name()
                self.update_color_button(color.name())

    def apply_settings(self):
        new_settings = {
            "dock_position": self.pos_combo.currentText(),
            "transparency": self.trans_slider.value(),
            "dock_color": self.parent.dock_color,
            "dock_size": {
                "width": self.width_spin.value(),
                "height": self.height_spin.value()
            }
        }
        self.parent.apply_settings(new_settings)
        self.close()

class DockWindow(QWidget):
    """Main dock widget with auto-hide functionality and customizable appearance.
    
    Features:
    - Auto-hiding when mouse leaves dock area
    - Configurable position (top, bottom, left, right)
    - Adjustable transparency and color
    - Dynamic sizing based on content
    - Persistent settings via JSON storage
    """
    
    def __init__(self):
        super().__init__()
        self.settings_file = "settings.json"
        self.load_settings()
        
        self.is_hidden = False
        self.settings_dialog_open = False
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
        
        # Set initial size based on settings
        self.update_size()

        # Create main layout for the dock
        self.main_layout = QVBoxLayout(self)  # Assign layout directly to widget
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Add settings button with center alignment
        settings_btn = QPushButton("⚙", self)
        settings_btn.setFixedSize(30, 30)
        settings_btn.clicked.connect(self.show_settings)
        settings_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                font-size: 20px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 30);
                border-radius: 15px;
            }
        """)
        self.main_layout.addWidget(settings_btn, alignment=Qt.AlignmentFlag.AlignCenter)
    def load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
            else:
                settings = self.get_default_settings()
                self.save_settings(settings)
        except Exception as e:
            settings = self.get_default_settings()
            self.save_settings(settings)

        self.edge = settings['dock_position']
        self.transparency = settings['transparency']
        self.dock_color = settings['dock_color']
        self.size = settings['dock_size']['width']
        self.dock_height = settings['dock_size']['height']
        self.offset = 10

    def get_default_settings(self):
        return {
            "dock_position": EDGE_LEFT,
            "transparency": 60,
            "dock_color": "#000000",
            "dock_size": {
                "width": 50,
                "height": 300
            }
        }

    def save_settings(self, settings):
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save settings: {str(e)}")

    def show_settings(self):
        self.settings_dialog_open = True
        if self.is_hidden:
            self.start_show_animation()
        dialog = SettingsDialog(self)
        dialog.finished.connect(self._on_settings_dialog_closed)
        dialog.exec()

    def _on_settings_dialog_closed(self):
        self.settings_dialog_open = False

    def apply_settings(self, settings):
        self.edge = settings['dock_position']
        self.transparency = settings['transparency']
        self.dock_color = settings['dock_color']
        self.size = settings['dock_size']['width']
        self.dock_height = settings['dock_size']['height']
        
        self.update_size()
        self.place_dock()
        self.update()
        self.save_settings(settings)

    def update_size(self):
        # Set minimum sizes but allow expansion
        if self.edge in [EDGE_TOP, EDGE_BOTTOM]:
            self.setMinimumSize(120, max(self.size, 40))
            self.setMaximumSize(16777215, max(self.size, 40))  # Allow horizontal expansion
        else:
            self.setMinimumSize(max(self.size, 40), 120)
            self.setMaximumSize(max(self.size, 40), 16777215)  # Allow vertical expansion
        
        # Update layout to ensure proper content sizing
        layout = self.layout()
        if layout is not None:
            layout.activate()
            self.adjustSize()
            
        # Ensure the dock is properly centered after size changes
        if self.isVisible():
            self.place_dock()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background with user-defined color and transparency
        color = QColor(self.dock_color)
        color.setAlpha(int(255 * (1 - self.transparency / 100)))
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 16, 16)
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
        if not self.is_hidden and not self.settings_dialog_open:
            self.is_hidden = True
            target_geometry = self.get_hidden_geometry()
            self.animation.setStartValue(self.geometry())
            self.animation.setEndValue(target_geometry)
            self.animation.start()

    def start_show_animation(self):
        if self.is_hidden:
            self.is_hidden = False
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
    dock = DockWindow()
    dock.show()
    # Use single-shot timer to position after the window is shown and sized
    QTimer.singleShot(0, dock.place_dock)
    sys.exit(app.exec())
