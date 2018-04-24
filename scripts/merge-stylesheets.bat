@echo off
%~dp0\..\_bkgen\Scripts\activate.bat
python -m bkgen.project merge-stylesheet "%1"