@echo off
"C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe" ^
  /target:library ^
  /out:"C:\Users\artem\NightCallRussian\bin\RussianLocalization.dll" ^
  /reference:"C:\Users\artem\NightCallRussian\data\BepInEx\core\BepInEx.dll" ^
  /reference:"C:\Users\artem\NightCallRussian\data\BepInEx\core\0Harmony.dll" ^
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
  "C:\Users\artem\NightCallRussian\src\Mod\RussianLocalization.cs"
if %errorlevel% equ 0 (
    echo BUILD SUCCEEDED
) else (
    echo BUILD FAILED
)
