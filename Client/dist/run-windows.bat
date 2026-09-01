@echo off
setlocal
cd /d "%~dp0"
set "JAR=TerminalClient.jar"
if not exist "%JAR%" set "JAR=TerminalClient-windows.jar"

echo Uruchamianie Terminal Gateway Client...
java --enable-native-access=ALL-UNNAMED -jar "%JAR%" %*
