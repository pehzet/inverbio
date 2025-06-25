@echo off
echo Setze Umgebungsvariablen...
set INVERBIO_ENV=prod
echo Aktuelles ENV: %INVERBIO_ENV%

echo Kopiere agent\ nach functions\...
rmdir /s /q functions\agent
xcopy agent functions\agent /E /I /Y

echo Starte Firebase Deployment...
firebase deploy --only functions

pause