@echo off
echo "updating the repository..."
git pull

echo "updating the Python environment"
cd %~dp0
set pip=%~dp0\_bkgen\Scripts\pip.exe
set python=%~dp0\_bkgen\Scripts\python.exe

start /b /wait cmd /C "%pip% install -r requirements.txt"
start /b /wait cmd /C "%pip% uninstall bkgen -y"
start /b /wait cmd /C "%pip% install -e ."

