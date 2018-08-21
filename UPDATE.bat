@echo off
cd %~dp0
set pip=%~dp0_bkgen\Scripts\pip.exe
set python=%~dp0_bkgen\Scripts\python.exe
set LOG=%~dp0update.log
@echo on
echo "updating the repository..." >%LOG% 2>&1
git pull >>%LOG%
echo "updating the Python environment" >>%LOG% 2>&1
start /b /wait cmd /C "%pip% install -q -r requirements.txt" >>%LOG% 2>&1
start /b /wait cmd /C "%pip% uninstall -q bkgen -y" >>%LOG% 2>&1
start /b /wait cmd /C "%pip% install -q -e ." >>%LOG% 2>&1
