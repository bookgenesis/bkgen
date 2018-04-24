@echo off
echo "Setting up the Python environment (requires Python 3)"
cd %~dp0
pip install virtualenv
start /b /wait cmd /C "python -m virtualenv _bkgen"
UPDATE.bat
echo "Installation complete." 
