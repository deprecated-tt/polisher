@echo off
echo Building Polisher executable...
echo.

REM Activate virtual environment
call .venv\Scripts\activate

REM Build with PyInstaller
pyinstaller --onefile --windowed --name "Polisher" --add-data "config.py;." --manifest "Polisher.manifest" --uac-admin --hidden-import=pystray._win32 --hidden-import=PIL._tkinter_finder main.py

echo.
echo Build complete! Check the 'dist' folder for Polisher.exe
echo.
echo The executable will automatically request Administrator privileges when run.
pause
