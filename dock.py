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
- Support for custom icons, actions, and tooltips
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
import urllib.request
import urllib.error
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QDialog, QVBoxLayout, QHBoxLayout,
    QComboBox, QSlider, QSpinBox, QColorDialog, QMessageBox, QLabel,
    QToolButton, QSizePolicy, QTabWidget, QTableWidget, QTableWidgetItem, QButtonGroup,
    QHeaderView, QFileDialog, QLineEdit
)
from PyQt6.QtCore import Qt, QTimer, QRect, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtCore import pyqtSignal, QThread
from PyQt6.QtGui import QPainter, QColor, QIcon, QFont, QPen
from packaging.version import parse as parse_version

# Application version
__version__ = "0.0.0-placeholder"
UPDATE_URL = "https://api.github.com/repos/demandmodule-star/dock/releases/latest"
# Dock position constants
EDGE_TOP = 'top'
EDGE_BOTTOM = 'bottom'
EDGE_LEFT = 'left'
EDGE_RIGHT = 'right'

# File constants
SETTINGS_FILE = "settings.json"
BUTTONS_FILE = "buttons.json"

SHOW_TRIGGER_DISTANCE = 20  # Distance from edge to trigger show

class UpdateCheckThread(QThread):
    """Worker thread to check for updates without blocking the GUI."""
    finished = pyqtSignal(dict)

    def run(self):
        """Fetch and compare version info from the remote server."""
        result = {'update_available': False, 'latest_version': '', 'download_url': ''}
        try:
            # Use urllib to avoid adding new dependencies like requests
            # The GitHub API requires a User-Agent header.
            req = urllib.request.Request(UPDATE_URL, headers={'User-Agent': 'DynamicDockWidget-Update-Checker'})
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    # The version is in the 'tag_name', which might have a 'v' prefix.
                    latest_version_str = data.get('tag_name', '').lstrip('v')
                    # The download URL is the main release page.
                    download_url = data.get('html_url')

                    if latest_version_str:
                        local_version = parse_version(__version__)
                        latest_version = parse_version(latest_version_str)

                        if latest_version > local_version:
                            result['update_available'] = True
                            result['latest_version'] = latest_version_str
                            result['download_url'] = download_url
                    else:
                        print("Update check: 'tag_name' not found in API response.")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # This is expected if no releases are published yet.
                print("Update check: No releases found (404). This is normal for a new project.")
            else:
                print(f"Update check failed with HTTP error: {e}")
        except Exception as e:
            # Silently fail on network errors, timeout, etc.
            # The UI will just show that it's up-to-date.
            print(f"Update check failed: {e}")
        finally:
            self.finished.emit(result)


class SettingsDialog(QDialog):
    """Settings dialog for configuring dock appearance and behavior.
    
    Provides controls for:
    - Dock position selection
    - Transparency adjustment
    - Color selection
    - Size configuration
    """
    
    settings_applied = pyqtSignal(dict)

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
        self._setup_customization_tab()
        self.setup_buttons_tab()
        self._setup_info_tab()
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

    def _setup_info_tab(self):
        """Setup the info tab with application details."""
        from PyQt6.QtWidgets import QFormLayout, QFrame, QScrollArea

        info_tab = QWidget()
        tab_layout = QVBoxLayout(info_tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Create a scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        tab_layout.addWidget(scroll_area)

        # Container for all content inside the scroll area
        scroll_content_widget = QWidget()
        scroll_area.setWidget(scroll_content_widget)

        # Main layout for the scrollable content
        main_layout = QVBoxLayout(scroll_content_widget)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Frame for the central content block
        content_frame = QFrame()
        content_frame.setObjectName("infoFrame")
        content_frame.setFixedWidth(650)
        frame_layout = QVBoxLayout(content_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(15)
        frame_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # App Icon
        icon_label = QLabel()
        icon_label.setPixmap(QIcon("app.ico").pixmap(64, 64))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        frame_layout.addWidget(icon_label)

        # Title and Version
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label = QLabel("Dynamic Dock Widget")
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        frame_layout.addWidget(title_label)

        version_label = QLabel(f"Version {__version__}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        frame_layout.addWidget(version_label)
        
        # Update status section
        self.update_status_label = QLabel("Checking for updates...")
        self.update_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_status_label.setStyleSheet("color: #888;")
        frame_layout.addWidget(self.update_status_label)

        self.download_button = QPushButton("Download Update")
        self.download_button.setFixedWidth(150)
        self.download_button.setVisible(False) # Initially hidden
        self.download_button.clicked.connect(self.open_download_page)
        download_layout = QHBoxLayout()
        download_layout.addStretch()
        download_layout.addWidget(self.download_button)
        download_layout.addStretch()
        frame_layout.addLayout(download_layout)

        frame_layout.addSpacing(15)

        # Description
        desc_text = "A customizable, auto-hiding dock widget. It provides a sleek, modern, and highly configurable interface for your desktop."
        desc_label = QLabel(desc_text)
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        frame_layout.addWidget(desc_label)

        frame_layout.addSpacing(15)

        # Details Section
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        author_label = QLabel("Demand Module")
        form_layout.addRow("<b>Author:</b>", author_label)

        license_label = QLabel("MIT License")
        form_layout.addRow("<b>License:</b>", license_label)

        repo_label = QLabel("<a href='https://github.com/demandmodule-star/dock'>https://github.com/demandmodule-star/dock</a>")
        repo_label.setOpenExternalLinks(True)
        form_layout.addRow("<b>Repository:</b>", repo_label)
        frame_layout.addLayout(form_layout)

        frame_layout.addStretch() # Pushes the quit button to the bottom

        # Quit Button
        quit_btn = QPushButton("Quit Application")
        quit_btn.setFixedWidth(150)
        # Use a lambda to call QApplication.quit directly
        quit_btn.clicked.connect(lambda: QApplication.quit())
        quit_btn_layout = QHBoxLayout()
        quit_btn_layout.addStretch()
        quit_btn_layout.addWidget(quit_btn)
        quit_btn_layout.addStretch()
        frame_layout.addLayout(quit_btn_layout)

        main_layout.addWidget(content_frame)
        self.tab_widget.addTab(info_tab, "Info")
        
        # Start update check when the dialog is opened
        self.check_for_updates()

    def check_for_updates(self):
        """Initiates the background thread to check for updates."""
        self.update_checker = UpdateCheckThread()
        self.update_checker.finished.connect(self.on_update_check_finished)
        self.update_checker.start()

    def on_update_check_finished(self, result):
        """Handles the result from the update check thread."""
        if result.get('update_available'):
            self.update_status_label.setText(f"Update available: <b>v{result['latest_version']}</b>")
            self.update_status_label.setStyleSheet("color: #3daee9;") # A nice blue color
            self.download_url = result['download_url']
            self.download_button.setVisible(True)
        else:
            self.update_status_label.setText("You are up-to-date!")
            self.update_status_label.setStyleSheet("color: #2ecc71;") # A nice green color

    def open_download_page(self):
        """Opens the download URL in the user's default web browser."""
        if hasattr(self, 'download_url') and self.download_url:
            webbrowser.open(self.download_url)

    def _setup_customization_tab(self):
        """Setup the customization tab with appearance settings"""
        from PyQt6.QtWidgets import QFormLayout, QLabel, QScrollArea

        customization_tab = QWidget()
        # Main layout for the tab, which will hold the scroll area
        tab_layout = QVBoxLayout(customization_tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)

        # Create a scroll area to make the content scrollable
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        tab_layout.addWidget(scroll_area)

        # Create a container widget for the scroll area's content
        scroll_content_widget = QWidget()
        scroll_area.setWidget(scroll_content_widget)

        # This layout will hold all the settings sections inside the scrollable widget
        main_layout = QVBoxLayout(scroll_content_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- Position & Sizing Section ---
        position_heading = QLabel("<b>Position & Sizing</b>")
        font = position_heading.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        position_heading.setFont(font)
        main_layout.addWidget(position_heading)

        position_form_layout = QFormLayout()
        position_form_layout.setSpacing(10)
        position_form_layout.addRow("Dock Position:", self._create_position_controls())
        self.offset_slider, self.offset_label = self._create_slider_control(position_form_layout, "Dock Offset:", 0, 100, self.parent.dock_offset, "px")
        main_layout.addLayout(position_form_layout)

        main_layout.addSpacing(20) # Visual separator between sections

        # --- Appearance Section ---
        appearance_heading = QLabel("<b>Appearance</b>")
        appearance_heading.setFont(font)
        main_layout.addWidget(appearance_heading)

        appearance_form_layout = QFormLayout()
        appearance_form_layout.setSpacing(10)
        appearance_form_layout.addRow("Dock Color:", self._create_color_picker())
        self.trans_slider, self.trans_label = self._create_slider_control(appearance_form_layout, "Transparency:", 0, 100, self.parent.transparency, "%")
        self.radius_slider, self.radius_label = self._create_slider_control(appearance_form_layout, "Corner Radius:", 0, 50, self.parent.corner_radius, "px")
        appearance_form_layout.addRow("Border Color:", self._create_border_color_picker())
        self.border_width_slider, self.border_width_label = self._create_slider_control(appearance_form_layout, "Border Width:", 0, 10, self.parent.border_width, "px", scale=2)
        main_layout.addLayout(appearance_form_layout)

        main_layout.addSpacing(20)

        # --- Content Section ---
        content_heading = QLabel("<b>Content</b>")
        content_heading.setFont(font)
        main_layout.addWidget(content_heading)

        content_form_layout = QFormLayout()
        content_form_layout.setSpacing(10)
        self.icon_size_slider, self.icon_size_label = self._create_slider_control(content_form_layout, "Icon Size:", 16, 64, self.parent.icon_size, "px")
        self.spacing_slider, self.spacing_label = self._create_slider_control(content_form_layout, "Layout Spacing:", 0, 30, self.parent.layout_spacing, "px")
        main_layout.addLayout(content_form_layout)
        
        self.tab_widget.addTab(customization_tab, "Customization")

    def _create_position_controls(self):
        pos_widget = QWidget()
        pos_layout = QHBoxLayout(pos_widget)
        pos_layout.setContentsMargins(0, 0, 0, 0)
        self.pos_button_group = QButtonGroup(self)
        self.pos_button_group.setExclusive(True)
        positions = {EDGE_LEFT: "Left", EDGE_RIGHT: "Right", EDGE_TOP: "Top", EDGE_BOTTOM: "Bottom"}
        for i, (edge, text) in enumerate(positions.items()):
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setFixedWidth(70)
            if self.parent.edge == edge:
                btn.setChecked(True)
            self.pos_button_group.addButton(btn, id=i)
            pos_layout.addWidget(btn)
        pos_layout.addStretch()
        return pos_widget

    def _create_slider_control(self, layout, label_text, min_val, max_val, current_val, suffix="", scale=1):
        widget = QWidget()
        h_layout = QHBoxLayout(widget)
        h_layout.setContentsMargins(0, 0, 0, 0)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMaximumWidth(300)
        slider.setRange(min_val * scale, max_val * scale)
        slider.setValue(int(current_val * scale))
        
        # Format label text to show float if scale is not 1, otherwise int
        label_text_format = "{:.1f}" if scale != 1 else "{:d}"
        label = QLabel(f"{label_text_format.format(current_val)}{suffix}")
        label.setFixedWidth(40)

        def update_label(value):
            display_value = value / scale
            # If the format is for an integer ('d'), we must cast the display_value
            # to an int first to prevent the ValueError.
            if 'd' in label_text_format:
                display_value = int(display_value)
            
            label.setText(f"{label_text_format.format(display_value)}{suffix}")

        slider.valueChanged.connect(update_label)
        h_layout.addWidget(slider)
        h_layout.addWidget(label)
        h_layout.addStretch()
        layout.addRow(label_text, widget)
        return slider, label

    def _create_color_picker(self):
        self.color_button = QPushButton()
        self.color_button.setFixedSize(50, 25)
        self._update_color_button(self.parent.dock_color)
        self.color_button.clicked.connect(self._choose_color)
        color_widget = QWidget()
        color_layout = QHBoxLayout(color_widget)
        color_layout.setContentsMargins(0, 0, 0, 0)
        color_layout.addWidget(self.color_button, alignment=Qt.AlignmentFlag.AlignLeft)
        return color_widget

    def _create_border_color_picker(self):
        self.border_color_button = QPushButton()
        self.border_color_button.setFixedSize(50, 25)
        self._update_border_color_button(self.parent.border_color)
        self.border_color_button.clicked.connect(self._choose_border_color)
        border_color_widget = QWidget()
        border_color_layout = QHBoxLayout(border_color_widget)
        border_color_layout.setContentsMargins(0, 0, 0, 0)
        border_color_layout.addWidget(self.border_color_button, alignment=Qt.AlignmentFlag.AlignLeft)
        return border_color_widget

    def _update_border_color_button(self, color):
        self.border_color_button.setStyleSheet(f"background-color: {color}; border: 1px solid #888;")

    def _update_color_button(self, color):
        self.color_button.setStyleSheet(f"background-color: {color}; border: 1px solid #888;")

    def _choose_color(self):
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
                self._update_color_button(color.name())

    def _choose_border_color(self):
        color_dialog = QColorDialog(QColor(self.parent.border_color), self)
        color_dialog.setWindowFlags(
            color_dialog.windowFlags() |
            Qt.WindowType.WindowStaysOnTopHint
        )
        color_dialog.setCurrentColor(QColor(self.parent.border_color))
        
        if color_dialog.exec() == QColorDialog.DialogCode.Accepted:
            color = color_dialog.currentColor()
            if color.isValid():
                self.parent.border_color = color.name()
                self._update_border_color_button(color.name())

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
            with open(BUTTONS_FILE, 'r', encoding='utf-8-sig') as f:
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
            "corner_radius": self.radius_slider.value(),
            "dock_color": self.parent.dock_color,
            "icon_size": self.icon_size_slider.value(),
            "layout_spacing": self.spacing_slider.value(),
            "dock_offset": self.offset_slider.value(),
            "border_width": self.border_width_slider.value() / 2.0, # Divide by scale
            "border_color": self.parent.border_color,
        }
        self.settings_applied.emit(new_settings)

    def apply_and_close_settings(self):
        """Apply settings and close the dialog."""
        self.apply_settings()
        self.close()

class DockButton(QToolButton):
    """Custom button class for the dock with hover animations and tooltips.
    
    Features:
    - Custom styling with transparent background
    - Fallback handling for fonts and icons
    - Configurable tooltips and actions
    """
    
    def __init__(self, config, initial_icon_size=QSize(32, 32), parent=None):
        super().__init__(parent)
        self.config = config
        self.setup_button()
        self.setIconSize(initial_icon_size)
        
    def setup_button(self):
        try:
            # Set button properties
            name = self.config.get('name', '')
            self.setToolTip(name)  # Use name as tooltip
            
            # Handle icon
            icon_path = self.config.get('icon', '')
            if (name == 'Settings' or (icon_path and Path(icon_path).exists())):  # An icon path is specified
                self.setIcon(QIcon(icon_path))
            else:
                # Fallback to app icon if icon path is invalid
                self.setIcon(QIcon("app.ico"))
            self.setText('')
            
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
                padding: 2px;
            }
            QToolButton:pressed {
                background-color: transparent;
            }
        """)

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
        self.settings_file = Path(SETTINGS_FILE)
        self.buttons_file = Path(BUTTONS_FILE)
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
            if self.settings_file.exists():
                with self.settings_file.open('r') as f:
                    settings = json.load(f)
            else:
                settings = self.get_default_settings()
                self.save_settings(settings)
        except (json.JSONDecodeError, IOError):
            settings = self.get_default_settings()
            self.save_settings(settings)

        self.edge = settings['dock_position']
        self.transparency = settings['transparency']
        self.dock_color = settings['dock_color']
        self.corner_radius = settings.get('corner_radius', 16)  # Default to 16 if not set
        self.icon_size = settings.get('icon_size', 32) # Default to 32 if not set
        self.layout_spacing = settings.get('layout_spacing', 5)
        self.dock_offset = settings.get('dock_offset', 10)
        self.border_width = settings.get('border_width', 1)
        self.border_color = settings.get('border_color', "#FFFFFF")

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
            "corner_radius": 16,             # Rounded corners
            "dock_color": "#000000",         # Black background
            "icon_size": 32,                 # Default icon size
            "layout_spacing": 5,             # Default space between icons
            "dock_offset": 10,               # Default distance from screen edge
            "border_width": 1,               # Default border width
            "border_color": "#FFFFFF",       # Default border color
        }

    def save_settings(self, settings):
        try:
            with self.settings_file.open('w') as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save settings: {str(e)}")

    def show_settings(self):
        self.settings_dialog_open = True
        if self.is_hidden:
            self.start_show_animation()
        dialog = SettingsDialog(self)
        dialog.settings_applied.connect(self.apply_settings)
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
                    "name": "Google",
                    "icon": "icons/google.png",
                    "action": "https://www.google.com"
                }
            ]
        }
        try:
            # Ensure the icons directory exists
            icons_dir = self.buttons_file.parent / "icons"
            icons_dir.mkdir(exist_ok=True)
            
            # Create the buttons configuration
            with self.buttons_file.open('w', encoding='utf-8') as f:
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
        if not self.buttons_file.exists():
            self.create_default_buttons_file()
        
        try:
            # First remove all existing buttons and the settings button
            for button in self.buttons:
                self.main_layout.removeWidget(button)
                button.deleteLater()
            self.buttons.clear()
            
            # Load and create regular buttons
            with self.buttons_file.open('r', encoding='utf-8-sig') as f:
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
                else:
                    # Expand environment variables for paths
                    expanded_action = os.path.expandvars(action)
                    action_path = Path(expanded_action)
                    if action_path.exists():
                        os.startfile(action_path)
                    else:
                        # Run other commands in a non-blocking way
                        # Split the command and arguments to avoid shell=True security issues
                        try:
                            subprocess.Popen(action.split(), shell=False)
                        except (FileNotFoundError, OSError):
                            # Fallback to shell=True for complex commands (e.g., with pipes)
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
        
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(self.layout_spacing)

    def apply_settings(self, settings):
        old_edge = self.edge
        self.edge = settings['dock_position']
        self.transparency = settings['transparency']
        self.corner_radius = settings.get('corner_radius', 16)
        self.dock_color = settings['dock_color']
        self.icon_size = settings.get('icon_size', 32)
        self.layout_spacing = settings.get('layout_spacing', 5)
        self.dock_offset = settings.get('dock_offset', 10)
        self.border_width = settings.get('border_width', 1)
        self.border_color = settings.get('border_color', "#FFFFFF")
        
        self.save_settings(settings)
        
        # If position changed, update layout
        if old_edge != self.edge:
            self.setup_layout()
        self.main_layout.setSpacing(self.layout_spacing)
        
        # Reload buttons to reflect new order and apply new icon size
        self.load_buttons()
        
        # Recreate the settings button to apply new size
        self.recreate_settings_button()
        
        # If position changed, we need to re-add all buttons to the new layout
        if old_edge != self.edge:
            # Add all buttons to the new layout
            for btn in self.buttons:
                self.main_layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
            self.main_layout.addWidget(self.settings_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # Force layout recalculation and update size
        self.main_layout.invalidate()
        self.update_size()
        
        # Reposition the dock
        self.place_dock()
        self.update()
        
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
        painter.setPen(Qt.PenStyle.NoPen) # Default to no border

        # Draw border only if width is greater than 0
        if self.border_width > 0:
            border_color = QColor(self.border_color)
            border_color.setAlpha(color.alpha()) # Match border transparency to background
            
            # Adjust the rectangle to ensure the border is drawn inside the widget bounds
            # Use int() to convert potential float to int for QRect.adjusted()
            adjustment = int(self.border_width / 2)
            painter.setPen(QPen(border_color, self.border_width))
            painter.drawRoundedRect(self.rect().adjusted(adjustment, adjustment, -adjustment, -adjustment), self.corner_radius, self.corner_radius)
        else:
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
        is_horizontal = self.edge in [EDGE_TOP, EDGE_BOTTOM]
        
        x = (screen.width() - self.width()) // 2 if is_horizontal else (self.dock_offset if self.edge == EDGE_LEFT else screen.width() - self.width() - self.dock_offset)
        y = (screen.height() - self.height()) // 2 if not is_horizontal else (self.dock_offset if self.edge == EDGE_TOP else screen.height() - self.height() - self.dock_offset)
        
        self.move(x, y)
        
    def enterEvent(self, event):
        """Show the dock when the mouse enters its area."""
        self.hide_timer.stop()
        if self.is_hidden:
            self.start_show_animation()

    def leaveEvent(self, event):
        self.hide_timer.start(500)  # Start hide timer with 500ms delay

    def start_hide_animation(self):
        """Animate the dock to its hidden position."""
        if not self.is_hidden and not self.settings_dialog_open:
            self.is_hidden = True
            target_geometry = self.get_hidden_geometry()
            self.animation.setStartValue(self.geometry())
            self.animation.setEndValue(target_geometry)
            self.animation.start()

    def start_show_animation(self):
        """Animate the dock to its visible position."""
        if self.is_hidden:
            self.is_hidden = False
            target_geometry = self.get_visible_geometry()
            self.animation.setStartValue(self.geometry())
            self.animation.setEndValue(target_geometry)
            self.animation.start()

    def get_hidden_geometry(self):
        """Calculate the geometry for the dock when it's hidden."""
        current = self.geometry()
        screen = QApplication.primaryScreen().geometry()
        x, y = current.x(), current.y()
        
        if self.edge == EDGE_LEFT: x = -self.width() + 5
        elif self.edge == EDGE_RIGHT: x = screen.width() - 5
        elif self.edge == EDGE_TOP: y = -self.height() + 5
        elif self.edge == EDGE_BOTTOM: y = screen.height() - 5
            
        return QRect(x, y, current.width(), current.height())

    def get_visible_geometry(self):
        """Calculate the geometry for the dock when it's visible."""
        screen = QApplication.primaryScreen().geometry()
        is_horizontal = self.edge in [EDGE_TOP, EDGE_BOTTOM]
        
        x = (screen.width() - self.width()) // 2 if is_horizontal else (self.dock_offset if self.edge == EDGE_LEFT else screen.width() - self.width() - self.dock_offset)
        y = (screen.height() - self.height()) // 2 if not is_horizontal else (self.dock_offset if self.edge == EDGE_TOP else screen.height() - self.height() - self.dock_offset)
        
        return QRect(x, y, self.width(), self.height())


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
