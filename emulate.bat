@echo off
echo Setze Umgebungsvariablen...
set INVERBIO_ENV=emu
echo Aktuelles ENV: %INVERBIO_ENV%

echo Kopiere agent\ nach functions\...
rmdir /s /q functions\agent
xcopy agent functions\agent /E /I /Y

echo Starte Firebase Emulator...
firebase emulators:start --only functions

pause