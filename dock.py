"""
Dynamic Dock Widget - A customizable, auto-hiding dock for desktop applications.

This module provides a configurable dock widget that can be positioned on any screen edge.
The dock supports custom buttons with icons that can launch applications or execute commands,
with a full GUI interface for customization and button management.

Features:
- Auto-hiding dock that slides in/out when mouse hovers
- Configurable position (top, bottom, left, right)
- Advanced button management through GUI:
    * Add, edit, and delete buttons
    * Reorder buttons with up/down controls
    * Icon file picker integration
    * Live preview of changes
- Support for custom icons and actions
- Hover animations and tooltips
- Persistent settings with tabbed interface
- Customizable appearance:
    * Transparency
    * Color
    * Corner radius
    * Size
    * Position

Configuration:
    buttons.json - Defines dock buttons with their icons and actions
    settings.json - Stores dock position, size, and appearance settings

Settings Dialog:
    Customization Tab:
        - Dock position, transparency, color
        - Corner radius and size settings
    Buttons Tab:
        - Full CRUD operations for buttons
        - Button reordering controls
        - Visual icon picker

Usage:
    python dock.py

Author: Demand Module
License: MIT
Repository: https://github.com/demandmodule-star/dock
"""

import os
import sys
import json
import subprocess
import webbrowser
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QDialog, QVBoxLayout, QHBoxLayout,
    QComboBox, QSlider, QSpinBox, QColorDialog, QMessageBox, QLabel,
    QToolButton, QSizePolicy, QTabWidget, QTableWidget, QTableWidgetItem, QButtonGroup,
    QHeaderView, QFileDialog, QLineEdit
)
from PyQt6.QtCore import Qt, QTimer, QRect, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtCore import pyqtProperty as Property
from PyQt6.QtGui import QPainter, QColor, QIcon, QFont

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
        self.setFixedSize(800, 500)
        
        # Center the dialog on screen
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2
        )

        layout = QVBoxLayout()
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.setup_customization_tab()
        self.setup_buttons_tab()
        layout.addWidget(self.tab_widget)
        
        # Bottom buttons
        bottom_btn_layout = QHBoxLayout()
        
        apply_btn = QPushButton("Apply")
        apply_btn.setFixedWidth(120)
        apply_btn.clicked.connect(self.apply_settings)

        apply_close_btn = QPushButton("Apply & Close")
        apply_close_btn.setFixedWidth(120)
        apply_close_btn.clicked.connect(self.apply_and_close_settings)

        bottom_btn_layout.addStretch()
        bottom_btn_layout.addWidget(apply_btn)
        bottom_btn_layout.addWidget(apply_close_btn)
        bottom_btn_layout.addStretch()
        layout.addLayout(bottom_btn_layout)
        
        self.setLayout(layout)

    def setup_customization_tab(self):
        """Setup the customization tab with appearance settings"""
        from PyQt6.QtWidgets import QFormLayout

        customization_tab = QWidget()
        layout = QFormLayout()
        layout.setContentsMargins(20, 20, 20, 20) # Add some padding
        layout.setSpacing(15) # Increase spacing between rows
        
        # --- Basic Settings ---
        basic_heading = QLabel("<b>Basic</b>")
        font = basic_heading.font()
        font.setPointSize(font.pointSize() + 2) # Increase font size
        basic_heading.setFont(font)
        basic_heading.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addRow(basic_heading)

        # Dock Position
        pos_widget = QWidget()
        pos_layout = QHBoxLayout(pos_widget)
        pos_layout.setContentsMargins(0, 0, 0, 0)
        self.pos_button_group = QButtonGroup(self)
        self.pos_button_group.setExclusive(True)

        positions = {
            EDGE_LEFT: "Left", EDGE_RIGHT: "Right",
            EDGE_TOP: "Top", EDGE_BOTTOM: "Bottom"
        }
        for edge, text in positions.items():
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setFixedWidth(70)
            if self.parent.edge == edge:
                btn.setChecked(True)
            self.pos_button_group.addButton(btn, id=list(positions.keys()).index(edge))
            pos_layout.addWidget(btn)
        
        pos_layout.addStretch()
        layout.addRow("Dock Position:", pos_widget)

        # Transparency
        trans_widget = QWidget()
        trans_layout = QHBoxLayout(trans_widget)
        trans_layout.setContentsMargins(0, 0, 0, 0)
        
        self.trans_slider = QSlider(Qt.Orientation.Horizontal)
        self.trans_slider.setMaximumWidth(300) # Reduce slider width
        self.trans_slider.setRange(0, 100)
        self.trans_slider.setValue(self.parent.transparency)
        
        self.trans_label = QLabel(f"{self.parent.transparency}%")
        self.trans_label.setFixedWidth(40) # Give it a fixed width
        self.trans_slider.valueChanged.connect(lambda value: self.trans_label.setText(f"{value}%"))
        
        trans_layout.addWidget(self.trans_slider)
        trans_layout.addWidget(self.trans_label)
        trans_layout.addStretch()
        layout.addRow("Transparency:", trans_widget)

        # Corner Radius
        radius_widget = QWidget()
        radius_layout = QHBoxLayout(radius_widget)
        radius_layout.setContentsMargins(0, 0, 0, 0)
        self.radius_slider = QSlider(Qt.Orientation.Horizontal)
        self.radius_slider.setMaximumWidth(300)
        self.radius_slider.setRange(0, 50)
        self.radius_slider.setValue(getattr(self.parent, 'corner_radius', 16))
        self.radius_label = QLabel(f"{self.radius_slider.value()}")
        self.radius_label.setFixedWidth(40)
        self.radius_slider.valueChanged.connect(lambda value: self.radius_label.setText(f"{value}"))
        radius_layout.addWidget(self.radius_slider)
        radius_layout.addWidget(self.radius_label)
        radius_layout.addStretch()
        layout.addRow("Corner Radius:", radius_widget)

        # Color Picker
        self.color_button = QPushButton()
        self.color_button.setFixedSize(50, 25)
        self.update_color_button(self.parent.dock_color)
        self.color_button.clicked.connect(self.choose_color)
        
        # Use a small layout to keep the button from stretching
        color_widget = QWidget()
        color_layout = QHBoxLayout(color_widget)
        color_layout.setContentsMargins(0, 0, 0, 0)
        color_layout.addWidget(self.color_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addRow("Dock Color:", color_widget)

        # --- Advanced Settings ---
        advanced_heading = QLabel("<b>Advanced</b>")
        advanced_heading.setFont(font) # Use the same larger font
        advanced_heading.setAlignment(Qt.AlignmentFlag.AlignLeft)
        advanced_heading.setContentsMargins(0, 10, 0, 0) # Add 10px space above the heading
        layout.addRow(advanced_heading)

        # Icon Size
        icon_size_widget = QWidget()
        icon_size_layout = QHBoxLayout(icon_size_widget)
        icon_size_layout.setContentsMargins(0, 0, 0, 0)
        self.icon_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.icon_size_slider.setMaximumWidth(300)
        self.icon_size_slider.setRange(16, 64) # e.g., 16px to 64px
        self.icon_size_slider.setValue(getattr(self.parent, 'icon_size', 32))
        self.icon_size_label = QLabel(f"{self.icon_size_slider.value()}px")
        self.icon_size_label.setFixedWidth(40)
        self.icon_size_slider.valueChanged.connect(lambda value: self.icon_size_label.setText(f"{value}px"))
        icon_size_layout.addWidget(self.icon_size_slider)
        icon_size_layout.addWidget(self.icon_size_label)
        icon_size_layout.addStretch()
        layout.addRow("Icon Size:", icon_size_widget)

        customization_tab.setLayout(layout)
        self.tab_widget.addTab(customization_tab, "Customization")

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

    def setup_buttons_tab(self):
        """Setup the buttons tab with CRUD operations"""
        buttons_tab = QWidget()
        layout = QVBoxLayout()
        
        # Buttons table
        self.buttons_table = QTableWidget()
        self.buttons_table.setColumnCount(4)
        self.buttons_table.setHorizontalHeaderLabels(["Name", "Icon", "Action", "Controls"])
        # Set specific column widths
        self.buttons_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)  # Name
        self.buttons_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)  # Icon
        self.buttons_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)      # Action
        self.buttons_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) # Controls
        
        # Set initial column widths
        self.buttons_table.setColumnWidth(0, 150)  # Name
        self.buttons_table.setColumnWidth(1, 200)  # Icon
        self.buttons_table.setColumnWidth(3, 170)  # Controls
        self.buttons_table.verticalHeader().setDefaultSectionSize(40)  # Set row height
        
        # Set selection behavior
        self.buttons_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # Load current buttons
        self.load_buttons_to_table()
        
        layout.addWidget(self.buttons_table)
        
        # Add New Button
        add_btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add New Button")
        add_btn.setFixedWidth(120)
        add_btn.clicked.connect(self.add_new_button)
        add_btn_layout.addWidget(add_btn, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addLayout(add_btn_layout)
        
        buttons_tab.setLayout(layout)
        self.tab_widget.addTab(buttons_tab, "Buttons")

    def load_buttons_to_table(self, add_empty_row=False):
        """Load current buttons into the table"""
        try:
            with open(self.parent.buttons_file, 'r', encoding='utf-8-sig') as f:
                config = json.load(f)
                buttons = config.get('buttons', [])
                
                if add_empty_row:
                    # Append a blank dictionary to create an empty row at the end
                    buttons.append({'name': '', 'icon': '', 'action': ''})

                self.buttons_table.setRowCount(len(buttons))
                for row, button in enumerate(buttons):
                    # Name
                    name_text = button.get('name', '')
                    name_item = QTableWidgetItem(name_text)
                    name_item.setFlags(name_item.flags() | Qt.ItemFlag.ItemIsEditable)
                    self.buttons_table.setItem(row, 0, name_item)
                    
                    # Icon
                    icon_text = button.get('icon', '')
                    self.create_icon_cell_widget(row, icon_text)
                    
                    # Action
                    action_text = button.get('action', '')
                    action_item = QTableWidgetItem(action_text)
                    action_item.setFlags(action_item.flags() | Qt.ItemFlag.ItemIsEditable)
                    self.buttons_table.setItem(row, 2, action_item)
                    
                    # Create and set controls widget
                    self.buttons_table.setCellWidget(row, 3, self.create_controls_widget(row))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load buttons: {str(e)}")

    def add_new_button(self):
        """Add a new, empty button row to the table for editing."""
        # Reload the entire table to include the new empty row
        self.load_buttons_to_table(add_empty_row=True)
        # Reload all controls to ensure proper state
        for i in range(self.buttons_table.rowCount()):
            self.update_row_controls(i)

        self.buttons_table.scrollToBottom()

    def create_controls_widget(self, row):
        """Creates a widget containing the move up, move down, and delete buttons."""
        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(2)

        # Move buttons
        move_up_btn = QPushButton("↑")
        move_up_btn.setObjectName("move_up_btn")
        move_up_btn.setFixedSize(25, 30)
        move_up_btn.clicked.connect(lambda checked, r=row: self.move_button_up(r))
        move_up_btn.setEnabled(row > 0)

        move_down_btn = QPushButton("↓")
        move_down_btn.setObjectName("move_down_btn")
        move_down_btn.setFixedSize(25, 30)
        move_down_btn.clicked.connect(lambda checked, r=row: self.move_button_down(r))
        move_down_btn.setEnabled(row < self.buttons_table.rowCount() - 1)

        delete_btn = QPushButton("Delete")
        delete_btn.setObjectName("delete_btn")
        delete_btn.setFixedSize(50, 30)
        delete_btn.clicked.connect(lambda checked, r=row: self.delete_button(r))

        controls_layout.addWidget(move_up_btn)
        controls_layout.addWidget(move_down_btn)
        controls_layout.addWidget(delete_btn)

        return controls

    def create_icon_cell_widget(self, row, text):
        """Creates a widget with a line edit and a browse button for the icon cell."""
        cell_widget = QWidget()
        layout = QHBoxLayout(cell_widget)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(2)

        icon_edit = QLineEdit()
        icon_edit.setText(text)
        browse_btn = QPushButton("Browse...")
        browse_btn.setFixedSize(70, 30)
        browse_btn.clicked.connect(lambda: self.browse_icon(icon_edit))

        layout.addWidget(icon_edit)
        layout.addWidget(browse_btn)
        self.buttons_table.setCellWidget(row, 1, cell_widget)

    def browse_icon(self, line_edit):
        """Open file dialog for icon selection"""
        icon_path, _ = QFileDialog.getOpenFileName(
            self, "Select Icon", "", "Image Files (*.png *.ico *.jpg *.jpeg)"
        )
        if icon_path:
            line_edit.setText(icon_path)

    def get_row_data(self, row):
        """Get all data from a row"""
        icon_widget = self.buttons_table.cellWidget(row, 1)
        icon_text = icon_widget.findChild(QLineEdit).text()
        return {
            'name': self.buttons_table.item(row, 0).text(),
            'icon': icon_text,
            'action': self.buttons_table.item(row, 2).text()
        }

    def set_row_data(self, row, data):
        """Set all data for a row"""
        self.buttons_table.item(row, 0).setText(data['name'])
        icon_widget = self.buttons_table.cellWidget(row, 1)
        icon_widget.findChild(QLineEdit).setText(data['icon'])
        self.buttons_table.item(row, 2).setText(data['action'])

    def move_button_up(self, row):
        """Move button up one row"""
        if row > 0:
            current_data = self.get_row_data(row)
            above_data = self.get_row_data(row - 1)
            self.set_row_data(row, above_data)
            self.set_row_data(row - 1, current_data)
            # Manually update controls instead of reloading the whole table
            self.update_row_controls(row)
            self.update_row_controls(row - 1)
            self.buttons_table.selectRow(row - 1)

    def move_button_down(self, row):
        """Move button down one row"""
        if row < self.buttons_table.rowCount() - 1:
            current_data = self.get_row_data(row)
            below_data = self.get_row_data(row + 1)
            self.set_row_data(row, below_data)
            self.set_row_data(row + 1, current_data)
            # Manually update controls instead of reloading the whole table
            self.update_row_controls(row)
            self.update_row_controls(row + 1)
            self.buttons_table.selectRow(row + 1)

    def update_row_controls(self, row):
        """Update the enabled state of move buttons for a specific row."""
        controls_widget = self.buttons_table.cellWidget(row, 3)
        if controls_widget:
            move_up_btn = controls_widget.findChild(QPushButton, "move_up_btn")
            move_down_btn = controls_widget.findChild(QPushButton, "move_down_btn")
            
            if move_up_btn:
                move_up_btn.setEnabled(row > 0)
            if move_down_btn:
                move_down_btn.setEnabled(row < self.buttons_table.rowCount() - 1)

    def delete_button(self, row):
        """Delete button from the specified row"""
        if QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this button?"
        ) == QMessageBox.StandardButton.Yes:
            self.buttons_table.removeRow(row)
            # After deleting, update controls for all remaining rows
            for i in range(self.buttons_table.rowCount()):
                self.update_row_controls(i)

    def save_buttons(self):
        """Save buttons configuration to file"""
        buttons = []
        for row in range(self.buttons_table.rowCount()):
            # Skip empty rows that haven't been filled out
            name = self.buttons_table.item(row, 0).text()
            if not name.strip():
                continue

            button = {
                'name': name,
                'icon': self.buttons_table.cellWidget(row, 1).findChild(QLineEdit).text(),
                'action': self.buttons_table.item(row, 2).text()
            }
            buttons.append(button)
            
        config = {'buttons': buttons}
        try:
            with open(self.parent.buttons_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save buttons: {str(e)}")

    def apply_settings(self):
        # Save buttons first
        self.save_buttons()
        
        # Then save general settings
        positions = [EDGE_LEFT, EDGE_RIGHT, EDGE_TOP, EDGE_BOTTOM]
        new_settings = {
            "dock_position": positions[self.pos_button_group.checkedId()],
            "transparency": self.trans_slider.value(),
            "dock_color": self.parent.dock_color,
            "corner_radius": self.radius_slider.value(),
            "icon_size": self.icon_size_slider.value(),
        }
        self.parent.apply_settings(new_settings)
        
        # Reload dock buttons to reflect new order
        self.parent.load_buttons()
        
        # After loading buttons, update the size to fit the content
        self.parent.update_size()
        
        # Recreate the settings button to apply new size
        self.parent.recreate_settings_button()
        
        # Force layout recalculation
        self.parent.main_layout.invalidate()
        self.parent.update_size()

        # If position changed, we need to re-add all buttons to the new layout
        if self.parent.edge != self.parent.old_edge_before_apply:
            # Clear the old layout
            for i in reversed(range(self.parent.main_layout.count())): 
                self.parent.main_layout.itemAt(i).widget().setParent(None)
            # Add all buttons to the new layout
            for btn in self.parent.buttons:
                self.parent.main_layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
            self.parent.main_layout.addWidget(self.parent.settings_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def apply_and_close_settings(self):
        """Apply settings and close the dialog."""
        self.apply_settings()
        self.close()

class DockButton(QToolButton):
    """Custom button class for the dock with hover animations and tooltips.
    
    Features:
    - Hover animations with zoom effect
    - Custom styling with transparent background
    - Fallback handling for fonts and icons
    - Configurable tooltips and actions
    """
    
    def __init__(self, config, initial_icon_size=QSize(32, 32), parent=None):
        super().__init__(parent)
        self.config = config
        self._iconSize = initial_icon_size  # Initial icon size
        self.setup_button()
        
    def setup_button(self):
        try:
            # Set button properties
            name = self.config.get('name', '')
            self.setToolTip(name)  # Use name as tooltip
            
            # Handle icon
            icon_path = self.config.get('icon', '')
            if icon_path and os.path.exists(icon_path):
                icon = QIcon(icon_path)
                self.setIcon(icon)
                self.setIconSize(self._iconSize)
                self.setText('')  # Clear text when using icon
            else:
                self.setText('•')  # Fallback to dot if no icon
            
            self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            self.setCursor(Qt.CursorShape.PointingHandCursor)  # Set pointing hand cursor
            
            # Configure tooltip
            self.setToolTip(name)
            self.setToolTipDuration(3000)  # Show tooltip for 3 seconds
            
        except Exception as e:
            QMessageBox.warning(None, "Button Setup Error", 
                f"Error setting up button {self.config.get('name', 'unknown')}: {str(e)}")
            # Set fallback properties
            self.setToolTip("Error loading button")
            self.setText("•")
            self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            self.setFixedSize(40, 40)
            
        # Apply the style sheet
        self.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                border: none;
                padding: 8px;
            }
            QToolButton:pressed {
                background-color: transparent;
            }
        """)
        
        # Setup hover animation for icon size
        self.zoom_animation = QPropertyAnimation(self, b'iconSize')
        self.zoom_animation.setDuration(150)
        self.zoom_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setIconSize(self._iconSize) # Ensure initial state is set
        
    def enterEvent(self, event):
        super().enterEvent(event)
        # Stop any running animations
        self.zoom_animation.stop()
        # Only zoom the icon, not the button
        self.zoom_animation.setStartValue(self._iconSize)
        self.zoom_animation.setEndValue(self._iconSize * 1.25)  # Scale icon size on hover
        self.zoom_animation.start()
        
    def leaveEvent(self, event):
        super().leaveEvent(event)
        # Stop any running animations
        self.zoom_animation.stop()
        # Return icon to original size
        self.zoom_animation.setStartValue(self._iconSize)
        self.zoom_animation.setEndValue(self._iconSize)  # Return to default size
        self.zoom_animation.start()
        
    def get_iconSize(self):
        return self._iconSize
        
    def set_iconSize(self, size):
        self._iconSize = size
        super().setIconSize(size)
        
    iconSize = Property(QSize, get_iconSize, set_iconSize)

class DockWindow(QWidget):
    """Main dock widget with auto-hide functionality and customizable appearance.
    
    Features:
    - Auto-hiding when mouse leaves dock area
    - Configurable position (top, bottom, left, right)
    - Adjustable transparency and color
    - Dynamic sizing based on content
    - Persistent settings via JSON storage
    - Custom dock buttons with animations
    """
    
    def __init__(self):
        super().__init__()
        self.settings_file = "settings.json"
        self.buttons_file = "buttons.json"
        self.load_settings()
        self.buttons = []
        
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

        # Create main layout for the dock based on position
        self.setup_layout()
        
        # Load and add dock buttons first
        self.load_buttons()
        
        self.recreate_settings_button()
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
        self.corner_radius = settings.get('corner_radius', 16)  # Default to 16 if not set
        self.icon_size = settings.get('icon_size', 32) # Default to 32 if not set
        self.offset = 10

    def get_default_settings(self):
        """Get default settings for first-time initialization.
        
        Returns a dictionary containing default values for all dock settings:
        - dock_position: Initial screen edge placement
        - transparency: Default opacity (0-100)
        - dock_color: Background color in hex format
        - corner_radius: Rounded corner radius in pixels
        - dock_size: Dictionary with width and height values
        """
        return {
            "dock_position": EDGE_LEFT,      # Start on left edge
            "transparency": 60,              # 60% transparency
            "dock_color": "#000000",         # Black background
            "corner_radius": 16,             # Rounded corners
            "icon_size": 32,                 # Default icon size
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
        
    def create_default_buttons_file(self):
        """Create a default buttons.json file with sample configurations.
        
        Creates a basic configuration file with common applications
        that users might want to add to their dock.
        """
        default_buttons = {
            "buttons": [
                {
                    "name": "File Explorer",
                    "icon": "icons/folder.png",
                    "action": "explorer ."
                },
                {
                    "name": "Command Prompt",
                    "icon": "icons/terminal.png",
                    "action": "cmd"
                },
                {
                    "name": "Web Browser",
                    "icon": "icons/chrome.png",
                    "action": "https://www.google.com"
                }
            ]
        }
        try:
            # Ensure the icons directory exists
            icons_dir = os.path.join(os.path.dirname(self.buttons_file), "icons")
            os.makedirs(icons_dir, exist_ok=True)
            
            # Create the buttons configuration
            with open(self.buttons_file, 'w', encoding='utf-8') as f:
                json.dump(default_buttons, f, indent=4)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to create buttons file: {str(e)}")

    def load_buttons(self):
        """Load button configurations from JSON file and create buttons.

        Reads the buttons.json file in UTF-8-sig encoding to handle special characters,
        clears any existing buttons, and creates new buttons based on the configuration.
        Each button is added to the dock with proper alignment and click handling.
        Creates a default buttons.json if it doesn't exist.
        """
        # Create default buttons file if it doesn't exist
        if not os.path.exists(self.buttons_file):
            self.create_default_buttons_file()
        
        try:
            # First remove all existing buttons and the settings button
            for button in self.buttons:
                self.main_layout.removeWidget(button)
                button.deleteLater()
            self.buttons.clear()
            
            # Load and create regular buttons
            with open(self.buttons_file, 'r', encoding='utf-8-sig') as f:
                config = json.load(f)
                for button_config in config.get('buttons', []):
                    button = DockButton(
                        button_config,
                        initial_icon_size=QSize(self.icon_size, self.icon_size),
                        parent=self
                    )
                    button.clicked.connect(lambda checked, b=button_config: self.handle_button_click(b))
                    self.main_layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
                    self.buttons.append(button)
                    
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load buttons: {str(e)}")

    def recreate_settings_button(self):
        """Removes the old settings button and creates a new one with current settings."""
        # Remove existing settings button if it exists
        if hasattr(self, 'settings_btn') and self.settings_btn:
            self.main_layout.removeWidget(self.settings_btn)
            self.settings_btn.deleteLater()

        settings_config = {
            'name': 'Settings',
            'icon': '',  # No icon, using text instead
        }
        settings_icon_size = max(12, int(self.icon_size * 0.75))
        settings_font_size = max(8, int(settings_icon_size * 0.5))
        self.settings_btn = DockButton(
            config=settings_config,
            initial_icon_size=QSize(settings_icon_size, settings_icon_size),
            parent=self
        )
        self.settings_btn.setText("⚙")
        self.settings_btn.setFont(QFont('Arial', settings_font_size))
        self.settings_btn.clicked.connect(self.show_settings)
        self.main_layout.addWidget(self.settings_btn, alignment=Qt.AlignmentFlag.AlignCenter)
            
    def handle_button_click(self, button_config):
        """Handle button clicks by executing the specified command or opening URLs."""
        try:
            action = button_config.get('action', '').strip()
            if action:
                # Check if the action is a URL
                if action.startswith(('http://', 'https://', 'www.')):
                    # Open URLs in default browser
                    webbrowser.open(action)
                elif os.path.exists(action) or os.path.exists(os.path.expandvars(action)):
                    # Handle directory or file paths
                    # Expand environment variables if present
                    expanded_path = os.path.expandvars(action)
                    if os.path.isdir(expanded_path):
                        # For directories, use explorer.exe with /select flag
                        subprocess.Popen(['explorer', expanded_path], shell=False)
                    else:
                        # For files, use the default associated program
                        os.startfile(expanded_path)
                else:
                    # Run other commands in a non-blocking way
                    # Split the command and arguments to avoid shell=True security issues
                    try:
                        # First try to split and run without shell
                        subprocess.Popen(action.split(), shell=False)
                    except (FileNotFoundError, subprocess.SubprocessError):
                        # Fallback to shell=True for complex commands
                        subprocess.Popen(action, shell=True)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to execute action: {str(e)}")

    def setup_layout(self):
        """Create and setup the layout based on dock position."""
        # Remove old layout if it exists
        if hasattr(self, 'main_layout'):
            old_layout = self.main_layout
            for button in self.buttons:
                old_layout.removeWidget(button)
            if hasattr(self, 'settings_btn'):
                old_layout.removeWidget(self.settings_btn)
            QWidget().setLayout(old_layout)

        # Create new layout based on position
        if self.edge in [EDGE_LEFT, EDGE_RIGHT]:
            self.main_layout = QVBoxLayout(self)
        else:
            self.main_layout = QHBoxLayout(self)
        
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(5)

    def apply_settings(self, settings):
        self.old_edge_before_apply = self.edge
        self.edge = settings['dock_position']
        self.transparency = settings['transparency']
        self.dock_color = settings['dock_color']
        self.corner_radius = settings.get('corner_radius', 16)
        self.icon_size = settings.get('icon_size', 32)
        
        # If position changed, update layout
        if self.old_edge_before_apply != self.edge:
            self.setup_layout()
        
        self.update_size()
        self.place_dock()
        self.update()
        self.save_settings(settings)

    def update_size(self):
        """Resizes the dock to fit its contents."""
        # Let the layout manager calculate the optimal size.
        self.adjustSize() # This will trigger a resizeEvent, which will then call place_dock

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background with user-defined color and transparency
        color = QColor(self.dock_color)
        color.setAlpha(int(255 * (1 - self.transparency / 100)))
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), self.corner_radius, self.corner_radius)
        painter.end()

    def resizeEvent(self, event):
        """Override resize event to re-center the dock after size changes."""
        super().resizeEvent(event)
        # Re-center the dock whenever its size changes.
        # This ensures it stays centered after adding/removing buttons.
        self.place_dock()

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
    # Set application icon
    app_icon = QIcon("app.ico")
    app.setWindowIcon(app_icon)
    dock = DockWindow()
    dock.setWindowIcon(app_icon)  # Set icon for the dock window
    dock.show()
    # Use single-shot timer to position after the window is shown and sized
    QTimer.singleShot(0, dock.place_dock)
    sys.exit(app.exec())
