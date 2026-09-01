@echo off
setlocal
cd /d "%~dp0"
set "JAR=TerminalClient.jar"
if not exist "%JAR%" set "JAR=TerminalClient-windows.jar"

start "" javaw --enable-native-access=ALL-UNNAMED -jar "%JAR%" %*
