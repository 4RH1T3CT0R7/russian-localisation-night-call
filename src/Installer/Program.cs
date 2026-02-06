using System;
using System.ComponentModel;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Windows.Forms;
using Microsoft.Win32;

namespace NightCallRussianInstaller
{
    public class InstallerForm : Form
    {
        private Label titleLabel;
        private Label versionLabel;
        private Label pathLabel;
        private TextBox pathTextBox;
        private Button browseButton;
        private GroupBox infoGroup;
        private Label infoLabel;
        private Button installButton;
        private Button uninstallButton;
        private ProgressBar progressBar;
        private RichTextBox logBox;
        private Label statusLabel;
        private BackgroundWorker worker;

        private const string ModVersion = "7.6.0";

        public InstallerForm()
        {
            InitializeComponents();
            string detected = DetectGamePath();
            if (detected != null)
            {
                pathTextBox.Text = detected;
                CheckInstalledState(detected);
            }
        }

        private void InitializeComponents()
        {
            this.Text = "Night Call \u2014 \u0420\u0443\u0441\u0438\u0444\u0438\u043A\u0430\u0442\u043E\u0440";
            this.Size = new Size(620, 560);
            this.MinimumSize = new Size(620, 560);
            this.MaximizeBox = false;
            this.FormBorderStyle = FormBorderStyle.FixedSingle;
            this.StartPosition = FormStartPosition.CenterScreen;
            this.Font = new Font("Segoe UI", 9f);
            this.BackColor = Color.FromArgb(24, 24, 32);
            this.ForeColor = Color.FromArgb(220, 220, 230);

            // Title
            titleLabel = new Label
            {
                Text = "Night Call \u2014 \u0420\u0443\u0441\u0438\u0444\u0438\u043A\u0430\u0442\u043E\u0440",
                Font = new Font("Segoe UI", 18f, FontStyle.Bold),
                ForeColor = Color.FromArgb(255, 200, 80),
                AutoSize = true,
                Location = new Point(20, 15)
            };

            versionLabel = new Label
            {
                Text = "\u0412\u0435\u0440\u0441\u0438\u044F " + ModVersion + "  |  Artem Lytkin (4RH1T3CT0R)",
                Font = new Font("Segoe UI", 8.5f),
                ForeColor = Color.FromArgb(140, 140, 160),
                AutoSize = true,
                Location = new Point(22, 52)
            };

            // Path selection
            pathLabel = new Label
            {
                Text = "\u041F\u0430\u043F\u043A\u0430 \u0441 \u0438\u0433\u0440\u043E\u0439 Night Call:",
                AutoSize = true,
                Location = new Point(20, 85)
            };

            pathTextBox = new TextBox
            {
                Location = new Point(20, 105),
                Size = new Size(470, 24),
                BackColor = Color.FromArgb(40, 40, 55),
                ForeColor = Color.FromArgb(220, 220, 230),
                BorderStyle = BorderStyle.FixedSingle
            };

            browseButton = new Button
            {
                Text = "\u041E\u0431\u0437\u043E\u0440...",
                Location = new Point(500, 104),
                Size = new Size(85, 26),
                FlatStyle = FlatStyle.Flat,
                BackColor = Color.FromArgb(50, 50, 70),
                ForeColor = Color.FromArgb(220, 220, 230)
            };
            browseButton.FlatAppearance.BorderColor = Color.FromArgb(80, 80, 100);
            browseButton.Click += BrowseButton_Click;

            // Info box
            infoGroup = new GroupBox
            {
                Text = "\u0411\u0443\u0434\u0443\u0442 \u0443\u0441\u0442\u0430\u043D\u043E\u0432\u043B\u0435\u043D\u044B",
                Location = new Point(20, 140),
                Size = new Size(565, 100),
                ForeColor = Color.FromArgb(180, 180, 200)
            };

            infoLabel = new Label
            {
                Text = "\u2022 BepInEx (\u0444\u0440\u0435\u0439\u043C\u0432\u043E\u0440\u043A \u043C\u043E\u0434\u043E\u0432)\n" +
                       "\u2022 NightCallRussian.dll (\u043C\u043E\u0434 \u0440\u0443\u0441\u0438\u0444\u0438\u043A\u0430\u0446\u0438\u0438)\n" +
                       "\u2022 \u041F\u0435\u0440\u0435\u0432\u043E\u0434\u044B \u0434\u0438\u0430\u043B\u043E\u0433\u043E\u0432 (155 \u0444\u0430\u0439\u043B\u043E\u0432) + \u0438\u043D\u0442\u0435\u0440\u0444\u0435\u0439\u0441\u0430 (30,000+ \u0441\u0442\u0440\u043E\u043A)\n" +
                       "\u2022 \u041A\u0438\u0440\u0438\u043B\u043B\u0438\u0447\u0435\u0441\u043A\u0438\u0435 \u0448\u0440\u0438\u0444\u0442\u044B \u0438 SDF-\u0430\u0442\u043B\u0430\u0441\u044B",
                Location = new Point(15, 22),
                Size = new Size(535, 70),
                ForeColor = Color.FromArgb(200, 200, 215)
            };
            infoGroup.Controls.Add(infoLabel);

            // Buttons
            installButton = new Button
            {
                Text = "\u0423\u0441\u0442\u0430\u043D\u043E\u0432\u0438\u0442\u044C",
                Location = new Point(20, 252),
                Size = new Size(160, 36),
                FlatStyle = FlatStyle.Flat,
                BackColor = Color.FromArgb(40, 100, 60),
                ForeColor = Color.White,
                Font = new Font("Segoe UI", 10f, FontStyle.Bold)
            };
            installButton.FlatAppearance.BorderColor = Color.FromArgb(60, 140, 80);
            installButton.Click += InstallButton_Click;

            uninstallButton = new Button
            {
                Text = "\u0423\u0434\u0430\u043B\u0438\u0442\u044C \u043C\u043E\u0434",
                Location = new Point(190, 252),
                Size = new Size(140, 36),
                FlatStyle = FlatStyle.Flat,
                BackColor = Color.FromArgb(100, 40, 40),
                ForeColor = Color.White,
                Font = new Font("Segoe UI", 10f)
            };
            uninstallButton.FlatAppearance.BorderColor = Color.FromArgb(140, 60, 60);
            uninstallButton.Click += UninstallButton_Click;

            // Progress
            progressBar = new ProgressBar
            {
                Location = new Point(20, 300),
                Size = new Size(565, 20),
                Style = ProgressBarStyle.Continuous,
                Visible = false
            };

            statusLabel = new Label
            {
                Text = "",
                Location = new Point(20, 325),
                Size = new Size(565, 20),
                ForeColor = Color.FromArgb(160, 160, 180)
            };

            // Log
            logBox = new RichTextBox
            {
                Location = new Point(20, 350),
                Size = new Size(565, 155),
                ReadOnly = true,
                BackColor = Color.FromArgb(16, 16, 24),
                ForeColor = Color.FromArgb(180, 180, 200),
                BorderStyle = BorderStyle.FixedSingle,
                Font = new Font("Consolas", 8.5f),
                ScrollBars = RichTextBoxScrollBars.Vertical
            };

            // Worker
            worker = new BackgroundWorker();
            worker.WorkerReportsProgress = true;
            worker.DoWork += Worker_DoWork;
            worker.ProgressChanged += Worker_ProgressChanged;
            worker.RunWorkerCompleted += Worker_RunWorkerCompleted;

            this.Controls.AddRange(new Control[]
            {
                titleLabel, versionLabel, pathLabel, pathTextBox, browseButton,
                infoGroup, installButton, uninstallButton, progressBar,
                statusLabel, logBox
            });
        }

        private void BrowseButton_Click(object sender, EventArgs e)
        {
            using (var dialog = new FolderBrowserDialog())
            {
                dialog.Description = "\u0412\u044B\u0431\u0435\u0440\u0438\u0442\u0435 \u043F\u0430\u043F\u043A\u0443 \u0441 \u0438\u0433\u0440\u043E\u0439 Night Call";
                dialog.ShowNewFolderButton = false;
                if (!string.IsNullOrEmpty(pathTextBox.Text) && Directory.Exists(pathTextBox.Text))
                    dialog.SelectedPath = pathTextBox.Text;

                if (dialog.ShowDialog() == DialogResult.OK)
                {
                    pathTextBox.Text = dialog.SelectedPath;
                    CheckInstalledState(dialog.SelectedPath);
                }
            }
        }

        private void CheckInstalledState(string gamePath)
        {
            bool installed = File.Exists(Path.Combine(gamePath, "BepInEx", "plugins", "NightCallRussian.dll"));
            if (installed)
            {
                statusLabel.Text = "\u0421\u0442\u0430\u0442\u0443\u0441: \u043C\u043E\u0434 \u0443\u0436\u0435 \u0443\u0441\u0442\u0430\u043D\u043E\u0432\u043B\u0435\u043D";
                statusLabel.ForeColor = Color.FromArgb(100, 200, 120);
            }
            else
            {
                statusLabel.Text = "\u0421\u0442\u0430\u0442\u0443\u0441: \u043C\u043E\u0434 \u043D\u0435 \u0443\u0441\u0442\u0430\u043D\u043E\u0432\u043B\u0435\u043D";
                statusLabel.ForeColor = Color.FromArgb(200, 200, 100);
            }
        }

        private void Log(string message, Color? color = null)
        {
            if (logBox.InvokeRequired)
            {
                logBox.Invoke(new Action(() => Log(message, color)));
                return;
            }
            logBox.SelectionStart = logBox.TextLength;
            logBox.SelectionColor = color ?? Color.FromArgb(180, 180, 200);
            logBox.AppendText(message + "\n");
            logBox.ScrollToCaret();
        }

        private void SetButtonsEnabled(bool enabled)
        {
            installButton.Enabled = enabled;
            uninstallButton.Enabled = enabled;
            browseButton.Enabled = enabled;
            pathTextBox.Enabled = enabled;
        }

        // ========== INSTALL ==========

        private void InstallButton_Click(object sender, EventArgs e)
        {
            string gamePath = pathTextBox.Text.Trim().Trim('"');

            if (string.IsNullOrEmpty(gamePath))
            {
                MessageBox.Show(
                    "\u0423\u043A\u0430\u0436\u0438\u0442\u0435 \u043F\u0443\u0442\u044C \u043A \u043F\u0430\u043F\u043A\u0435 \u0441 \u0438\u0433\u0440\u043E\u0439.",
                    "\u041E\u0448\u0438\u0431\u043A\u0430", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            string exePath = Path.Combine(gamePath, "Night Call.exe");
            if (!File.Exists(exePath))
            {
                MessageBox.Show(
                    "\u0424\u0430\u0439\u043B \"Night Call.exe\" \u043D\u0435 \u043D\u0430\u0439\u0434\u0435\u043D \u0432:\n" + gamePath +
                    "\n\n\u041F\u0440\u043E\u0432\u0435\u0440\u044C\u0442\u0435 \u043F\u0443\u0442\u044C \u0438 \u043F\u043E\u043F\u0440\u043E\u0431\u0443\u0439\u0442\u0435 \u0441\u043D\u043E\u0432\u0430.",
                    "\u041E\u0448\u0438\u0431\u043A\u0430", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }

            try
            {
                var procs = Process.GetProcessesByName("Night Call");
                if (procs.Length > 0)
                {
                    MessageBox.Show(
                        "\u0418\u0433\u0440\u0430 Night Call \u0437\u0430\u043F\u0443\u0449\u0435\u043D\u0430.\n\u0417\u0430\u043A\u0440\u043E\u0439\u0442\u0435 \u0438\u0433\u0440\u0443 \u043F\u0435\u0440\u0435\u0434 \u0443\u0441\u0442\u0430\u043D\u043E\u0432\u043A\u043E\u0439.",
                        "\u041E\u0448\u0438\u0431\u043A\u0430", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    return;
                }
            }
            catch { }

            logBox.Clear();
            SetButtonsEnabled(false);
            progressBar.Visible = true;
            progressBar.Value = 0;
            worker.RunWorkerAsync(new WorkerArgs { GamePath = gamePath, Mode = "install" });
        }

        // ========== UNINSTALL ==========

        private void UninstallButton_Click(object sender, EventArgs e)
        {
            string gamePath = pathTextBox.Text.Trim().Trim('"');

            if (string.IsNullOrEmpty(gamePath) || !Directory.Exists(gamePath))
            {
                MessageBox.Show(
                    "\u0423\u043A\u0430\u0436\u0438\u0442\u0435 \u043F\u0443\u0442\u044C \u043A \u043F\u0430\u043F\u043A\u0435 \u0441 \u0438\u0433\u0440\u043E\u0439.",
                    "\u041E\u0448\u0438\u0431\u043A\u0430", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            var result = MessageBox.Show(
                "\u0423\u0434\u0430\u043B\u0438\u0442\u044C \u0440\u0443\u0441\u0438\u0444\u0438\u043A\u0430\u0442\u043E\u0440 \u0438\u0437:\n" + gamePath + "\n\n" +
                "\u0411\u0443\u0434\u0443\u0442 \u0443\u0434\u0430\u043B\u0435\u043D\u044B: BepInEx, Russian_UI, Russian_Texts,\n" +
                "Generated_SDF, Fonts_Cyrillic, winhttp.dll, doorstop_config.ini, passage_dump.txt",
                "\u041F\u043E\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043D\u0438\u0435",
                MessageBoxButtons.YesNo, MessageBoxIcon.Question);

            if (result != DialogResult.Yes)
                return;

            logBox.Clear();
            SetButtonsEnabled(false);
            progressBar.Visible = true;
            progressBar.Value = 0;
            worker.RunWorkerAsync(new WorkerArgs { GamePath = gamePath, Mode = "uninstall" });
        }

        // ========== BACKGROUND WORKER ==========

        private class WorkerArgs
        {
            public string GamePath;
            public string Mode;
        }

        private void Worker_DoWork(object sender, DoWorkEventArgs e)
        {
            var args = (WorkerArgs)e.Argument;
            if (args.Mode == "install")
                DoInstall(args.GamePath);
            else
                DoUninstall(args.GamePath);
        }

        private void DoInstall(string gamePath)
        {
            string tempDir = Path.Combine(Path.GetTempPath(),
                "NightCallRussian_install_" + Guid.NewGuid().ToString("N").Substring(0, 8));

            try
            {
                Directory.CreateDirectory(tempDir);

                // Step 1: Extract
                worker.ReportProgress(10, "\u0420\u0430\u0441\u043F\u0430\u043A\u043E\u0432\u043A\u0430 \u0434\u0430\u043D\u043D\u044B\u0445...");
                Log("[1/3] \u0420\u0430\u0441\u043F\u0430\u043A\u043E\u0432\u043A\u0430 \u0434\u0430\u043D\u043D\u044B\u0445...");

                string zipTemp = Path.Combine(tempDir, "data.zip");
                var assembly = Assembly.GetExecutingAssembly();
                using (var stream = assembly.GetManifestResourceStream("data.zip"))
                {
                    if (stream == null)
                    {
                        Log("\u041E\u0428\u0418\u0411\u041A\u0410: \u043D\u0435 \u0443\u0434\u0430\u043B\u043E\u0441\u044C \u043D\u0430\u0439\u0442\u0438 \u0432\u0441\u0442\u0440\u043E\u0435\u043D\u043D\u044B\u0435 \u0434\u0430\u043D\u043D\u044B\u0435.", Color.Red);
                        return;
                    }

                    using (var file = File.Create(zipTemp))
                    {
                        stream.CopyTo(file);
                    }
                }

                ZipFile.ExtractToDirectory(zipTemp, tempDir);
                File.Delete(zipTemp);
                Log("   \u0420\u0430\u0441\u043F\u0430\u043A\u043E\u0432\u043A\u0430 OK", Color.FromArgb(100, 200, 120));

                // Step 2: Copy
                worker.ReportProgress(40, "\u041A\u043E\u043F\u0438\u0440\u043E\u0432\u0430\u043D\u0438\u0435 \u0444\u0430\u0439\u043B\u043E\u0432...");
                Log("[2/3] \u041A\u043E\u043F\u0438\u0440\u043E\u0432\u0430\u043D\u0438\u0435 \u0444\u0430\u0439\u043B\u043E\u0432...");

                int copied = CopyDirectory(tempDir, gamePath);
                Log("   \u0421\u043A\u043E\u043F\u0438\u0440\u043E\u0432\u0430\u043D\u043E: " + copied + " \u0444\u0430\u0439\u043B\u043E\u0432", Color.FromArgb(100, 200, 120));

                // Step 3: Verify
                worker.ReportProgress(80, "\u041F\u0440\u043E\u0432\u0435\u0440\u043A\u0430...");
                Log("[3/3] \u041F\u0440\u043E\u0432\u0435\u0440\u043A\u0430...");

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

                bool ok = true;
                foreach (var cf in checkFiles)
                {
                    if (!File.Exists(Path.Combine(gamePath, cf)))
                    {
                        Log("   \u041D\u0435 \u043D\u0430\u0439\u0434\u0435\u043D: " + cf, Color.FromArgb(255, 100, 100));
                        ok = false;
                    }
                }

                if (ok)
                {
                    worker.ReportProgress(100, "\u0423\u0441\u0442\u0430\u043D\u043E\u0432\u043A\u0430 \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043D\u0430!");
                    Log("");
                    Log("\u0423\u0441\u0442\u0430\u043D\u043E\u0432\u043A\u0430 \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043D\u0430!", Color.FromArgb(255, 200, 80));
                    Log("\u0417\u0430\u043F\u0443\u0441\u0442\u0438\u0442\u0435 Night Call \u0447\u0435\u0440\u0435\u0437 Steam \u2014 \u0440\u0443\u0441\u0441\u043A\u0438\u0439 \u044F\u0437\u044B\u043A \u0432\u043A\u043B\u044E\u0447\u0438\u0442\u0441\u044F \u0430\u0432\u0442\u043E\u043C\u0430\u0442\u0438\u0447\u0435\u0441\u043A\u0438.");
                }
                else
                {
                    worker.ReportProgress(100, "\u0423\u0441\u0442\u0430\u043D\u043E\u0432\u043A\u0430 \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043D\u0430 \u0441 \u043E\u0448\u0438\u0431\u043A\u0430\u043C\u0438");
                    Log("\u0423\u0441\u0442\u0430\u043D\u043E\u0432\u043A\u0430 \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043D\u0430, \u043D\u043E \u043D\u0435\u043A\u043E\u0442\u043E\u0440\u044B\u0435 \u0444\u0430\u0439\u043B\u044B \u043D\u0435 \u043D\u0430\u0439\u0434\u0435\u043D\u044B.", Color.FromArgb(255, 200, 100));
                }
            }
            catch (Exception ex)
            {
                Log("\u041E\u0428\u0418\u0411\u041A\u0410: " + ex.Message, Color.Red);
                worker.ReportProgress(100, "\u041E\u0448\u0438\u0431\u043A\u0430 \u0443\u0441\u0442\u0430\u043D\u043E\u0432\u043A\u0438");
            }
            finally
            {
                try
                {
                    if (Directory.Exists(tempDir))
                        Directory.Delete(tempDir, true);
                }
                catch { }
            }
        }

        private void DoUninstall(string gamePath)
        {
            worker.ReportProgress(10, "\u0423\u0434\u0430\u043B\u0435\u043D\u0438\u0435 \u043C\u043E\u0434\u0430...");
            Log("\u0423\u0434\u0430\u043B\u0435\u043D\u0438\u0435 \u0440\u0443\u0441\u0438\u0444\u0438\u043A\u0430\u0442\u043E\u0440\u0430...");

            int removed = 0;

            string[] filesToDelete = new string[]
            {
                "winhttp.dll",
                "doorstop_config.ini",
                "passage_dump.txt"
            };

            string[] dirsToDelete = new string[]
            {
                "BepInEx",
                "Russian_UI",
                "Russian_Texts",
                "Generated_SDF",
                "Fonts_Cyrillic"
            };

            foreach (var f in filesToDelete)
            {
                string fullPath = Path.Combine(gamePath, f);
                if (File.Exists(fullPath))
                {
                    try
                    {
                        File.Delete(fullPath);
                        Log("   \u0423\u0434\u0430\u043B\u0451\u043D: " + f);
                        removed++;
                    }
                    catch (Exception ex)
                    {
                        Log("   \u041D\u0435 \u0443\u0434\u0430\u043B\u043E\u0441\u044C \u0443\u0434\u0430\u043B\u0438\u0442\u044C " + f + ": " + ex.Message, Color.FromArgb(255, 200, 100));
                    }
                }
            }

            worker.ReportProgress(40, "\u0423\u0434\u0430\u043B\u0435\u043D\u0438\u0435 \u043F\u0430\u043F\u043E\u043A...");

            foreach (var d in dirsToDelete)
            {
                string fullPath = Path.Combine(gamePath, d);
                if (Directory.Exists(fullPath))
                {
                    try
                    {
                        Directory.Delete(fullPath, true);
                        Log("   \u0423\u0434\u0430\u043B\u0451\u043D\u0430 \u043F\u0430\u043F\u043A\u0430: " + d);
                        removed++;
                    }
                    catch (Exception ex)
                    {
                        Log("   \u041D\u0435 \u0443\u0434\u0430\u043B\u043E\u0441\u044C \u0443\u0434\u0430\u043B\u0438\u0442\u044C " + d + ": " + ex.Message, Color.FromArgb(255, 200, 100));
                    }
                }
            }

            worker.ReportProgress(100, "\u0423\u0434\u0430\u043B\u0435\u043D\u0438\u0435 \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043D\u043E");
            Log("");
            Log("\u041C\u043E\u0434 \u0443\u0434\u0430\u043B\u0451\u043D. \u0423\u0434\u0430\u043B\u0435\u043D\u043E \u044D\u043B\u0435\u043C\u0435\u043D\u0442\u043E\u0432: " + removed, Color.FromArgb(255, 200, 80));
        }

        private void Worker_ProgressChanged(object sender, ProgressChangedEventArgs e)
        {
            progressBar.Value = e.ProgressPercentage;
            if (e.UserState is string msg)
                statusLabel.Text = msg;
        }

        private void Worker_RunWorkerCompleted(object sender, RunWorkerCompletedEventArgs e)
        {
            SetButtonsEnabled(true);
            CheckInstalledState(pathTextBox.Text.Trim().Trim('"'));
        }

        // ========== GAME PATH DETECTION ==========

        private static string DetectGamePath()
        {
            // Method 1: Common Steam library paths
            string[] drives = { "C", "D", "E", "F", "G", "H" };
            string[] prefixes =
            {
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
                        return path;
                }
            }

            // Method 2: Steam registry
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

                            string mainLib = Path.Combine(steamPath, "steamapps", "common", "Night Call");
                            if (File.Exists(Path.Combine(mainLib, "Night Call.exe")))
                                return mainLib;

                            string vdfPath = Path.Combine(steamPath, "steamapps", "libraryfolders.vdf");
                            if (File.Exists(vdfPath))
                            {
                                string vdf = File.ReadAllText(vdfPath);
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

            // Method 3: Installer next to game
            string selfDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
            if (File.Exists(Path.Combine(selfDir, "Night Call.exe")))
                return selfDir;

            return null;
        }

        private static int CopyDirectory(string source, string target)
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
    }

    static class Program
    {
        [STAThread]
        static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new InstallerForm());
        }
    }
}
