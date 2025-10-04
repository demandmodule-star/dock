# Dynamic Dock Widget

A customizable, auto-hiding dock widget built with PyQt6 that provides a sleek and configurable interface for your desktop.

## Features

- 🔄 Auto-hiding dock with smooth animations
- 📍 Multiple dock positions (Left, Right, Top, Bottom)
- 🎨 Customizable appearance:
  - Adjustable transparency
  - Custom color picker
  - Dynamic sizing based on content
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

Run the dock application:
```bash
python dock.py
```

### Controls

- Hover over the screen edge to reveal the dock
- Click the ⚙️ (gear) icon to open settings
- Use the settings dialog to customize:
  - Dock position on screen
  - Background transparency
  - Dock color
  - Size preferences

### Settings

All settings are automatically saved to `settings.json` and persisted between sessions. Default settings are created on first run.

## Development

The dock is designed to be extensible. The main components are:
- `DockWindow`: Main dock widget with auto-hide functionality
- `SettingsDialog`: Configuration interface
- Settings persistence layer with JSON storage

## License

MIT License