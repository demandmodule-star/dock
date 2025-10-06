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
    QToolButton, QSizePolicy, QTabWidget, QTableWidget, QTableWidgetItem,
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
        
        # Apply Button at bottom
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.apply_settings)
        layout.addWidget(apply_btn)
        
        self.setLayout(layout)

    def setup_customization_tab(self):
        """Setup the customization tab with appearance settings"""
        customization_tab = QWidget()
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

        # Corner Radius
        radius_layout = QHBoxLayout()
        radius_label = QLabel("Corner Radius:")
        self.radius_spin = QSpinBox()
        self.radius_spin.setRange(0, 50)
        self.radius_spin.setValue(getattr(self.parent, 'corner_radius', 16))
        radius_layout.addWidget(radius_label)
        radius_layout.addWidget(self.radius_spin)
        layout.addLayout(radius_layout)

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
        self.buttons_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)        # Controls
        
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
        add_btn = QPushButton("Add New Button")
        add_btn.clicked.connect(self.add_new_button)
        layout.addWidget(add_btn)
        
        buttons_tab.setLayout(layout)
        self.tab_widget.addTab(buttons_tab, "Buttons")

    def load_buttons_to_table(self):
        """Load current buttons into the table"""
        try:
            with open(self.parent.buttons_file, 'r', encoding='utf-8-sig') as f:
                config = json.load(f)
                buttons = config.get('buttons', [])
                
                self.buttons_table.setRowCount(len(buttons))
                for row, button in enumerate(buttons):
                    # Name
                    name_item = QTableWidgetItem(button.get('name', ''))
                    self.buttons_table.setItem(row, 0, name_item)
                    
                    # Icon
                    icon_item = QTableWidgetItem(button.get('icon', ''))
                    self.buttons_table.setItem(row, 1, icon_item)
                    
                    # Action
                    action_item = QTableWidgetItem(button.get('action', ''))
                    self.buttons_table.setItem(row, 2, action_item)
                    
                    # Controls
                    controls = QWidget()
                    controls_layout = QHBoxLayout()
                    controls_layout.setContentsMargins(0, 0, 0, 0)
                    controls_layout.setSpacing(2)
                    
                    # Move buttons
                    move_up_btn = QPushButton("↑")
                    move_up_btn.setFixedSize(25, 30)
                    move_up_btn.clicked.connect(lambda checked, r=row: self.move_button_up(r))
                    move_up_btn.setEnabled(row > 0)  # Disable for first row
                    
                    move_down_btn = QPushButton("↓")
                    move_down_btn.setFixedSize(25, 30)
                    move_down_btn.clicked.connect(lambda checked, r=row: self.move_button_down(r))
                    move_down_btn.setEnabled(row < self.buttons_table.rowCount() - 1)  # Disable for last row
                    
                    # Edit and Delete buttons
                    edit_btn = QPushButton("Edit")
                    edit_btn.setFixedSize(50, 30)
                    edit_btn.clicked.connect(lambda checked, r=row: self.edit_button(r))
                    
                    delete_btn = QPushButton("Delete")
                    delete_btn.setFixedSize(50, 30)
                    delete_btn.clicked.connect(lambda checked, r=row: self.delete_button(r))
                    
                    controls_layout.addWidget(move_up_btn)
                    controls_layout.addWidget(move_down_btn)
                    controls_layout.addWidget(edit_btn)
                    controls_layout.addWidget(delete_btn)
                    controls.setLayout(controls_layout)
                    
                    self.buttons_table.setCellWidget(row, 3, controls)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load buttons: {str(e)}")

    def add_new_button(self):
        """Add a new button row to the table"""
        row = self.buttons_table.rowCount()
        self.buttons_table.insertRow(row)
        
        # Add empty items
        for col in range(3):
            self.buttons_table.setItem(row, col, QTableWidgetItem(""))
            
        # Add controls
        controls = QWidget()
        controls_layout = QHBoxLayout()
        
        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(lambda checked, r=row: self.edit_button(r))
        
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(lambda checked, r=row: self.delete_button(r))
        
        controls_layout.addWidget(edit_btn)
        controls_layout.addWidget(delete_btn)
        controls.setLayout(controls_layout)
        
        self.buttons_table.setCellWidget(row, 3, controls)

    def edit_button(self, row):
        """Edit button in the specified row using a dialog"""
        edit_dialog = QDialog(self)
        edit_dialog.setWindowTitle("Edit Button")
        edit_dialog.setFixedSize(400, 200)
        layout = QVBoxLayout()

        # Name field
        name_layout = QHBoxLayout()
        name_label = QLabel("Name:")
        name_edit = QLineEdit()
        name_edit.setText(self.buttons_table.item(row, 0).text())
        name_layout.addWidget(name_label)
        name_layout.addWidget(name_edit)
        layout.addLayout(name_layout)

        # Icon field with file picker
        icon_layout = QHBoxLayout()
        icon_label = QLabel("Icon:")
        icon_edit = QLineEdit()
        icon_edit.setText(self.buttons_table.item(row, 1).text())
        icon_browse = QPushButton("Browse")
        icon_browse.clicked.connect(lambda: self.browse_icon(icon_edit))
        icon_layout.addWidget(icon_label)
        icon_layout.addWidget(icon_edit)
        icon_layout.addWidget(icon_browse)
        layout.addLayout(icon_layout)

        # Action field
        action_layout = QHBoxLayout()
        action_label = QLabel("Action:")
        action_edit = QLineEdit()
        action_edit.setText(self.buttons_table.item(row, 2).text())
        action_layout.addWidget(action_label)
        action_layout.addWidget(action_edit)
        layout.addLayout(action_layout)

        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        edit_dialog.setLayout(layout)

        # Connect buttons
        save_btn.clicked.connect(lambda: self.save_button_edit(
            row, name_edit.text(), icon_edit.text(), action_edit.text(), edit_dialog
        ))
        cancel_btn.clicked.connect(edit_dialog.close)

        # Show dialog
        edit_dialog.exec()

    def browse_icon(self, line_edit):
        """Open file dialog for icon selection"""
        icon_path, _ = QFileDialog.getOpenFileName(
            self, "Select Icon", "", "Image Files (*.png *.jpg *.jpeg)"
        )
        if icon_path:
            line_edit.setText(icon_path)

    def save_button_edit(self, row, name, icon, action, dialog):
        """Save the edited button values"""
        self.buttons_table.item(row, 0).setText(name)
        self.buttons_table.item(row, 1).setText(icon)
        self.buttons_table.item(row, 2).setText(action)
        dialog.close()

    def get_row_data(self, row):
        """Get all data from a row"""
        return {
            'name': self.buttons_table.item(row, 0).text(),
            'icon': self.buttons_table.item(row, 1).text(),
            'action': self.buttons_table.item(row, 2).text()
        }

    def set_row_data(self, row, data):
        """Set all data for a row"""
        self.buttons_table.item(row, 0).setText(data['name'])
        self.buttons_table.item(row, 1).setText(data['icon'])
        self.buttons_table.item(row, 2).setText(data['action'])

    def move_button_up(self, row):
        """Move button up one row"""
        if row > 0:
            # First get all button configurations
            buttons = []
            for i in range(self.buttons_table.rowCount()):
                buttons.append(self.get_row_data(i))
            
            # Move the button up in the list
            buttons.insert(row - 1, buttons.pop(row))
            
            # Save the new configuration
            config = {'buttons': buttons}
            with open(self.parent.buttons_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            
            # Reload the entire table to reflect changes
            self.load_buttons_to_table()
            
            # Select the moved row
            self.buttons_table.selectRow(row - 1)

    def move_button_down(self, row):
        """Move button down one row"""
        if row < self.buttons_table.rowCount() - 1:
            # First get all button configurations
            buttons = []
            for i in range(self.buttons_table.rowCount()):
                buttons.append(self.get_row_data(i))
            
            # Move the button down in the list
            buttons.insert(row + 1, buttons.pop(row))
            
            # Save the new configuration
            config = {'buttons': buttons}
            with open(self.parent.buttons_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            
            # Reload the entire table to reflect changes
            self.load_buttons_to_table()
            
            # Select the moved row
            self.buttons_table.selectRow(row + 1)

    def delete_button(self, row):
        """Delete button from the specified row"""
        if QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this button?"
        ) == QMessageBox.StandardButton.Yes:
            self.buttons_table.removeRow(row)

    def save_buttons(self):
        """Save buttons configuration to file"""
        buttons = []
        for row in range(self.buttons_table.rowCount()):
            button = {
                'name': self.buttons_table.item(row, 0).text(),
                'icon': self.buttons_table.item(row, 1).text(),
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
        new_settings = {
            "dock_position": self.pos_combo.currentText(),
            "transparency": self.trans_slider.value(),
            "dock_color": self.parent.dock_color,
            "corner_radius": self.radius_spin.value(),
            "dock_size": {
                "width": self.width_spin.value(),
                "height": self.height_spin.value()
            }
        }
        self.parent.apply_settings(new_settings)
        
        # Reload dock buttons to reflect new order
        self.parent.load_buttons()
        
        self.close()

class DockButton(QToolButton):
    """Custom button class for the dock with hover animations and tooltips.
    
    Features:
    - Hover animations with zoom effect
    - Custom styling with transparent background
    - Fallback handling for fonts and icons
    - Configurable tooltips and actions
    """
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self._iconSize = QSize(32, 32)  # Initial icon size
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
                self.setIconSize(QSize(32, 32))  # Increased icon size to 32x32
                self.setText('')  # Clear text when using icon
            else:
                self.setText('•')  # Fallback to dot if no icon
            
            self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            self.setFixedSize(48, 48)  # Increased button size to accommodate larger icon
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
            self.setFont(QFont('Arial', 14))
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
        self.setIconSize(self._iconSize)
        
    def enterEvent(self, event):
        super().enterEvent(event)
        # Stop any running animations
        self.zoom_animation.stop()
        # Only zoom the icon, not the button
        self.zoom_animation.setStartValue(self._iconSize)
        self.zoom_animation.setEndValue(QSize(40, 40))  # Increase icon size to 40x40 on hover
        self.zoom_animation.start()
        
    def leaveEvent(self, event):
        super().leaveEvent(event)
        # Stop any running animations
        self.zoom_animation.stop()
        # Return icon to original size
        self.zoom_animation.setStartValue(self._iconSize)
        self.zoom_animation.setEndValue(QSize(32, 32))  # Return to default 32x32 size
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
        
        # Add settings button with the same style as other buttons
        settings_config = {
            'name': 'Settings',
            'icon': '',  # No icon, using text
        }
        self.settings_btn = DockButton(settings_config, self)
        self.settings_btn.setText("⚙")
        self.settings_btn.setFont(QFont('Arial', 20))
        self.settings_btn.clicked.connect(self.show_settings)
        self.main_layout.addWidget(self.settings_btn, alignment=Qt.AlignmentFlag.AlignCenter)
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
        self.size = settings['dock_size']['width']
        self.dock_height = settings['dock_size']['height']
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
            "dock_size": {
                "width": 50,                 # Default button width
                "height": 300                # Initial dock height
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
            
            if hasattr(self, 'settings_btn'):
                self.main_layout.removeWidget(self.settings_btn)
            
            # Load and create regular buttons
            with open(self.buttons_file, 'r', encoding='utf-8-sig') as f:
                config = json.load(f)
                for button_config in config.get('buttons', []):
                    button = DockButton(button_config, self)
                    button.clicked.connect(lambda checked, b=button_config: self.handle_button_click(b))
                    self.main_layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
                    self.buttons.append(button)
            
            # Always add settings button last
            if hasattr(self, 'settings_btn'):
                self.main_layout.addWidget(self.settings_btn, alignment=Qt.AlignmentFlag.AlignCenter)
                    
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load buttons: {str(e)}")
            
    def handle_button_click(self, button_config):
        """Handle button clicks by executing the specified command or opening URLs."""
        try:
            action = button_config.get('action', '').strip()
            if action:
                # Check if the action is a URL
                if action.startswith(('http://', 'https://', 'www.')):
                    # Open URLs in default browser
                    webbrowser.open(action)
                else:
                    # Run other commands in a non-blocking way
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
        old_edge = self.edge
        self.edge = settings['dock_position']
        self.transparency = settings['transparency']
        self.dock_color = settings['dock_color']
        self.size = settings['dock_size']['width']
        self.dock_height = settings['dock_size']['height']
        
        # If position changed, update layout
        if old_edge != self.edge:
            self.setup_layout()
            # Re-add buttons in the new layout
            for button in self.buttons:
                self.main_layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
            if hasattr(self, 'settings_btn'):
                self.main_layout.addWidget(self.settings_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
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
        painter.drawRoundedRect(self.rect(), self.corner_radius, self.corner_radius)
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
