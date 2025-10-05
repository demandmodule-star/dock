# Dynamic Dock Widget

A customizable, auto-hiding dock widget built with PyQt6 that provides a sleek and configurable interface for your desktop. Launch your favorite applications and tools with style!

## Features

- 🔄 Auto-hiding dock with smooth animations
- 📍 Multiple dock positions (Left, Right, Top, Bottom)
- 🎨 Customizable appearance:
  - Adjustable transparency
  - Custom color picker
  - Dynamic sizing based on content
- 🚀 Dynamic button loading from configuration
- 🖼️ Custom icon support for buttons
- 💫 Hover animations and tooltips
- ⚙️ Persistent settings stored in JSON
- 🖱️ Easy-to-use settings dialog

## Requirements

- Python 3.6+
- PyQt6

## Installation

1. Ensure you have Python installed
2. Install the required dependency:
```bash
pip install PyQt6
```

## Usage

1. Run the dock application:
```bash
python dock.py
```

2. Configure buttons in `buttons.json`:
```json
{
    "buttons": [
        {
            "name": "File Explorer",
            "icon": "icons/folder.png",
            "action": "explorer ."
        },
        {
            "name": "Terminal",
            "icon": "icons/terminal.png",
            "action": "wt"
        }
    ]
}
```

### Controls

- Hover over the screen edge to reveal the dock
- Click buttons to launch applications or execute commands
- Click the ⚙️ (gear) icon to open settings
- Use the settings dialog to customize:
  - Dock position on screen
  - Background transparency
  - Dock color
  - Size preferences

### Button Configuration

Each button supports:
- `name`: Display name (shown in tooltip)
- `icon`: Path to PNG icon file
- `action`: Command to execute when clicked

### Settings

All settings are automatically saved and persisted between sessions:
- `settings.json`: Stores dock position, appearance, and size
- `buttons.json`: Stores button configurations
- Default configurations are created on first run

## Development

The dock is designed to be extensible. The main components are:
- `DockWindow`: Main dock widget with auto-hide functionality
- `DockButton`: Custom button implementation with animations
- `SettingsDialog`: Configuration interface
- Settings persistence layer with JSON storage

## License

MIT License