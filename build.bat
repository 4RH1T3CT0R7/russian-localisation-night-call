@echo off
chcp 65001 >nul
setlocal

echo ============================================================
echo   Night Call Russian Localization - Build Script
echo ============================================================
echo.

set REPO_DIR=%~dp0
set DATA_DIR=%REPO_DIR%data
set MOD_SRC=%REPO_DIR%src\Mod
set INSTALLER_SRC=%REPO_DIR%src\Installer
set GAME_DIR=F:\SteamLibrary\steamapps\common\Night Call

:: Check game directory exists
if not exist "%GAME_DIR%\Night Call.exe" (
    echo [!] Папка игры не найдена: %GAME_DIR%
    echo     Измените переменную GAME_DIR в этом скрипте.
    goto :error
)

:: ---- Step 1: Build Mod DLL ----
echo [1/5] Сборка мода...
dotnet build "%MOD_SRC%" -c Release -p:GameDir="%GAME_DIR%"
if errorlevel 1 (
    echo [!] Сборка мода не удалась!
    goto :error
)
echo      OK
echo.

:: ---- Step 2: Copy DLL to repo data ----
echo [2/5] Обновление DLL в репозитории...
copy /Y "%MOD_SRC%\bin\Release\net46\NightCallRussian.dll" "%DATA_DIR%\BepInEx\plugins\" >nul 2>&1
echo      OK
echo.

:: ---- Step 3: Sync to game ----
echo [3/5] Синхронизация: репозиторий -^> папка игры...
robocopy "%DATA_DIR%\BepInEx" "%GAME_DIR%\BepInEx" /E /NFL /NDL /NJH /NJS /NP >nul
robocopy "%DATA_DIR%\Russian_UI" "%GAME_DIR%\Russian_UI" /E /NFL /NDL /NJH /NJS /NP >nul
robocopy "%DATA_DIR%\Russian_Texts" "%GAME_DIR%\Russian_Texts" /E /NFL /NDL /NJH /NJS /NP >nul
robocopy "%DATA_DIR%\Generated_SDF" "%GAME_DIR%\Generated_SDF" /E /NFL /NDL /NJH /NJS /NP >nul
robocopy "%DATA_DIR%\Fonts_Cyrillic" "%GAME_DIR%\Fonts_Cyrillic" /E /NFL /NDL /NJH /NJS /NP >nul
copy /Y "%DATA_DIR%\winhttp.dll" "%GAME_DIR%\" >nul 2>&1
copy /Y "%DATA_DIR%\doorstop_config.ini" "%GAME_DIR%\" >nul 2>&1
copy /Y "%DATA_DIR%\passage_dump.txt" "%GAME_DIR%\" >nul 2>&1
echo      OK
echo.

:: ---- Step 4: Package data.zip ----
echo [4/5] Упаковка data.zip...
if exist "%INSTALLER_SRC%\data.zip" del "%INSTALLER_SRC%\data.zip"
%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -Command "Compress-Archive -Path '%DATA_DIR%\*' -DestinationPath '%INSTALLER_SRC%\data.zip' -Force"
if errorlevel 1 (
    echo [!] Не удалось создать data.zip!
    goto :error
)
echo      OK
echo.

:: ---- Step 5: Build Installer ----
echo [5/5] Сборка установщика...
dotnet publish "%INSTALLER_SRC%" -c Release
if errorlevel 1 (
    echo [!] Сборка установщика не удалась!
    goto :error
)
copy /Y "%INSTALLER_SRC%\bin\Release\net472\publish\NightCallRussian-Setup.exe" "%REPO_DIR%" >nul 2>&1
echo      OK
echo.

echo ============================================================
echo   Готово!
echo ============================================================
echo.
echo   Мод DLL:    %MOD_SRC%\bin\Release\net46\NightCallRussian.dll
echo   Установщик: %REPO_DIR%NightCallRussian-Setup.exe
echo   Игра:       синхронизирована (%GAME_DIR%)
echo.
goto :end

:error
echo.
echo Сборка прервана из-за ошибки.
echo.

:end
pause
