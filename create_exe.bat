@echo off
setlocal

echo.
echo --- Building Executable ---
echo.

echo [1/3] Running PyInstaller to create dock.exe...
pyinstaller --noconfirm --onefile --windowed --icon=app.ico --clean dock.py

REM Check if build was successful
if not exist "dist\dock.exe" (
    echo [ERROR] PyInstaller failed to create dock.exe. Aborting.
    goto :end
)
echo Executable created in 'dist' folder.
echo.

echo [2/3] Copying dock.exe to project root...
copy /Y "dist\dock.exe" "dock.exe"
echo.

echo [3/3] Cleaning up build artifacts...
rmdir /S /Q build
rmdir /S /Q dist
del /Q dock.spec
echo Cleanup complete.
echo.

echo --- Build Finished ---
echo Executable 'dock.exe' is ready in the project root.
echo.

:end
pause