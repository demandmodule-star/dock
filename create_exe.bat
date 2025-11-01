@echo off

echo Creating executable...
pyinstaller --noconfirm --onefile --windowed --icon=app.ico --clean dock.py

echo Copying executable to main folder...
copy /Y "dist\dock.exe" "dock.exe"

echo Cleaning up...
rmdir /S /Q build
rmdir /S /Q dist
del /Q dock.spec

echo Done! Executable created as dock.exe
pause