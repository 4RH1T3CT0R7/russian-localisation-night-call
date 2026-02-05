@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo  Night Call Russian - Build
echo ========================================
echo.

REM Parse argument
set BUILD_INSTALLER=0
if /i "%1"=="--installer" set BUILD_INSTALLER=1
if /i "%1"=="-i" set BUILD_INSTALLER=1

REM Build mod DLL
echo Building RussianLocalization.dll...
"C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe" ^
  /target:library ^
  /out:"%~dp0bin\RussianLocalization.dll" ^
  /reference:"%~dp0data\BepInEx\core\BepInEx.dll" ^
  /reference:"%~dp0data\BepInEx\core\0Harmony.dll" ^
  /reference:"F:\SteamLibrary\steamapps\common\Night Call\Night Call_Data\Managed\UnityEngine.dll" ^
  /reference:"F:\SteamLibrary\steamapps\common\Night Call\Night Call_Data\Managed\UnityEngine.CoreModule.dll" ^
  /reference:"F:\SteamLibrary\steamapps\common\Night Call\Night Call_Data\Managed\UnityEngine.UI.dll" ^
  /reference:"F:\SteamLibrary\steamapps\common\Night Call\Night Call_Data\Managed\UnityEngine.TextRenderingModule.dll" ^
  /reference:"F:\SteamLibrary\steamapps\common\Night Call\Night Call_Data\Managed\UnityEngine.IMGUIModule.dll" ^
  /reference:"F:\SteamLibrary\steamapps\common\Night Call\Night Call_Data\Managed\TextMeshPro-2017.3-1.0.56-Runtime.dll" ^
  /reference:"F:\SteamLibrary\steamapps\common\Night Call\Night Call_Data\Managed\Assembly-CSharp.dll" ^
  /reference:"F:\SteamLibrary\steamapps\common\Night Call\Night Call_Data\Managed\UnityEngine.ImageConversionModule.dll" ^
  /reference:"F:\SteamLibrary\steamapps\common\Night Call\Night Call_Data\Managed\UnityEngine.AssetBundleModule.dll" ^
  /langversion:5 ^
  /nowarn:0618 ^
  "%~dp0src\Mod\RussianLocalization.cs"
if %errorlevel% neq 0 (
    echo [FAIL] DLL build failed
    pause
    exit /b 1
)
echo [OK] DLL built: %~dp0bin\RussianLocalization.dll
echo.

REM Build installer if requested
if %BUILD_INSTALLER%==1 (
    echo Building installer...
    python "%~dp0set_version.py" --increment
    if %errorlevel% neq 0 (
        echo [FAIL] Version increment failed
        pause
        exit /b 1
    )

    dotnet build "%~dp0src\Installer\Installer.csproj" -c Release
    if %errorlevel% neq 0 (
        echo [FAIL] Installer build failed
        pause
        exit /b 1
    )

    for /f %%v in ('python "%~dp0set_version.py"') do set VER=%%v
    echo [OK] Installer built: v!VER!
    echo      %~dp0src\Installer\bin\Release\net472\NightCallRussian-Setup.exe
)

echo.
echo BUILD SUCCEEDED
pause
