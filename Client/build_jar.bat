@echo off
setlocal
cd /d "%~dp0"
echo Buduje projekt Maven (pomin testy)...
call mvnw.cmd -DskipTests package

if not exist target\TerminalClient.jar (
    echo Nie znaleziono pliku JAR w target\
    exit /b 1
)

if not exist dist mkdir dist
copy /y target\TerminalClient.jar dist\TerminalClient.jar

echo Gotowe! Wygenerowano plik: dist\TerminalClient.jar
echo Aby uruchomic: java -jar dist\TerminalClient.jar
