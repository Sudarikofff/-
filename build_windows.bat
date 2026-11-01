@echo off
setlocal
cd /d "%~dp0"
py -3.12 -c "import sys, struct; sys.exit(0 if sys.version_info[:2] == (3, 12) and struct.calcsize('P') == 8 else 1)" >nul 2>&1
if errorlevel 1 (
    echo Python 3.12 64-bit is required, with Python Launcher and Tcl/Tk.
    echo Download: https://www.python.org/downloads/release/python-31210/
    echo Python 3.15 cannot build this project's pinned dependencies.
    pause
    exit /b 1
)
set "BUILD_PYTHON=.venv-build-py312\Scripts\python.exe"
if not exist "%BUILD_PYTHON%" (
    py -3.12 -m venv .venv-build-py312
    if errorlevel 1 goto :failed
)
"%BUILD_PYTHON%" -c "import sys, struct; sys.exit(0 if sys.version_info[:2] == (3, 12) and struct.calcsize('P') == 8 else 1)"
if errorlevel 1 (
    echo Invalid build environment. Rename .venv-build-py312 and run this script again.
    goto :failed
)
"%BUILD_PYTHON%" -m pip install --upgrade pip
if errorlevel 1 goto :failed
"%BUILD_PYTHON%" -m pip install --only-binary=Pillow -r requirements.txt pyinstaller
if errorlevel 1 goto :failed
"%BUILD_PYTHON%" -m unittest discover -s tests -q
if errorlevel 1 goto :failed
"%BUILD_PYTHON%" -m PyInstaller --noconfirm --clean --distpath windows-dist --workpath windows-build Discipline_PS_FSB.spec
if errorlevel 1 goto :failed
echo.
echo Ready: windows-dist\Discipline_PS_FSB\Discipline_PS_FSB.exe
echo Copy the ENTIRE Discipline_PS_FSB folder to the Windows computer.
pause
exit /b 0

:failed
echo.
echo Build failed. See the error above.
pause
exit /b 1
