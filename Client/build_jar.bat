@echo off
setlocal
cd /d "%~dp0"

echo ==========================================================
echo   Budowanie Terminal Gateway Client (Windows)
echo ==========================================================

echo [1/3] Kompilacja i pakowanie Maven...
call mvnw.cmd -DskipTests package

if not exist target\TerminalClient.jar (
    echo BLAD: Nie znaleziono pliku JAR w target\
    exit /b 1
)

echo [2/3] Kopiowanie plikow do katalogu dist\...
if not exist dist mkdir dist
copy /y target\TerminalClient.jar dist\TerminalClient.jar
copy /y target\TerminalClient.jar dist\TerminalClient-windows.jar

echo [3/3] Tworzenie skryptow uruchomieniowych...

(
echo @echo off
echo setlocal
echo cd /d "%%~dp0"
echo set "JAR=TerminalClient.jar"
echo if not exist "%%JAR%%" set "JAR=TerminalClient-windows.jar"
echo echo Uruchamianie Terminal Gateway Client...
echo java --enable-native-access=ALL-UNNAMED -jar "%%JAR%%" %%*
) > dist\run-windows.bat

(
echo @echo off
echo setlocal
echo cd /d "%%~dp0"
echo set "JAR=TerminalClient.jar"
echo if not exist "%%JAR%%" set "JAR=TerminalClient-windows.jar"
echo start "" javaw --enable-native-access=ALL-UNNAMED -jar "%%JAR%%" %%*
) > dist\run-windows-gui.bat

echo ==========================================================
echo Gotowe! Wygenerowano pliki w katalogu dist\:
echo   - dist\TerminalClient.jar
echo   - dist\TerminalClient-windows.jar
echo   - dist\run-windows-gui.bat (uruchomienie 1-kliknieciem)
echo   - dist\run-windows.bat     (uruchomienie w konsoli)
echo ==========================================================

