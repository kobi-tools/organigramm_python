@echo off
rem Baut den fertigen Programmordner: dist\Ordner-Organigramm
rem Danach reicht es, diesen Ordner zu kopieren. Python wird dort nicht gebraucht.
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Lege Build-Umgebung an ...
    py -m venv .venv || goto fehler
    ".venv\Scripts\python.exe" -m pip install --quiet pyinstaller || goto fehler
)

echo Baue Organigramm.exe ...
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --windowed --log-level=WARN ^
    --name Organigramm ^
    --icon "%~dp0organigramm.ico" ^
    --version-file "%~dp0version_info.txt" ^
    --add-data "%~dp0organigramm.ico;." ^
    --distpath "%~dp0dist" --workpath "%~dp0build" --specpath "%~dp0build" ^
    organigramm_gui.py || goto fehler

if exist "dist\Ordner-Organigramm" rmdir /s /q "dist\Ordner-Organigramm"
move "dist\Organigramm" "dist\Ordner-Organigramm" >nul || goto fehler
copy /y "LIESMICH.txt" "dist\Ordner-Organigramm\LIESMICH.txt" >nul || goto fehler
copy /y "LICENSE" "dist\Ordner-Organigramm\LICENSE.txt" >nul || goto fehler

rem Zeitzonen und Datumstexte von Tcl braucht das Programm nicht, das spart ueber 700 Dateien
rmdir /s /q "dist\Ordner-Organigramm\_internal\_tcl_data\tzdata"
rmdir /s /q "dist\Ordner-Organigramm\_internal\_tcl_data\msgs"

rem Zwischendateien vom Bauen aufraeumen
rmdir /s /q "build"
if exist "__pycache__" rmdir /s /q "__pycache__"

echo.
echo Fertig: %~dp0dist\Ordner-Organigramm
exit /b 0

:fehler
echo.
echo Das Bauen ist fehlgeschlagen.
exit /b 1
