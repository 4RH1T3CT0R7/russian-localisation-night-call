@echo off
echo ========================================
echo  Night Call Russian - Build Installer
echo ========================================
echo.

REM Increment version
python "%~dp0set_version.py" --increment
if %errorlevel% neq 0 (
    echo [FAIL] Version increment failed
    pause
    exit /b 1
)
echo.

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
echo [OK] DLL built
echo.

REM Build installer EXE
echo Building NightCallRussian-Setup.exe...
dotnet build "%~dp0src\Installer\Installer.csproj" -c Release
if %errorlevel% neq 0 (
    echo [FAIL] Installer build failed
    pause
    exit /b 1
)
echo.

echo ========================================
for /f %%v in ('python "%~dp0set_version.py"') do set VER=%%v
echo  BUILD SUCCEEDED - v%VER%
echo  DLL: %~dp0bin\RussianLocalization.dll
echo  EXE: %~dp0src\Installer\bin\Release\net472\NightCallRussian-Setup.exe
echo ========================================
echo.
pause
