@echo off
echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.
echo Installation complete!
echo.
echo Don't forget to install Tesseract OCR:
echo https://github.com/UB-Mannheim/tesseract/wiki
echo.
pause
