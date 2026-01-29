using System;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Diagnostics;
using Microsoft.Win32;

namespace NightCallRussianInstaller
{
    class Program
    {
        static void Main(string[] args)
        {
            Console.OutputEncoding = System.Text.Encoding.UTF8;

            Console.WriteLine("============================================================");
            Console.WriteLine("  Night Call — Русификатор (Russian Localization Mod)");
            Console.WriteLine("  Автор: Artem Lytkin (4RH1T3CT0R)");
            Console.WriteLine("  Версия: 6.0.0");
            Console.WriteLine("============================================================");
            Console.WriteLine();

            // Detect game path
            string gamePath = DetectGamePath();

            if (gamePath == null)
            {
                Console.WriteLine("[!] Не удалось автоматически определить путь к игре.");
                Console.WriteLine();
                Console.Write("Укажите полный путь к папке Night Call: ");
                gamePath = Console.ReadLine();

                if (string.IsNullOrWhiteSpace(gamePath))
                {
                    Console.WriteLine("Установка отменена.");
                    WaitForKey();
                    return;
                }

                gamePath = gamePath.Trim().Trim('"');
            }

            string exePath = Path.Combine(gamePath, "Night Call.exe");
            if (!File.Exists(exePath))
            {
                Console.WriteLine();
                Console.WriteLine("[ОШИБКА] Файл \"Night Call.exe\" не найден в: " + gamePath);
                Console.WriteLine("Проверьте путь и попробуйте снова.");
                WaitForKey();
                return;
            }

            Console.WriteLine("Папка игры: " + gamePath);
            Console.WriteLine();

            // Check if game is running
            try
            {
                var procs = Process.GetProcessesByName("Night Call");
                if (procs.Length > 0)
                {
                    Console.WriteLine("[!] Игра Night Call запущена. Закройте игру перед установкой.");
                    WaitForKey();
                    return;
                }
            }
            catch { }

            Console.WriteLine("Будут установлены:");
            Console.WriteLine("  - BepInEx (фреймворк модов)");
            Console.WriteLine("  - NightCallRussian.dll (мод русификации)");
            Console.WriteLine("  - Переводы диалогов (155 файлов)");
            Console.WriteLine("  - Переводы интерфейса (30,000+ строк)");
            Console.WriteLine("  - Кириллические шрифты и SDF-атласы");
            Console.WriteLine();
            Console.Write("Продолжить установку? (Y/N): ");

            string answer = Console.ReadLine();
            if (string.IsNullOrEmpty(answer) || (answer.ToUpper() != "Y" && answer.ToUpper() != "Д"))
            {
                Console.WriteLine("Установка отменена.");
                WaitForKey();
                return;
            }

            Console.WriteLine();
            Console.WriteLine("Установка...");
            Console.WriteLine();

            // Extract embedded ZIP to temp
            string tempDir = Path.Combine(Path.GetTempPath(), "NightCallRussian_install_" + Guid.NewGuid().ToString("N").Substring(0, 8));

            try
            {
                Directory.CreateDirectory(tempDir);

                Console.Write("[1/3] Распаковка данных...");
                string zipTemp = Path.Combine(tempDir, "data.zip");

                var assembly = Assembly.GetExecutingAssembly();
                using (var stream = assembly.GetManifestResourceStream("data.zip"))
                {
                    if (stream == null)
                    {
                        Console.WriteLine(" ОШИБКА");
                        Console.WriteLine("Не удалось найти встроенные данные.");
                        WaitForKey();
                        return;
                    }

                    using (var file = File.Create(zipTemp))
                    {
                        stream.CopyTo(file);
                    }
                }

                ZipFile.ExtractToDirectory(zipTemp, tempDir);
                File.Delete(zipTemp);
                Console.WriteLine(" OK");

                // Copy files
                Console.Write("[2/3] Копирование файлов...");
                int copied = CopyDirectory(tempDir, gamePath);
                Console.WriteLine(" OK (" + copied + " файлов)");

                // Verify
                Console.Write("[3/3] Проверка...");
                bool ok = true;
                string[] checkFiles = new string[]
                {
                    "winhttp.dll",
                    "doorstop_config.ini",
                    "BepInEx\\core\\BepInEx.dll",
                    "BepInEx\\plugins\\NightCallRussian.dll",
                    "Russian_UI\\full_translation_mapping.json",
                    "Russian_UI\\key_based_translations.json",
                    "Fonts_Cyrillic\\PTSans-Regular.ttf",
                    "Generated_SDF\\PTSans_SDF_atlas.png",
                    "passage_dump.txt"
                };

                foreach (var cf in checkFiles)
                {
                    if (!File.Exists(Path.Combine(gamePath, cf)))
                    {
                        Console.WriteLine(" ОШИБКА");
                        Console.WriteLine("Файл не найден: " + cf);
                        ok = false;
                        break;
                    }
                }

                if (ok)
                {
                    Console.WriteLine(" OK");
                    Console.WriteLine();
                    Console.WriteLine("============================================================");
                    Console.WriteLine("  Установка завершена!");
                    Console.WriteLine("============================================================");
                    Console.WriteLine();
                    Console.WriteLine("Запустите Night Call через Steam — русский язык включится");
                    Console.WriteLine("автоматически.");
                    Console.WriteLine();
                    Console.WriteLine("Если возникнут проблемы, проверьте лог:");
                    Console.WriteLine("  " + Path.Combine(gamePath, "BepInEx", "LogOutput.log"));
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine();
                Console.WriteLine("[ОШИБКА] " + ex.Message);
            }
            finally
            {
                // Cleanup temp
                try
                {
                    if (Directory.Exists(tempDir))
                        Directory.Delete(tempDir, true);
                }
                catch { }
            }

            WaitForKey();
        }

        static string DetectGamePath()
        {
            // Method 1: Check common Steam library paths
            string[] drives = { "C", "D", "E", "F", "G", "H" };
            string[] prefixes = {
                @":\Program Files (x86)\Steam\steamapps\common\Night Call",
                @":\Program Files\Steam\steamapps\common\Night Call",
                @":\Steam\steamapps\common\Night Call",
                @":\SteamLibrary\steamapps\common\Night Call",
                @":\Games\Steam\steamapps\common\Night Call",
                @":\Games\SteamLibrary\steamapps\common\Night Call"
            };

            foreach (var drive in drives)
            {
                foreach (var prefix in prefixes)
                {
                    string path = drive + prefix;
                    if (File.Exists(Path.Combine(path, "Night Call.exe")))
                    {
                        return path;
                    }
                }
            }

            // Method 2: Check Steam registry
            try
            {
                using (var key = Registry.CurrentUser.OpenSubKey(@"Software\Valve\Steam"))
                {
                    if (key != null)
                    {
                        string steamPath = key.GetValue("SteamPath") as string;
                        if (!string.IsNullOrEmpty(steamPath))
                        {
                            steamPath = steamPath.Replace("/", "\\");

                            // Check main library
                            string mainLib = Path.Combine(steamPath, "steamapps", "common", "Night Call");
                            if (File.Exists(Path.Combine(mainLib, "Night Call.exe")))
                                return mainLib;

                            // Parse libraryfolders.vdf for additional libraries
                            string vdfPath = Path.Combine(steamPath, "steamapps", "libraryfolders.vdf");
                            if (File.Exists(vdfPath))
                            {
                                string vdf = File.ReadAllText(vdfPath);
                                // Simple parse: find "path" values
                                int idx = 0;
                                while (true)
                                {
                                    idx = vdf.IndexOf("\"path\"", idx);
                                    if (idx < 0) break;
                                    int q1 = vdf.IndexOf("\"", idx + 6);
                                    if (q1 < 0) break;
                                    int q2 = vdf.IndexOf("\"", q1 + 1);
                                    if (q2 < 0) break;
                                    string libPath = vdf.Substring(q1 + 1, q2 - q1 - 1).Replace("\\\\", "\\");
                                    string check = Path.Combine(libPath, "steamapps", "common", "Night Call");
                                    if (File.Exists(Path.Combine(check, "Night Call.exe")))
                                        return check;
                                    idx = q2 + 1;
                                }
                            }
                        }
                    }
                }
            }
            catch { }

            // Method 3: Check if installer is next to the game
            string selfDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
            if (File.Exists(Path.Combine(selfDir, "Night Call.exe")))
                return selfDir;

            return null;
        }

        static int CopyDirectory(string source, string target)
        {
            int count = 0;
            foreach (var dir in Directory.GetDirectories(source, "*", SearchOption.AllDirectories))
            {
                string rel = dir.Substring(source.Length).TrimStart('\\');
                Directory.CreateDirectory(Path.Combine(target, rel));
            }

            foreach (var file in Directory.GetFiles(source, "*", SearchOption.AllDirectories))
            {
                string rel = file.Substring(source.Length).TrimStart('\\');
                string dest = Path.Combine(target, rel);
                File.Copy(file, dest, true);
                count++;
            }

            return count;
        }

        static void WaitForKey()
        {
            Console.WriteLine();
            Console.WriteLine("Нажмите любую клавишу для выхода...");
            try { Console.ReadKey(true); } catch { }
        }
    }
}
