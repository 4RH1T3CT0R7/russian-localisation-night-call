@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ========================================
echo  Night Call Russian - Commit and Release
echo ========================================
echo.

REM 1. Get latest tag and sync version.txt
for /f "tokens=*" %%t in ('git describe --tags --abbrev^=0 2^>nul') do set LATEST_TAG=%%t
if not defined LATEST_TAG (
    echo [WARN] No tags found, using version.txt as base
) else (
    set CURRENT_VER=!LATEST_TAG:v=!
    echo Current version: !CURRENT_VER! ^(from tag !LATEST_TAG!^)
    python set_version.py --set !CURRENT_VER!
)

REM 2. Increment version
python set_version.py --increment
if %errorlevel% neq 0 (
    echo [FAIL] Version increment failed
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python set_version.py') do set NEW_VER=%%v
echo New version: %NEW_VER%
echo.

REM 3. Rebuild mod with new version
echo Building NightCallRussian.dll...
dotnet build src\Mod\NightCallRussian.csproj -c Release
if %errorlevel% neq 0 (
    echo [FAIL] Build failed
    pause
    exit /b 1
)
echo [OK] Build succeeded
echo.

REM 4. Stage all changes
echo Staging files...
git add -A
git status --short
echo.

REM 5. Commit
echo Committing...
git commit -m "v%NEW_VER%"
if %errorlevel% neq 0 (
    echo [FAIL] Commit failed
    pause
    exit /b 1
)
echo.

REM 6. Push commit
echo Pushing to origin...
git push origin main
if %errorlevel% neq 0 (
    echo [FAIL] Push failed
    pause
    exit /b 1
)
echo.

REM 7. Create and push tag
echo Creating tag v%NEW_VER%...
git tag v%NEW_VER%
git push origin v%NEW_VER%
if %errorlevel% neq 0 (
    echo [FAIL] Tag push failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo  DONE! Released v%NEW_VER%
echo  GitHub Actions will build the installer.
echo  https://github.com/4RH1T3CT0R7/russian-localisation-night-call/releases
echo ========================================
echo.
pause
