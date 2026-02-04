using BepInEx;
using BepInEx.Configuration;
using BepInEx.Logging;
using HarmonyLib;
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

namespace NightCallRussian
{
    [BepInPlugin("com.nightcall.russian", "Night Call Russian", "6.2.0")]
    public class RussianLocalization : BaseUnityPlugin
    {
        internal static ManualLogSource Log;
        internal static Dictionary<string, string> Translations = new Dictionary<string, string>();
        internal static Dictionary<string, string> KeyTranslations = new Dictionary<string, string>();
        internal static Dictionary<string, string> DialogueTexts = new Dictionary<string, string>();
        internal static Dictionary<string, string> RuToEngSpeaker = new Dictionary<string, string>();
        internal static bool IsInitialized = false;

        // Static empty array to avoid Array.Empty optimization issues with .NET 4.6
        private static readonly object[] EmptyObjectArray = new object[] { };
        internal static Font CyrillicFont = null;
        internal static Dictionary<string, Font> LoadedFonts = new Dictionary<string, Font>();
        internal static object CyrillicTMPFont = null; // TMP_FontAsset
        internal static Material BundleMaterial = null;
        internal static Texture2D BundleAtlas = null;

        // Font scaling configuration
        internal static float FontScale = 1.0f;
        private static ConfigEntry<float> FontScaleConfig;

        private static RussianLocalization Instance;
        private static Harmony HarmonyInstance;
        private static bool LocalizationPatched = false;
        private static bool TranslationsInjected = false;
        private static Type LocalizationManagerType = null;
        private float lastScanTime = 0f;
        private const float SCAN_INTERVAL = 0.05f; // 50ms for instant translation
        private HashSet<string> processedTextKeys = new HashSet<string>();
        private static HashSet<int> PatchedFontIds = new HashSet<int>(); // Track patched fonts by instance ID
        private static bool FontMetricsLogged = false; // Log metrics only once per session

        void Awake()
        {
            Instance = this;
            Log = Logger;
            Log.LogInfo("Night Call Russian Localization v6.2.0 - Starting...");

            // Load font scale config
            FontScaleConfig = Config.Bind("Font", "FontScale", 1.15f,
                "Font scale multiplier (1.0 = normal, 1.15 = 15% larger)");
            FontScale = FontScaleConfig.Value;
            Log.LogInfo(string.Format("Font scale: {0}", FontScale));

            try
            {
                Log.LogInfo("Loading translations...");
                LoadTranslations();
                Log.LogInfo(string.Format("Translations loaded: {0}", Translations.Count));
            }
            catch (Exception e)
            {
                Log.LogError(string.Format("Error loading translations: {0}", e));
            }

            try
            {
                Log.LogInfo("Loading dialogue texts...");
                LoadDialogueTexts();
                Log.LogInfo(string.Format("Dialogue texts loaded: {0}", DialogueTexts.Count));
            }
            catch (Exception e)
            {
                Log.LogError(string.Format("Error loading dialogue texts: {0}", e));
            }

            try
            {
                Log.LogInfo("Loading key-based translations...");
                LoadKeyTranslations();
                Log.LogInfo(string.Format("Key-based translations loaded: {0}", KeyTranslations.Count));
            }
            catch (Exception e)
            {
                Log.LogError(string.Format("Error loading key translations: {0}", e));
            }

            try
            {
                Log.LogInfo("Loading passage dump for sequential fallback...");
                LoadPassageDump();
            }
            catch (Exception e)
            {
                Log.LogError(string.Format("Error loading passage dump: {0}", e));
            }

            try
            {
                Log.LogInfo("Loading Cyrillic fonts...");
                LoadCyrillicFonts();
            }
            catch (Exception e)
            {
                Log.LogError(string.Format("Error loading fonts: {0}", e));
            }

            try
            {
                Log.LogInfo("Applying Harmony patches...");
                HarmonyInstance = new Harmony("com.nightcall.russian");

                // Apply standard patches (TextAsset, UI.Text, Resources)
                HarmonyInstance.PatchAll();
                Log.LogInfo("Standard Harmony patches applied");

                // Patch TMP_Text.set_text to strip __ markers
                PatchTMPText();

                // LocalizationManager patch will be applied on first scene load
                // because Assembly-CSharp isn't loaded yet during Awake
            }
            catch (Exception e)
            {
                Log.LogError(string.Format("Error applying patches: {0}", e));
            }

            // Register scene loading event
            try
            {
                SceneManager.sceneLoaded += OnSceneLoaded;
                Log.LogInfo("Scene load hook registered");
            }
            catch (Exception e)
            {
                Log.LogError(string.Format("Error registering scene hook: {0}", e));
            }

            IsInitialized = true;
            Log.LogInfo(string.Format("Initialization complete. {0} UI translations, {1} key translations, {2} dialogue texts", Translations.Count, KeyTranslations.Count, DialogueTexts.Count));
        }

        void OnDestroy()
        {
            SceneManager.sceneLoaded -= OnSceneLoaded;
        }

        // Translate TMP text immediately - this is called by Harmony patch on TMP_Text.text setter
        public static void TMP_Text_set_text_Prefix(ref string value)
        {
            if (string.IsNullOrEmpty(value)) return;

            // Fix encoding corruption (é -> missing char, etc.)
            if (value.Contains("Al\u00A0sia") || value.Contains("Al sia"))
            {
                value = value.Replace("Al\u00A0sia", "Al\u00E9sia").Replace("Al sia", "Al\u00E9sia");
            }

            // Replace "km" with "км" in distance strings (e.g. "4.68 km")
            if (value.EndsWith(" km") || value.EndsWith(" km "))
            {
                value = value.Replace(" km", " км");
            }

            // Strip __ markers if present
            string cleanText = value;
            if (cleanText.StartsWith("__") && cleanText.EndsWith("__") && cleanText.Length > 4)
            {
                cleanText = cleanText.Substring(2, cleanText.Length - 4);
            }

            // Try to translate
            string translated = TranslateTextDirect(cleanText);
            if (!string.IsNullOrEmpty(translated))
            {
                value = translated;
            }
            else if (cleanText != value)
            {
                // At least return without __ markers
                value = cleanText;
            }
        }

        // Normalize text by replacing typographic characters with standard ones
        internal static string NormalizeText(string text)
        {
            if (string.IsNullOrEmpty(text)) return text;

            // Replace typographic characters
            text = text.Replace('\u2019', '\'');  // ' -> '
            text = text.Replace('\u2018', '\'');  // ' -> '
            text = text.Replace('\u201C', '"');   // " -> "
            text = text.Replace('\u201D', '"');   // " -> "
            text = text.Replace('\u2026', '.');   // … -> . (will become ...)
            text = text.Replace("\u2026", "..."); // … -> ...
            text = text.Replace('\u00AB', '<');   // « -> <
            text = text.Replace('\u00BB', '>');   // » -> >
            text = text.Replace('\u00A0', ' ');   // non-breaking space -> space
            text = text.Replace('\u2013', '-');   // en dash -> -
            text = text.Replace('\u2014', '-');   // em dash -> -

            return text;
        }

        // Strip diacritics/accents from text (e.g. HERVÉ -> HERVE, GÉRARD -> GERARD)
        internal static string StripAccents(string text)
        {
            if (string.IsNullOrEmpty(text)) return text;
            string decomposed = text.Normalize(System.Text.NormalizationForm.FormD);
            var sb = new System.Text.StringBuilder(decomposed.Length);
            for (int i = 0; i < decomposed.Length; i++)
            {
                char c = decomposed[i];
                if (System.Globalization.CharUnicodeInfo.GetUnicodeCategory(c) !=
                    System.Globalization.UnicodeCategory.NonSpacingMark)
                    sb.Append(c);
            }
            return sb.ToString().Normalize(System.Text.NormalizationForm.FormC);
        }

        // Check if text is a currency amount or time (shouldn't be translated)
        internal static bool IsCurrencyOrTimeString(string text)
        {
            if (string.IsNullOrEmpty(text)) return false;

            string trimmed = text.Trim();
            if (trimmed.Length == 0) return false;

            // Check for currency symbols
            bool hasCurrency = trimmed.Contains("€") || trimmed.Contains("$") ||
                               trimmed.Contains("£") || trimmed.Contains("¥");

            // Check if mostly digits, dots, commas, spaces, colons, and currency
            int digitCount = 0;
            int letterCount = 0;
            foreach (char c in trimmed)
            {
                if (char.IsDigit(c)) digitCount++;
                else if (char.IsLetter(c)) letterCount++;
            }

            // If has currency symbol and mostly numeric, skip translation
            if (hasCurrency && digitCount > letterCount)
                return true;

            // Time format like "22:00"
            if (trimmed.Length <= 10 && trimmed.Contains(":") && digitCount >= 2 && letterCount == 0)
                return true;

            // Pure numeric with possible decimals (like "327.00")
            if (letterCount == 0 && digitCount > 0)
                return true;

            return false;
        }

        // Direct translation lookup without side effects
        internal static string TranslateTextDirect(string text)
        {
            if (string.IsNullOrEmpty(text)) return null;
            if (Translations == null || Translations.Count == 0) return null;

            // Check if already contains Cyrillic
            foreach (char c in text)
            {
                if (c >= 0x0400 && c <= 0x04FF) return null;
            }

            // Skip currency/numeric strings (like "327.00 €" or "22:00")
            // These are dynamically formatted and shouldn't be translated
            if (IsCurrencyOrTimeString(text)) return null;

            string translation;

            // Try exact match first
            if (Translations.TryGetValue(text, out translation))
            {
                return translation;
            }

            // Try normalized version (replace typographic chars with standard)
            string normalized = NormalizeText(text);
            if (normalized != text && Translations.TryGetValue(normalized, out translation))
            {
                return translation;
            }

            // Try without leading/trailing whitespace and newlines
            string trimmed = text.Trim().Replace("\r", "").Replace("\n", " ");
            if (trimmed != text && Translations.TryGetValue(trimmed, out translation))
            {
                return translation;
            }

            // Try normalized + trimmed
            string normTrimmed = NormalizeText(trimmed);
            if (normTrimmed != text && Translations.TryGetValue(normTrimmed, out translation))
            {
                return translation;
            }

            // Try case-insensitive - check common variations
            if (Translations.TryGetValue(text.ToUpperInvariant(), out translation))
            {
                return translation;
            }

            if (Translations.TryGetValue(text.ToLowerInvariant(), out translation))
            {
                return translation;
            }

            // Try normalized uppercase/lowercase
            if (Translations.TryGetValue(normalized.ToUpperInvariant(), out translation))
            {
                return translation;
            }

            if (Translations.TryGetValue(normalized.ToLowerInvariant(), out translation))
            {
                return translation;
            }

            // Try with first letter capitalized
            if (text.Length > 0)
            {
                string capitalized = char.ToUpperInvariant(text[0]) + (text.Length > 1 ? text.Substring(1).ToLowerInvariant() : "");
                if (Translations.TryGetValue(capitalized, out translation))
                {
                    return translation;
                }

                // Also try normalized capitalized
                string normCapitalized = char.ToUpperInvariant(normalized[0]) + (normalized.Length > 1 ? normalized.Substring(1).ToLowerInvariant() : "");
                if (Translations.TryGetValue(normCapitalized, out translation))
                {
                    return translation;
                }
            }

            // Try accent-stripped version (e.g. HERVÉ -> HERVE, GÉRARD -> GERARD)
            string stripped = StripAccents(text);
            if (stripped != text)
            {
                if (Translations.TryGetValue(stripped, out translation))
                    return translation;
                if (Translations.TryGetValue(stripped.ToUpperInvariant(), out translation))
                    return translation;
            }

            // Try multi-line translation: split by newlines, translate each line
            if (text.IndexOf('\n') >= 0)
            {
                string[] parts = text.Split(new char[] { '\n' });
                if (parts.Length >= 2 && parts.Length <= 20)
                {
                    bool allTranslated = true;
                    string[] translated_parts = new string[parts.Length];
                    for (int pi = 0; pi < parts.Length; pi++)
                    {
                        string part = parts[pi].Trim('\r');
                        if (string.IsNullOrEmpty(part) || part.Trim().Length == 0)
                        {
                            translated_parts[pi] = part;
                            continue;
                        }
                        // Skip lines already in Cyrillic
                        bool hasCyr = false;
                        foreach (char ch in part)
                        {
                            if (ch >= 0x0400 && ch <= 0x04FF) { hasCyr = true; break; }
                        }
                        if (hasCyr)
                        {
                            translated_parts[pi] = part;
                            continue;
                        }
                        string partNorm = NormalizeText(part);
                        string partTrimmed = part.Trim();
                        string ptrans;
                        if (Translations.TryGetValue(part, out ptrans) ||
                            Translations.TryGetValue(partNorm, out ptrans) ||
                            Translations.TryGetValue(partTrimmed, out ptrans) ||
                            Translations.TryGetValue(NormalizeText(partTrimmed), out ptrans))
                        {
                            translated_parts[pi] = ptrans;
                        }
                        else
                        {
                            allTranslated = false;
                            break;
                        }
                    }
                    if (allTranslated)
                    {
                        return string.Join("\n", translated_parts);
                    }
                }
            }

            return null;
        }

        void PatchTMPText()
        {
            try
            {
                // Find TMP_Text type
                Type tmpTextType = null;
                foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
                {
                    tmpTextType = assembly.GetType("TMPro.TMP_Text");
                    if (!object.ReferenceEquals(tmpTextType, null)) break;
                }

                if (object.ReferenceEquals(tmpTextType, null))
                {
                    Log.LogWarning("TMP_Text type not found for patching");
                    return;
                }

                // Find the text property setter
                PropertyInfo textProp = tmpTextType.GetProperty("text");
                if (object.ReferenceEquals(textProp, null))
                {
                    Log.LogWarning("TMP_Text.text property not found");
                    return;
                }

                MethodInfo setter = textProp.GetSetMethod();
                if (object.ReferenceEquals(setter, null))
                {
                    Log.LogWarning("TMP_Text.text setter not found");
                    return;
                }

                // Get our prefix method
                MethodInfo prefix = typeof(RussianLocalization).GetMethod("TMP_Text_set_text_Prefix",
                    BindingFlags.Public | BindingFlags.Static);

                if (object.ReferenceEquals(prefix, null))
                {
                    Log.LogWarning("TMP_Text_set_text_Prefix method not found");
                    return;
                }

                // Apply patch
                HarmonyInstance.Patch(setter, new HarmonyMethod(prefix));
                Log.LogInfo("TMP_Text.text setter patched to strip __ markers");
            }
            catch (Exception e)
            {
                Log.LogError(string.Format("Error patching TMP_Text: {0}", e));
            }
        }

        void EnumerateAndPatchAllFonts()
        {
            try
            {
                // Find TMP_FontAsset type
                Type tmpFontAssetType = null;
                foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
                {
                    tmpFontAssetType = assembly.GetType("TMPro.TMP_FontAsset");
                    if (!object.ReferenceEquals(tmpFontAssetType, null)) break;
                }

                if (object.ReferenceEquals(tmpFontAssetType, null))
                {
                    Log.LogWarning("TMP_FontAsset type not found for enumeration");
                    return;
                }

                // Find all loaded TMP font assets
                var allFontAssets = Resources.FindObjectsOfTypeAll(tmpFontAssetType);
                Log.LogInfo(string.Format("=== TMP FONT ENUMERATION: Found {0} fonts ===", allFontAssets.Length));

                // Prepare to write metrics to file
                string gameRoot = Path.GetDirectoryName(Application.dataPath);
                string metricsPath = Path.Combine(gameRoot, "TMP_Font_Metrics.txt");
                StringBuilder metricsBuilder = new StringBuilder();
                metricsBuilder.AppendLine("=== TMP FONT METRICS ===");
                metricsBuilder.AppendLine(string.Format("Generated: {0}", DateTime.Now));
                metricsBuilder.AppendLine(string.Format("Total fonts: {0}", allFontAssets.Length));
                metricsBuilder.AppendLine();

                // Get fontInfo property
                PropertyInfo fontInfoProp = tmpFontAssetType.GetProperty("fontInfo");

                // Get paths to our Cyrillic SDF files
                string sdfFolder = Path.Combine(gameRoot, "Generated_SDF");
                string atlasPath = Path.Combine(sdfFolder, "PTSans_SDF_atlas.png");
                string glyphsPath = Path.Combine(sdfFolder, "PTSans_SDF_glyphs.txt");
                bool canPatch = File.Exists(atlasPath) && File.Exists(glyphsPath);

                int patchedCount = 0;
                int skippedCount = 0;

                foreach (var fontAsset in allFontAssets)
                {
                    int fontId = fontAsset.GetInstanceID();
                    string fontName = ((UnityEngine.Object)fontAsset).name;

                    // Log basic info
                    Log.LogInfo(string.Format("  [{0}] Font: {1} (ID: {2})",
                        PatchedFontIds.Contains(fontId) ? "PATCHED" : "NEW", fontName, fontId));
                    metricsBuilder.AppendLine(string.Format("=== Font: {0} ===", fontName));
                    metricsBuilder.AppendLine(string.Format("Instance ID: {0}", fontId));
                    metricsBuilder.AppendLine(string.Format("Already Patched: {0}", PatchedFontIds.Contains(fontId)));

                    // Get and log fontInfo metrics
                    if (!object.ReferenceEquals(fontInfoProp, null))
                    {
                        try
                        {
                            object fontInfo = fontInfoProp.GetValue(fontAsset, null);
                            if (!object.ReferenceEquals(fontInfo, null))
                            {
                                Type faceInfoType = fontInfo.GetType();

                                // Log all FaceInfo fields
                                FieldInfo[] fields = faceInfoType.GetFields(BindingFlags.Public | BindingFlags.Instance);
                                foreach (var field in fields)
                                {
                                    try
                                    {
                                        object val = field.GetValue(fontInfo);
                                        string valStr = val != null ? val.ToString() : "null";

                                        // Only log important metrics to console on first run
                                        if (!FontMetricsLogged)
                                        {
                                            if (field.Name == "PointSize" || field.Name == "Scale" ||
                                                field.Name == "LineHeight" || field.Name == "Ascender" ||
                                                field.Name == "Descender" || field.Name == "AtlasWidth" ||
                                                field.Name == "AtlasHeight")
                                            {
                                                Log.LogInfo(string.Format("    {0}: {1}", field.Name, valStr));
                                            }
                                        }
                                        metricsBuilder.AppendLine(string.Format("  {0}: {1}", field.Name, valStr));
                                    }
                                    catch { }
                                }
                            }
                        }
                        catch (Exception ex)
                        {
                            Log.LogWarning(string.Format("    Error reading fontInfo: {0}", ex.Message));
                        }
                    }

                    // Get atlas info
                    try
                    {
                        FieldInfo atlasField = tmpFontAssetType.GetField("atlas", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                        if (!object.ReferenceEquals(atlasField, null))
                        {
                            Texture2D atlasTexture = atlasField.GetValue(fontAsset) as Texture2D;
                            if (!object.ReferenceEquals(atlasTexture, null))
                            {
                                metricsBuilder.AppendLine(string.Format("  Atlas Size: {0}x{1}", atlasTexture.width, atlasTexture.height));
                                metricsBuilder.AppendLine(string.Format("  Atlas Format: {0}", atlasTexture.format));
                            }
                        }
                    }
                    catch { }

                    // Get glyph count
                    try
                    {
                        FieldInfo glyphListField = tmpFontAssetType.GetField("m_glyphInfoList", BindingFlags.NonPublic | BindingFlags.Instance);
                        if (!object.ReferenceEquals(glyphListField, null))
                        {
                            var glyphList = glyphListField.GetValue(fontAsset);
                            if (!object.ReferenceEquals(glyphList, null))
                            {
                                PropertyInfo countProp = glyphList.GetType().GetProperty("Count");
                                if (!object.ReferenceEquals(countProp, null))
                                {
                                    int glyphCount = (int)countProp.GetValue(glyphList, null);
                                    metricsBuilder.AppendLine(string.Format("  Glyph Count: {0}", glyphCount));
                                }
                            }
                        }
                    }
                    catch { }

                    metricsBuilder.AppendLine();

                    // Patch the font if not already patched
                    if (!PatchedFontIds.Contains(fontId))
                    {
                        Log.LogInfo(string.Format("    Patching font {0} with Cyrillic glyphs...", fontName));
                        try
                        {
                            // Temporarily disabled bundle patching due to Array.Empty issue
                            // if (!object.ReferenceEquals(CyrillicTMPFont, null))
                            // {
                            //     PatchFontFromBundleFont(fontAsset, CyrillicTMPFont, tmpFontAssetType);
                            // }
                            // else
                            if (canPatch)
                            {
                                PatchSingleFontWithCyrillic(fontAsset, atlasPath, glyphsPath, tmpFontAssetType);
                            }
                            PatchedFontIds.Add(fontId);
                            patchedCount++;
                            Log.LogInfo(string.Format("    Font {0} patched successfully!", fontName));
                        }
                        catch (Exception ex)
                        {
                            Log.LogError(string.Format("    Error patching font {0}: {1}", fontName, ex.Message));
                        }
                    }
                    else if (PatchedFontIds.Contains(fontId))
                    {
                        skippedCount++;
                    }
                }

                // Write metrics to file
                if (!FontMetricsLogged)
                {
                    try
                    {
                        File.WriteAllText(metricsPath, metricsBuilder.ToString(), Encoding.UTF8);
                        Log.LogInfo(string.Format("Font metrics saved to: {0}", metricsPath));
                    }
                    catch (Exception ex)
                    {
                        Log.LogWarning(string.Format("Could not save font metrics: {0}", ex.Message));
                    }
                    FontMetricsLogged = true;
                }

                Log.LogInfo(string.Format("=== Font enumeration complete: {0} patched, {1} skipped (already patched) ===",
                    patchedCount, skippedCount));

                // Update CyrillicTMPFont to use the first patched font
                if (object.ReferenceEquals(CyrillicTMPFont, null) && allFontAssets.Length > 0)
                {
                    CyrillicTMPFont = allFontAssets[0];
                    Log.LogInfo(string.Format("Set CyrillicTMPFont to: {0}", ((UnityEngine.Object)CyrillicTMPFont).name));
                }
            }
            catch (Exception e)
            {
                Log.LogError(string.Format("Error in EnumerateAndPatchAllFonts: {0}", e.Message));
                Log.LogError(e.StackTrace);
            }
        }

        void PatchFontFromBundleFont(object targetFont, object sourceFont, Type tmpFontAssetType)
        {
            Log.LogInfo("      Patching from bundle font...");
            Log.LogInfo(string.Format("      Target: {0}, Source: {1}", targetFont, sourceFont));

            try
            {
                Log.LogInfo("      Step 1: Getting atlas field...");
                // Get atlas from source font
                FieldInfo atlasField = tmpFontAssetType.GetField("atlas", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                Texture2D sourceAtlas = null;
                if (!object.ReferenceEquals(atlasField, null))
                {
                    sourceAtlas = atlasField.GetValue(sourceFont) as Texture2D;
                    if (!object.ReferenceEquals(sourceAtlas, null))
                    {
                        Log.LogInfo(string.Format("      Source atlas: {0}x{1}", sourceAtlas.width, sourceAtlas.height));
                        // Set atlas on target font
                        atlasField.SetValue(targetFont, sourceAtlas);
                    }
                }

                Log.LogInfo("      Step 2: Getting material field...");
                // Get material from source and set on target
                FieldInfo materialField = tmpFontAssetType.GetField("material", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                if (!object.ReferenceEquals(materialField, null))
                {
                    Material sourceMat = materialField.GetValue(sourceFont) as Material;
                    Material targetMat = materialField.GetValue(targetFont) as Material;

                    if (!object.ReferenceEquals(sourceMat, null) && !object.ReferenceEquals(targetMat, null))
                    {
                        // Copy the atlas texture to target material
                        targetMat.mainTexture = sourceAtlas;
                        Log.LogInfo(string.Format("      Material updated with source atlas"));
                    }
                }

                Log.LogInfo("      Step 3: Getting glyph list field...");
                // Copy glyph list from source to target
                FieldInfo glyphListField = tmpFontAssetType.GetField("m_glyphInfoList", BindingFlags.NonPublic | BindingFlags.Instance);
                if (object.ReferenceEquals(glyphListField, null))
                    glyphListField = tmpFontAssetType.GetField("glyphInfoList", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);

                if (!object.ReferenceEquals(glyphListField, null))
                {
                    var sourceGlyphs = glyphListField.GetValue(sourceFont);
                    if (!object.ReferenceEquals(sourceGlyphs, null))
                    {
                        // Get target glyph list
                        var targetGlyphs = glyphListField.GetValue(targetFont);

                        if (!object.ReferenceEquals(targetGlyphs, null))
                        {
                            // Get the Add method and source list
                            Type listType = targetGlyphs.GetType();
                            MethodInfo addMethod = listType.GetMethod("Add");
                            PropertyInfo countProp = listType.GetProperty("Count");

                            // Get source items
                            var sourceList = sourceGlyphs as System.Collections.IEnumerable;
                            int addedCount = 0;

                            Log.LogInfo("      Step 4: Clearing target glyph list...");
                            // Clear target glyph list first
                            MethodInfo clearMethod = listType.GetMethod("Clear");
                            if (!object.ReferenceEquals(clearMethod, null))
                            {
                                clearMethod.Invoke(targetGlyphs, EmptyObjectArray);
                                Log.LogInfo("      Step 4a: Cleared.");
                            }

                            Log.LogInfo("      Step 5: Copying glyphs...");
                            // Copy ALL glyphs from source (both ASCII and Cyrillic)
                            foreach (var glyph in sourceList)
                            {
                                addMethod.Invoke(targetGlyphs, new object[] { glyph });
                                addedCount++;
                            }

                            Log.LogInfo(string.Format("      Replaced with {0} glyphs from bundle font", addedCount));
                        }
                    }
                }

                // Update fontInfo to match source - copy all metrics
                PropertyInfo fontInfoProp = tmpFontAssetType.GetProperty("fontInfo");
                if (!object.ReferenceEquals(fontInfoProp, null))
                {
                    object sourceFontInfo = fontInfoProp.GetValue(sourceFont, null);
                    object targetFontInfo = fontInfoProp.GetValue(targetFont, null);

                    if (!object.ReferenceEquals(sourceFontInfo, null) && !object.ReferenceEquals(targetFontInfo, null))
                    {
                        Type fiType = targetFontInfo.GetType();

                        // Copy all important metrics from source to target
                        string[] fieldsToCopy = new string[] { "PointSize", "Scale", "LineHeight", "Ascender", "Descender",
                            "CapHeight", "Baseline", "SuperscriptOffset", "SubscriptOffset", "SubSize",
                            "Underline", "UnderlineThickness", "strikethrough", "strikethroughThickness",
                            "TabWidth", "Padding", "AtlasWidth", "AtlasHeight" };

                        foreach (string fieldName in fieldsToCopy)
                        {
                            FieldInfo field = fiType.GetField(fieldName);
                            if (!object.ReferenceEquals(field, null))
                            {
                                try
                                {
                                    object val = field.GetValue(sourceFontInfo);
                                    field.SetValue(targetFontInfo, val);
                                }
                                catch { }
                            }
                        }

                        // Force atlas dimensions from actual texture
                        if (!object.ReferenceEquals(sourceAtlas, null))
                        {
                            FieldInfo awField = fiType.GetField("AtlasWidth");
                            FieldInfo ahField = fiType.GetField("AtlasHeight");
                            if (!object.ReferenceEquals(awField, null))
                            {
                                awField.SetValue(targetFontInfo, sourceAtlas.width);
                                ahField.SetValue(targetFontInfo, sourceAtlas.height);
                            }
                        }

                        Log.LogInfo("      Font metrics copied from source");
                    }
                }

                Log.LogInfo("      Bundle font patch complete");
            }
            catch (Exception ex)
            {
                Log.LogError(string.Format("      Error in PatchFontFromBundleFont: {0}", ex.Message));
                Log.LogError(ex.StackTrace);
            }
        }

        void PatchSingleFontWithCyrillic(object fontAsset, string atlasPath, string glyphsPath, Type tmpFontAssetType)
        {
            // Our glyphs are generated at this size (must match Unity TMP Font Asset PointSize)
            float ourGlyphSize = 90f;

            Log.LogInfo(string.Format("      Loading atlas: {0}", atlasPath));
            Log.LogInfo(string.Format("      Loading glyphs: {0}", glyphsPath));

            // Read glyph file
            var glyphFileLines = File.ReadAllLines(glyphsPath);
            Log.LogInfo(string.Format("      Glyph file lines: {0}", glyphFileLines.Length));

            Texture2D atlas;

            // Load PNG atlas and convert to Alpha8 format (bundle atlas disabled due to TMP version mismatch)
            Log.LogInfo(string.Format("      Loading PNG atlas: {0}", atlasPath));
            Texture2D tempAtlas = new Texture2D(2, 2);
            byte[] atlasData = File.ReadAllBytes(atlasPath);
            tempAtlas.LoadImage(atlasData);
            Log.LogInfo(string.Format("      Loaded PNG: {0}x{1}", tempAtlas.width, tempAtlas.height));

            // Convert to Alpha8
            atlas = new Texture2D(tempAtlas.width, tempAtlas.height, TextureFormat.Alpha8, false);
            Color[] pixels = tempAtlas.GetPixels();
            byte[] alphaData = new byte[pixels.Length];
            for (int i = 0; i < pixels.Length; i++)
            {
                alphaData[i] = (byte)(pixels[i].r * 255f);
            }
            atlas.LoadRawTextureData(alphaData);
            atlas.Apply();

            // Set texture filtering for crisp SDF rendering
            atlas.filterMode = FilterMode.Bilinear;
            atlas.wrapMode = TextureWrapMode.Clamp;

            // Get material and replace texture
            FieldInfo materialField = tmpFontAssetType.GetField("material", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            if (!object.ReferenceEquals(materialField, null))
            {
                Material mat = materialField.GetValue(fontAsset) as Material;
                if (!object.ReferenceEquals(mat, null))
                {
                    mat.mainTexture = atlas;

                    // Adjust shader parameters for smoother rendering
                    if (mat.HasProperty("_FaceDilate"))
                        mat.SetFloat("_FaceDilate", 0.1f);  // Slightly expand face for smoother edges
                    if (mat.HasProperty("_OutlineSoftness"))
                        mat.SetFloat("_OutlineSoftness", 0.1f);  // Soften outline
                    if (mat.HasProperty("_FaceSoftness"))
                        mat.SetFloat("_FaceSoftness", 0.02f);  // Soften face edges

                    Log.LogInfo(string.Format("      Material shader: {0}", mat.shader.name));
                }
            }

            // Set atlas field
            FieldInfo atlasField = tmpFontAssetType.GetField("atlas", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            if (!object.ReferenceEquals(atlasField, null))
            {
                atlasField.SetValue(fontAsset, atlas);
            }

            // Update fontInfo to match our generation parameters
            PropertyInfo fontInfoProp = tmpFontAssetType.GetProperty("fontInfo");
            if (!object.ReferenceEquals(fontInfoProp, null))
            {
                try
                {
                    object fontInfo = fontInfoProp.GetValue(fontAsset, null);
                    if (!object.ReferenceEquals(fontInfo, null))
                    {
                        Type fiType = fontInfo.GetType();

                        // Read original values for proportional scaling
                        float origPointSize = 90f;
                        FieldInfo psField = fiType.GetField("PointSize");
                        if (!object.ReferenceEquals(psField, null))
                            origPointSize = Convert.ToSingle(psField.GetValue(fontInfo));

                        float scaleRatio = ourGlyphSize / origPointSize;

                        // Update PointSize to our generation size
                        if (!object.ReferenceEquals(psField, null))
                            psField.SetValue(fontInfo, ourGlyphSize);

                        // Update atlas dimensions
                        FieldInfo awField = fiType.GetField("AtlasWidth");
                        FieldInfo ahField = fiType.GetField("AtlasHeight");
                        if (!object.ReferenceEquals(awField, null))
                            awField.SetValue(fontInfo, atlas.width);
                        if (!object.ReferenceEquals(ahField, null))
                            ahField.SetValue(fontInfo, atlas.height);

                        // Scale font metrics proportionally
                        ScaleFontInfoField(fiType, fontInfo, "LineHeight", scaleRatio);
                        ScaleFontInfoField(fiType, fontInfo, "Ascender", scaleRatio);
                        ScaleFontInfoField(fiType, fontInfo, "Descender", scaleRatio);
                        ScaleFontInfoField(fiType, fontInfo, "CapHeight", scaleRatio);
                        ScaleFontInfoField(fiType, fontInfo, "Baseline", scaleRatio);
                        ScaleFontInfoField(fiType, fontInfo, "UnderlineOffset", scaleRatio);
                        ScaleFontInfoField(fiType, fontInfo, "UnderlineThickness", scaleRatio);
                        ScaleFontInfoField(fiType, fontInfo, "strikethroughOffset", scaleRatio);
                        ScaleFontInfoField(fiType, fontInfo, "strikethroughThickness", scaleRatio);
                        ScaleFontInfoField(fiType, fontInfo, "TabWidth", scaleRatio);
                        ScaleFontInfoField(fiType, fontInfo, "Padding", scaleRatio);
                    }
                }
                catch (Exception ex)
                {
                    Log.LogWarning(string.Format("Could not update fontInfo: {0}", ex.Message));
                }
            }

            // Find TMP_Glyph type
            Type tmpGlyphType = null;
            foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
            {
                tmpGlyphType = assembly.GetType("TMPro.TMP_Glyph");
                if (!object.ReferenceEquals(tmpGlyphType, null)) break;
            }

            if (object.ReferenceEquals(tmpGlyphType, null))
            {
                Log.LogWarning("TMP_Glyph type not found");
                return;
            }

            // Get glyph list
            FieldInfo glyphListField = tmpFontAssetType.GetField("m_glyphInfoList", BindingFlags.NonPublic | BindingFlags.Instance);
            if (object.ReferenceEquals(glyphListField, null)) return;

            var glyphList = glyphListField.GetValue(fontAsset);
            MethodInfo addMethod = glyphList.GetType().GetMethod("Add");
            MethodInfo clearMethod = glyphList.GetType().GetMethod("Clear");

            // Build a set of unicode values we have in our glyph file
            HashSet<int> ourUnicodes = new HashSet<int>();
            foreach (var line in glyphFileLines)
            {
                if (!line.StartsWith("char=")) continue;
                var parts = line.Split('\t');
                foreach (var part in parts)
                {
                    if (part.StartsWith("unicode="))
                    {
                        int val;
                        if (int.TryParse(part.Substring(8), out val))
                            ourUnicodes.Add(val);
                        break;
                    }
                }
            }

            // Store original glyphs for characters we DON'T have (like € euro sign)
            var originalGlyphs = new System.Collections.Generic.List<object>();
            var glyphListEnumerator = ((System.Collections.IEnumerable)glyphList).GetEnumerator();
            FieldInfo glyphIdField = tmpGlyphType.GetField("id") ?? tmpGlyphType.GetField("m_id");

            while (glyphListEnumerator.MoveNext())
            {
                object glyph = glyphListEnumerator.Current;
                if (!object.ReferenceEquals(glyphIdField, null))
                {
                    int glyphId = Convert.ToInt32(glyphIdField.GetValue(glyph));
                    // Keep glyphs for characters we don't have in our atlas
                    // This preserves € (8364) and other special characters
                    if (!ourUnicodes.Contains(glyphId))
                    {
                        originalGlyphs.Add(glyph);
                    }
                }
            }
            Log.LogInfo(string.Format("      Preserving {0} original glyphs (including € euro)", originalGlyphs.Count));

            // Clear glyphs - we'll add back original ones we want to keep
            clearMethod.Invoke(glyphList, EmptyObjectArray);

            // Re-add preserved original glyphs
            foreach (var glyph in originalGlyphs)
            {
                addMethod.Invoke(glyphList, new object[] { glyph });
            }

            // Add ALL glyphs from our Unity-exported file (both ASCII and Cyrillic)
            int addedGlyphs = 0;
            foreach (var line in glyphFileLines)
            {
                if (!line.StartsWith("char=")) continue;

                try
                {
                    var parts = line.Split('\t');
                    int unicode = 0;
                    float x = 0, y = 0, w = 0, h = 0, bx = 0, by = 0, adv = 0;

                    foreach (var part in parts)
                    {
                        if (part.StartsWith("unicode=")) unicode = int.Parse(part.Substring(8));
                        else if (part.StartsWith("x=")) x = float.Parse(part.Substring(2));
                        else if (part.StartsWith("y=")) y = float.Parse(part.Substring(2));
                        else if (part.StartsWith("w=")) w = float.Parse(part.Substring(2));
                        else if (part.StartsWith("h=")) h = float.Parse(part.Substring(2));
                        else if (part.StartsWith("bx=")) bx = float.Parse(part.Substring(3));
                        else if (part.StartsWith("by=")) by = float.Parse(part.Substring(3));
                        else if (part.StartsWith("adv=")) adv = float.Parse(part.Substring(4));
                    }

                    // Add ALL glyphs - both ASCII and Cyrillic
                    if (unicode > 0)
                    {
                        var glyph = Activator.CreateInstance(tmpGlyphType);
                        SetFieldValue(tmpGlyphType, glyph, "id", unicode);
                        // All values as-is - fontInfo.PointSize now matches our generation size
                        SetFieldValue(tmpGlyphType, glyph, "x", x);
                        SetFieldValue(tmpGlyphType, glyph, "y", y);
                        SetFieldValue(tmpGlyphType, glyph, "width", w);
                        SetFieldValue(tmpGlyphType, glyph, "height", h);
                        SetFieldValue(tmpGlyphType, glyph, "xOffset", bx);
                        SetFieldValue(tmpGlyphType, glyph, "yOffset", by);
                        SetFieldValue(tmpGlyphType, glyph, "xAdvance", adv);
                        SetFieldValue(tmpGlyphType, glyph, "scale", 1.0f);

                        addMethod.Invoke(glyphList, new object[] { glyph });
                        addedGlyphs++;
                    }
                }
                catch { }
            }

            // Rebuild character dictionary
            MethodInfo readFontDef = tmpFontAssetType.GetMethod("ReadFontDefinition", BindingFlags.Public | BindingFlags.Instance);
            if (!object.ReferenceEquals(readFontDef, null))
            {
                readFontDef.Invoke(fontAsset, EmptyObjectArray);
            }
        }

        void ScaleFontInfoField(Type fiType, object fontInfo, string fieldName, float scale)
        {
            try
            {
                FieldInfo field = fiType.GetField(fieldName);
                if (!object.ReferenceEquals(field, null))
                {
                    float val = Convert.ToSingle(field.GetValue(fontInfo));
                    field.SetValue(fontInfo, val * scale);
                }
            }
            catch { }
        }

        private static HashSet<int> ReplacedDialogueIds = new HashSet<int>();
        private static Type DialogObjectScriptType = null;
        private static FieldInfo[] DialogStringFields = null;
        private static bool PassageDumpDone = true; // Set to false to re-enable dump

        // Raw Russian content blocks per file base name (e.g. "001_patricia" -> list of content blocks)
        // Each block is a list of lines between nav markers in the raw file
        internal static Dictionary<string, List<List<string>>> RawRussianBlocks = new Dictionary<string, List<List<string>>>();
        // Track which block index we've consumed per file for sequential fallback
        internal static Dictionary<string, int> RawBlockIndex = new Dictionary<string, int>();
        // Set of all known passage titles (loaded from dump file)
        internal static HashSet<string> AllKnownPassageTitles = new HashSet<string>();

        // Passage-based translation: passage_title -> list of Russian lines
        internal static Dictionary<string, List<string>> RussianPassages = new Dictionary<string, List<string>>();
        // Each choice: (display_text, link_target, emote)
        internal static Dictionary<string, List<string[]>> RussianChoices = new Dictionary<string, List<string[]>>();
        // Global link -> list of russian choice texts (across all passages)
        internal static Dictionary<string, List<string>> GlobalLinkToChoiceTexts = new Dictionary<string, List<string>>();

        void ReplaceTextAssetsInMemory()
        {
            if (DialogueTexts.Count == 0) return;

            try
            {
                // Phase 1: Replace DialogObjectScript instances (MonoBehaviours with dialogue data)
                ReplaceDialogueObjects();

                // Phase 2: Replace TextAssets for 9xx files (stored as TextAssets in sharedassets)
                ReplaceTextAssetContents();
            }
            catch (Exception e)
            {
                Log.LogError(string.Format("[Replace] Error: {0}", e));
            }
        }

        void ReplaceDialogueObjects()
        {
            try
            {
                if (RussianPassages.Count == 0)
                {
                    Log.LogWarning("[DialogObj] No Russian passages parsed");
                    return;
                }

                // Find NC.Dialogs.DialogObjectScript type
                if (object.ReferenceEquals(DialogObjectScriptType, null))
                {
                    foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
                    {
                        try
                        {
                            DialogObjectScriptType = asm.GetType("NC.Dialogs.DialogObjectScript");
                            if (!object.ReferenceEquals(DialogObjectScriptType, null))
                            {
                                Log.LogInfo(string.Format("[DialogObj] Found type: {0}", DialogObjectScriptType.FullName));
                                break;
                            }
                        }
                        catch { }
                    }
                }

                if (object.ReferenceEquals(DialogObjectScriptType, null))
                {
                    Log.LogWarning("[DialogObj] NC.Dialogs.DialogObjectScript not found");
                    return;
                }

                var allObjects = Resources.FindObjectsOfTypeAll(DialogObjectScriptType);
                int total = allObjects.Length;

                FieldInfo dialogsListField = DialogObjectScriptType.GetField("dialogs",
                    BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                if (object.ReferenceEquals(dialogsListField, null))
                {
                    Log.LogWarning("[DialogObj] No 'dialogs' field found");
                    return;
                }

                // Cache reflection fields (resolved once)
                Type i18nType = null;
                FieldInfo langField = null;
                FieldInfo dialogField = null;
                Type dialogType = null;
                FieldInfo passagesField = null;
                Type passageSectionType = null;
                FieldInfo titleField = null;
                FieldInfo linesField = null;
                FieldInfo choicesField = null;
                Type choiceType = null;
                FieldInfo choiceTextField = null;
                FieldInfo choiceLinkField = null;

                // === DUMP PASS: log all passage titles from all DialogObjectScripts (once) ===
                if (!PassageDumpDone)
                {
                    PassageDumpDone = true;
                    Log.LogInfo(string.Format("[DUMP] Starting passage dump for {0} DialogObjectScript objects", allObjects.Length));

                    // We need to resolve types for the dump pass
                    Type dumpI18nType = null;
                    FieldInfo dumpLangField = null;
                    FieldInfo dumpDialogField = null;
                    Type dumpDialogType = null;
                    FieldInfo dumpPassagesField = null;
                    Type dumpPassageSectionType = null;
                    FieldInfo dumpTitleField = null;
                    FieldInfo dumpLinesField = null;
                    FieldInfo dumpChoicesField = null;

                    foreach (var obj in allObjects)
                    {
                        if (obj == null) continue;
                        string dObjName = obj.name;
                        if (string.IsNullOrEmpty(dObjName)) continue;

                        object dDialogsList = dialogsListField.GetValue(obj);
                        System.Collections.IList dI18nList = dDialogsList as System.Collections.IList;
                        if (dI18nList == null || dI18nList.Count == 0) continue;

                        // Find English Dialog
                        object dEngDialogObj = null;
                        for (int i = 0; i < dI18nList.Count; i++)
                        {
                            object item = dI18nList[i];
                            if (object.ReferenceEquals(item, null)) continue;
                            if (object.ReferenceEquals(dumpI18nType, null))
                            {
                                dumpI18nType = item.GetType();
                                dumpLangField = dumpI18nType.GetField("lang", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                                dumpDialogField = dumpI18nType.GetField("dialog", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                            }
                            if (object.ReferenceEquals(dumpLangField, null)) break;
                            object lv = dumpLangField.GetValue(item);
                            if (!object.ReferenceEquals(lv, null) && lv.ToString() == "eng")
                            {
                                if (!object.ReferenceEquals(dumpDialogField, null))
                                    dEngDialogObj = dumpDialogField.GetValue(item);
                                break;
                            }
                        }
                        if (object.ReferenceEquals(dEngDialogObj, null)) continue;

                        if (object.ReferenceEquals(dumpDialogType, null))
                        {
                            dumpDialogType = dEngDialogObj.GetType();
                            dumpPassagesField = dumpDialogType.GetField("_passages", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                        }
                        if (object.ReferenceEquals(dumpPassagesField, null)) continue;

                        System.Collections.IList dPassages = dumpPassagesField.GetValue(dEngDialogObj) as System.Collections.IList;
                        if (dPassages == null || dPassages.Count == 0) continue;

                        if (object.ReferenceEquals(dumpPassageSectionType, null))
                        {
                            dumpPassageSectionType = dPassages[0].GetType();
                            dumpTitleField = dumpPassageSectionType.GetField("_title", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                            dumpLinesField = dumpPassageSectionType.GetField("_lines", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                            dumpChoicesField = dumpPassageSectionType.GetField("_choices", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                        }

                        Log.LogInfo(string.Format("[DUMP] obj='{0}' passages={1}", dObjName, dPassages.Count));

                        for (int pi = 0; pi < dPassages.Count; pi++)
                        {
                            object ps = dPassages[pi];
                            if (object.ReferenceEquals(ps, null)) continue;

                            object tObj = !object.ReferenceEquals(dumpTitleField, null) ? dumpTitleField.GetValue(ps) : null;
                            string pTitle = tObj != null ? tObj.ToString() : "?";

                            object lObj = !object.ReferenceEquals(dumpLinesField, null) ? dumpLinesField.GetValue(ps) : null;
                            System.Collections.IList pLines = lObj as System.Collections.IList;
                            int lineCount = pLines != null ? pLines.Count : 0;

                            int choiceCount = 0;
                            if (!object.ReferenceEquals(dumpChoicesField, null))
                            {
                                object cObj = dumpChoicesField.GetValue(ps);
                                System.Collections.IList cList = cObj as System.Collections.IList;
                                if (cList != null) choiceCount = cList.Count;
                            }

                            // Get first 2 non-command lines for matching
                            string first = "";
                            string second = "";
                            if (pLines != null)
                            {
                                int found = 0;
                                for (int li = 0; li < pLines.Count && found < 2; li++)
                                {
                                    string ln = pLines[li] as string;
                                    if (ln == null) continue;
                                    string lt = ln.Trim();
                                    if (lt.StartsWith("$$") || lt.Length == 0) continue;
                                    if (found == 0) first = lt;
                                    else second = lt;
                                    found++;
                                }
                            }

                            // Truncate for log readability
                            if (first.Length > 80) first = first.Substring(0, 80);
                            if (second.Length > 80) second = second.Substring(0, 80);

                            Log.LogInfo(string.Format("[DUMP]   p='{0}' lines={1} choices={2} first='{3}'",
                                pTitle, lineCount, choiceCount, first));
                            if (second.Length > 0)
                                Log.LogInfo(string.Format("[DUMP]   p='{0}' second='{1}'", pTitle, second));
                        }
                    }
                    Log.LogInfo("[DUMP] Passage dump complete");

                    // Save dump to persistent file
                    try
                    {
                        string dumpPath = Path.Combine(Path.GetDirectoryName(Application.dataPath), "passage_dump.txt");
                        using (var sw = new System.IO.StreamWriter(dumpPath, false, Encoding.UTF8))
                        {
                            foreach (var obj2 in allObjects)
                            {
                                if (obj2 == null) continue;
                                string dn = obj2.name;
                                if (string.IsNullOrEmpty(dn)) continue;

                                object dl2 = dialogsListField.GetValue(obj2);
                                System.Collections.IList il2 = dl2 as System.Collections.IList;
                                if (il2 == null || il2.Count == 0) continue;

                                object engD2 = null;
                                for (int i = 0; i < il2.Count; i++)
                                {
                                    object item = il2[i];
                                    if (object.ReferenceEquals(item, null)) continue;
                                    object lv = dumpLangField.GetValue(item);
                                    if (!object.ReferenceEquals(lv, null) && lv.ToString() == "eng")
                                    {
                                        engD2 = dumpDialogField.GetValue(item);
                                        break;
                                    }
                                }
                                if (object.ReferenceEquals(engD2, null)) continue;

                                System.Collections.IList dp2 = dumpPassagesField.GetValue(engD2) as System.Collections.IList;
                                if (dp2 == null || dp2.Count == 0) continue;

                                sw.WriteLine(string.Format("OBJ {0} {1}", dn, dp2.Count));
                                for (int pi = 0; pi < dp2.Count; pi++)
                                {
                                    object ps2 = dp2[pi];
                                    if (object.ReferenceEquals(ps2, null)) continue;
                                    object tObj2 = dumpTitleField.GetValue(ps2);
                                    string pT = tObj2 != null ? tObj2.ToString() : "?";

                                    object lObj2 = dumpLinesField.GetValue(ps2);
                                    System.Collections.IList pL2 = lObj2 as System.Collections.IList;
                                    int lc = pL2 != null ? pL2.Count : 0;

                                    int cc = 0;
                                    object cObj2 = dumpChoicesField.GetValue(ps2);
                                    System.Collections.IList cL2 = cObj2 as System.Collections.IList;
                                    if (cL2 != null) cc = cL2.Count;

                                    sw.WriteLine(string.Format("P {0} {1} {2}", pT, lc, cc));
                                    // Write all English lines
                                    if (pL2 != null)
                                    {
                                        for (int li2 = 0; li2 < pL2.Count; li2++)
                                        {
                                            string eline = pL2[li2] as string;
                                            if (eline == null) eline = "";
                                            sw.WriteLine(string.Format("L {0}", eline));
                                        }
                                    }
                                    // Write all choice texts
                                    if (cL2 != null)
                                    {
                                        for (int ci2 = 0; ci2 < cL2.Count; ci2++)
                                        {
                                            object choiceObj = cL2[ci2];
                                            if (object.ReferenceEquals(choiceObj, null)) continue;
                                            if (object.ReferenceEquals(choiceType, null))
                                            {
                                                choiceType = choiceObj.GetType();
                                                choiceTextField = choiceType.GetField("_text", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                                                choiceLinkField = choiceType.GetField("_link", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                                            }
                                            string cText = "";
                                            string cLink = "";
                                            if (!object.ReferenceEquals(choiceTextField, null))
                                            {
                                                object ctObj = choiceTextField.GetValue(choiceObj);
                                                if (ctObj != null) cText = ctObj.ToString();
                                            }
                                            if (!object.ReferenceEquals(choiceLinkField, null))
                                            {
                                                object clObj = choiceLinkField.GetValue(choiceObj);
                                                if (clObj != null) cLink = clObj.ToString();
                                            }
                                            sw.WriteLine(string.Format("C {0}\t{1}", cText, cLink));
                                        }
                                    }
                                }
                            }
                        }
                        Log.LogInfo(string.Format("[DUMP] Saved to {0}", dumpPath));
                    }
                    catch (Exception ex)
                    {
                        Log.LogError(string.Format("[DUMP] Failed to save: {0}", ex.Message));
                    }
                }
                // === END DUMP PASS ===

                int replacedPassages = 0;
                int replacedObjects = 0;
                int skippedObjects = 0;

                foreach (var obj in allObjects)
                {
                    if (obj == null) continue;
                    int id = obj.GetInstanceID();
                    if (ReplacedDialogueIds.Contains(id))
                    {
                        skippedObjects++;
                        continue;
                    }
                    ReplacedDialogueIds.Add(id);

                    string objName = obj.name;
                    if (string.IsNullOrEmpty(objName)) continue;

                    // Get dialogs list
                    object dialogsList = dialogsListField.GetValue(obj);
                    System.Collections.IList i18nList = dialogsList as System.Collections.IList;
                    if (i18nList == null || i18nList.Count == 0) continue;

                    // Find English Dialog object
                    object engDialogObj = null;
                    for (int i = 0; i < i18nList.Count; i++)
                    {
                        object item = i18nList[i];
                        if (object.ReferenceEquals(item, null)) continue;

                        // Resolve types once
                        if (object.ReferenceEquals(i18nType, null))
                        {
                            i18nType = item.GetType();
                            langField = i18nType.GetField("lang", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                            dialogField = i18nType.GetField("dialog", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                        }

                        if (object.ReferenceEquals(langField, null)) break;

                        object lv = langField.GetValue(item);
                        if (!object.ReferenceEquals(lv, null) && lv.ToString() == "eng")
                        {
                            if (!object.ReferenceEquals(dialogField, null))
                                engDialogObj = dialogField.GetValue(item);
                            break;
                        }
                    }

                    if (object.ReferenceEquals(engDialogObj, null)) continue;

                    // Resolve Dialog type fields once
                    if (object.ReferenceEquals(dialogType, null))
                    {
                        dialogType = engDialogObj.GetType();
                        passagesField = dialogType.GetField("_passages",
                            BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                    }

                    if (object.ReferenceEquals(passagesField, null)) continue;

                    System.Collections.IList passages = passagesField.GetValue(engDialogObj) as System.Collections.IList;
                    if (passages == null || passages.Count == 0) continue;

                    // Resolve PassageSection type fields once
                    if (object.ReferenceEquals(passageSectionType, null))
                    {
                        passageSectionType = passages[0].GetType();
                        titleField = passageSectionType.GetField("_title",
                            BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                        linesField = passageSectionType.GetField("_lines",
                            BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                        choicesField = passageSectionType.GetField("_choices",
                            BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                    }

                    if (object.ReferenceEquals(titleField, null) || object.ReferenceEquals(linesField, null)) continue;

                    // Log first passage's original English lines for diagnostics (once)
                    if (replacedObjects == 0 && passages.Count > 0)
                    {
                        // Find a passage with dialogue lines (not just commands)
                        for (int dpi = 0; dpi < Math.Min(5, passages.Count); dpi++)
                        {
                            object dps = passages[dpi];
                            if (object.ReferenceEquals(dps, null)) continue;
                            object dlo = linesField.GetValue(dps);
                            System.Collections.IList dll = dlo as System.Collections.IList;
                            if (dll == null || dll.Count == 0) continue;
                            object dto = titleField.GetValue(dps);
                            string dtitle = dto != null ? dto.ToString() : "?";
                            Log.LogInfo(string.Format("[ENG_LINES] Passage '{0}' has {1} lines:", dtitle, dll.Count));
                            for (int dli = 0; dli < Math.Min(15, dll.Count); dli++)
                            {
                                string dline = dll[dli] as string;
                                if (dline == null) dline = "null";
                                Log.LogInfo(string.Format("[ENG_LINES]   [{0}] {1}", dli, dline));
                            }
                            break;
                        }
                    }

                    // Compute object base name for per-object passage lookup
                    // e.g., "034_phil_01" -> "034_phil", "068_sonny_02" -> "068_sonny"
                    string objBase = objName;
                    {
                        int lastUs = objBase.LastIndexOf('_');
                        if (lastUs > 0)
                        {
                            string suffix = objBase.Substring(lastUs + 1);
                            int dummy;
                            if (int.TryParse(suffix, out dummy))
                                objBase = objBase.Substring(0, lastUs);
                        }
                    }

                    // Replace lines per-passage with per-passage speaker mapping
                    int objReplacedCount = 0;
                    for (int pi = 0; pi < passages.Count; pi++)
                    {
                        object ps = passages[pi];
                        if (object.ReferenceEquals(ps, null)) continue;

                        object titleObj = titleField.GetValue(ps);
                        if (object.ReferenceEquals(titleObj, null)) continue;
                        string passageTitle = titleObj.ToString();

                        // Per-object qualified lookup first (prevents cross-contamination
                        // of shared passages like customer-add-clue-outro between passengers)
                        List<string> russianLines = null;
                        RussianPassages.TryGetValue(objBase + ":" + passageTitle, out russianLines);
                        if (russianLines == null)
                            RussianPassages.TryGetValue(passageTitle, out russianLines);
                        if (russianLines == null)
                        {
                            // Sequential fallback: try raw Russian blocks
                            // Find the base name for this object (e.g., "001_patricia" from "001_patricia_02")
                            string fallbackBase = null;
                            // Try exact object name first
                            if (RawRussianBlocks.ContainsKey(objName))
                                fallbackBase = objName;
                            else
                            {
                                // Try without suffix: "001_patricia_02" -> "001_patricia"
                                int lastUnderscore = objName.LastIndexOf('_');
                                if (lastUnderscore > 0)
                                {
                                    string shorter = objName.Substring(0, lastUnderscore);
                                    if (RawRussianBlocks.ContainsKey(shorter))
                                        fallbackBase = shorter;
                                }
                            }

                            if (fallbackBase != null)
                            {
                                int blockIdx;
                                if (!RawBlockIndex.TryGetValue(fallbackBase, out blockIdx))
                                    blockIdx = 0;
                                var blocks = RawRussianBlocks[fallbackBase];
                                if (blockIdx < blocks.Count)
                                {
                                    russianLines = blocks[blockIdx];
                                    RawBlockIndex[fallbackBase] = blockIdx + 1;
                                    if (replacedObjects < 5)
                                        Log.LogInfo(string.Format("[SeqFallback] obj='{0}' passage='{1}' -> block {2}/{3} ({4} lines)",
                                            objName, passageTitle, blockIdx, blocks.Count, russianLines.Count));
                                }
                            }

                            if (russianLines == null)
                            {
                                // Line-by-line translation fallback: translate each English line individually
                                object fbLinesObj = linesField.GetValue(ps);
                                System.Collections.IList fbLines = fbLinesObj as System.Collections.IList;
                                if (fbLines != null && fbLines.Count > 0 && Translations.Count > 0)
                                {
                                    var translated = new List<string>();
                                    int translatedCount = 0;
                                    for (int fli = 0; fli < fbLines.Count; fli++)
                                    {
                                        string engLine = fbLines[fli] as string;
                                        if (engLine == null) { translated.Add(""); continue; }
                                        string ruLine = TranslateText(engLine);
                                        if (!object.ReferenceEquals(ruLine, null))
                                        {
                                            translated.Add(ruLine);
                                            translatedCount++;
                                        }
                                        else
                                        {
                                            translated.Add(engLine);
                                        }
                                    }
                                    if (translatedCount > 0)
                                    {
                                        russianLines = translated;
                                        if (replacedObjects < 5)
                                            Log.LogInfo(string.Format("[LineFallback] obj='{0}' passage='{1}' translated {2}/{3} lines",
                                                objName, passageTitle, translatedCount, fbLines.Count));
                                    }
                                }

                                if (russianLines == null)
                                {
                                    if (replacedObjects < 10)
                                        Log.LogWarning(string.Format("[PassageMiss] obj='{0}' passage='{1}' not in RussianPassages",
                                            objName, passageTitle));
                                    continue;
                                }
                            }
                        }

                        object origLinesObj = linesField.GetValue(ps);
                        System.Collections.IList origLines = origLinesObj as System.Collections.IList;
                        if (origLines == null) continue;

                        // Extract English speakers from THIS passage's original lines (ordered, unique)
                        List<string> engSpkList = new List<string>();
                        Dictionary<string, bool> engSpkSet = new Dictionary<string, bool>();
                        for (int li = 0; li < origLines.Count; li++)
                        {
                            string el = origLines[li] as string;
                            if (el == null) continue;
                            string sp = ExtractSpeakerName(el);
                            if (sp != null && !engSpkSet.ContainsKey(sp))
                            {
                                engSpkSet[sp] = true;
                                engSpkList.Add(sp);
                            }
                        }

                        // Extract Russian speakers from the replacement lines (ordered, unique)
                        List<string> ruSpkList = new List<string>();
                        Dictionary<string, bool> ruSpkSet = new Dictionary<string, bool>();
                        foreach (string rl in russianLines)
                        {
                            string sp = ExtractSpeakerName(rl);
                            if (sp != null && !ruSpkSet.ContainsKey(sp))
                            {
                                ruSpkSet[sp] = true;
                                ruSpkList.Add(sp);
                            }
                        }

                        // Map Russian -> English by discovery order within this passage
                        Dictionary<string, string> passageRuToEng = new Dictionary<string, string>();
                        for (int si = 0; si < ruSpkList.Count && si < engSpkList.Count; si++)
                        {
                            passageRuToEng[ruSpkList[si]] = engSpkList[si];
                        }

                        // Log diagnostics for unmapped speakers
                        if (engSpkList.Count == 0 && ruSpkList.Count > 0 && replacedObjects < 3)
                        {
                            Log.LogInfo(string.Format("[Passage] '{0}' eng:0 ru:{1} - TESTING ExtractSpeakerName:", passageTitle, ruSpkList.Count));
                            for (int li = 0; li < Math.Min(10, origLines.Count); li++)
                            {
                                string el = origLines[li] as string;
                                if (el == null) continue;
                                string testSp = ExtractSpeakerName(el);
                                if (el.IndexOf(":") >= 0)
                                    Log.LogInfo(string.Format("[Passage]   [{0}] has colon, extract='{1}', line='{2}'", li, testSp ?? "NULL", el.Substring(0, Math.Min(60, el.Length))));
                            }
                        }

                        // Detect separator format from ORIGINAL ENGLISH lines
                        // Game parser is format-sensitive: "NAME: " vs "NAME : " per dialogue object
                        bool engSpaceColon = false;
                        for (int li = 0; li < origLines.Count; li++)
                        {
                            string el = origLines[li] as string;
                            if (el == null) continue;
                            if (el.IndexOf(" : \"") >= 0 || el.IndexOf(" : \u00ab") >= 0 ||
                                el.IndexOf(" : \u201c") >= 0 || el.IndexOf(" : \u2018") >= 0)
                            { engSpaceColon = true; break; }
                            if (el.IndexOf(": \"") >= 0 || el.IndexOf(": \u00ab") >= 0 ||
                                el.IndexOf(": \u201c") >= 0 || el.IndexOf(": \u2018") >= 0)
                            { engSpaceColon = false; break; }
                        }
                        string engSep = engSpaceColon ? " : " : ": ";

                        origLines.Clear();
                        foreach (string rl in russianLines)
                        {
                            string processedLine = rl;

                            // Navigation data: pass through as-is (preserve Ink engine conditionals)
                            if (processedLine.Contains(";;"))
                            {
                                origLines.Add(processedLine);
                                continue;
                            }

                            // Choice echo artifact: strip emote tag prefix (:silence:, :anger:, etc.)
                            if (processedLine.StartsWith(":"))
                            {
                                int emoteEnd = processedLine.IndexOf(":", 1);
                                if (emoteEnd > 0)
                                {
                                    string afterEmote = processedLine.Substring(emoteEnd + 1).Trim();
                                    if (afterEmote.Length > 0)
                                        processedLine = afterEmote;
                                }
                            }

                            // Use ENGLISH speaker name so the game's dialogue parser recognizes it
                            // (game parser only accepts Latin uppercase names for dialogue rendering)
                            // TMP_Text interceptor will translate the displayed name to Russian via JSON
                            string ruSp = ExtractSpeakerName(rl);
                            if (ruSp != null)
                            {
                                string textPart = ExtractSpeakerText(rl);
                                if (textPart != null)
                                {
                                    string engSp;
                                    if (!passageRuToEng.TryGetValue(ruSp, out engSp))
                                    {
                                        // Global fallback: reverse lookup from full_translation_mapping.json
                                        if (!RuToEngSpeaker.TryGetValue(ruSp, out engSp))
                                            engSp = ruSp; // last resort: keep Russian
                                    }
                                    processedLine = engSp + engSep + textPart;
                                }
                            }
                            else
                            {
                                string t = processedLine.Trim();
                                if (t.Length > 0 && !t.StartsWith("$$"))
                                {
                                    // Check for unquoted speaker line: "NAME: text" without quotes
                                    // Some Russian text files omit quotes around speaker dialogue
                                    string unqName = null;
                                    int unqIdx = t.IndexOf(": ");
                                    if (unqIdx > 0 && unqIdx <= 30)
                                    {
                                        string nm = t.Substring(0, unqIdx).Trim();
                                        if (nm.Length >= 2 && nm.Length <= 30)
                                        {
                                            bool nmOk = true;
                                            for (int ci = 0; ci < nm.Length; ci++)
                                            {
                                                char c = nm[ci];
                                                if (!char.IsUpper(c) && c != '-' && c != ' ')
                                                { nmOk = false; break; }
                                            }
                                            if (nmOk && (RuToEngSpeaker.ContainsKey(nm) || passageRuToEng.ContainsKey(nm)))
                                                unqName = nm;
                                        }
                                    }

                                    if (unqName != null)
                                    {
                                        // Unquoted speaker — restore English name, add quotes
                                        string engN;
                                        if (!passageRuToEng.TryGetValue(unqName, out engN))
                                        {
                                            if (!RuToEngSpeaker.TryGetValue(unqName, out engN))
                                                engN = unqName;
                                        }
                                        string txt = t.Substring(unqIdx + 2).Trim();
                                        // Strip leading em-dash or stray single quote
                                        if (txt.StartsWith("\u2014") || txt.StartsWith("\u2013"))
                                            txt = txt.Substring(1).Trim();
                                        if (txt.StartsWith("'"))
                                            txt = txt.Substring(1).Trim();
                                        processedLine = engN + engSep + "\"" + txt + "\"";
                                    }
                                    else if (t.StartsWith("\"") || t.StartsWith("\u201c"))
                                    {
                                        // Driver speech: convert "..." to « ... » so game parser
                                        // recognizes it as dialogue (not narration)
                                        string inner = t.Substring(1);
                                        if (inner.EndsWith("\"") || inner.EndsWith("\u201d"))
                                            inner = inner.Substring(0, inner.Length - 1);
                                        else if (inner.Length > 1)
                                        {
                                            int lastQ = inner.LastIndexOf('"');
                                            if (lastQ < 0) lastQ = inner.LastIndexOf('\u201d');
                                            if (lastQ >= 0)
                                                inner = inner.Substring(0, lastQ) + inner.Substring(lastQ + 1);
                                        }
                                        processedLine = "\u00ab " + inner.Trim() + " \u00bb";
                                    }
                                    else if (!t.StartsWith("\u00ab"))
                                    {
                                        // Narrative line — wrap in italic
                                        processedLine = "<i>" + processedLine + "</i>";
                                    }
                                }
                            }

                            origLines.Add(processedLine);
                        }

                        // Replace choices for this passage
                        if (!object.ReferenceEquals(choicesField, null))
                        {
                            object choicesObj = choicesField.GetValue(ps);
                            System.Collections.IList choicesList = choicesObj as System.Collections.IList;
                            if (choicesList != null && choicesList.Count > 0)
                            {
                                // Discover choice type structure once
                                if (object.ReferenceEquals(choiceType, null))
                                {
                                    choiceType = choicesList[0].GetType();
                                    FieldInfo[] cFields = choiceType.GetFields(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                                    Log.LogInfo(string.Format("[Choice] Type: {0}, fields: {1}", choiceType.Name, cFields.Length));
                                    for (int cfi = 0; cfi < cFields.Length; cfi++)
                                    {
                                        string fname = cFields[cfi].Name;
                                        if (fname == "_text") choiceTextField = cFields[cfi];
                                        if (fname == "_link") choiceLinkField = cFields[cfi];
                                        Log.LogInfo(string.Format("[Choice]   {0} ({1})", fname, cFields[cfi].FieldType.Name));
                                    }
                                }

                                if (!object.ReferenceEquals(choiceTextField, null) && !object.ReferenceEquals(choiceLinkField, null))
                                {
                                    // Build per-passage link map
                                    Dictionary<string, List<string>> localLinkMap = new Dictionary<string, List<string>>();
                                    Dictionary<string, int> localConsumed = new Dictionary<string, int>();
                                    List<string[]> ruChoices = null;
                                    RussianChoices.TryGetValue(objBase + ":" + passageTitle, out ruChoices);
                                    if (ruChoices == null)
                                        RussianChoices.TryGetValue(passageTitle, out ruChoices);
                                    if (ruChoices != null)
                                    {
                                        for (int ci = 0; ci < ruChoices.Count; ci++)
                                        {
                                            string ruLink = ruChoices[ci][1];
                                            if (ruLink.Length > 0)
                                            {
                                                if (!localLinkMap.ContainsKey(ruLink))
                                                    localLinkMap[ruLink] = new List<string>();
                                                // Prepend emote prefix (e.g. ":silence: ") to match game format
                                                string ruText = ruChoices[ci][0];
                                                string ruEmote = ruChoices[ci].Length > 2 ? ruChoices[ci][2] : "";
                                                if (ruEmote.Length > 0)
                                                    ruText = ruEmote + " " + ruText;
                                                localLinkMap[ruLink].Add(ruText);
                                            }
                                        }
                                    }

                                    // Global link consumed counters (separate from local)
                                    Dictionary<string, int> globalConsumed = new Dictionary<string, int>();

                                    for (int ci = 0; ci < choicesList.Count; ci++)
                                    {
                                        object choiceObj = choicesList[ci];
                                        string engLink = choiceLinkField.GetValue(choiceObj) as string;
                                        if (engLink == null) continue;
                                        string engText = choiceTextField.GetValue(choiceObj) as string;

                                        // 1. Try per-passage link match
                                        List<string> ruTexts;
                                        if (localLinkMap.TryGetValue(engLink, out ruTexts))
                                        {
                                            int consumed = 0;
                                            if (localConsumed.ContainsKey(engLink))
                                                consumed = localConsumed[engLink];
                                            if (consumed < ruTexts.Count)
                                            {
                                                choiceTextField.SetValue(choiceObj, ruTexts[consumed]);
                                                localConsumed[engLink] = consumed + 1;
                                                continue;
                                            }
                                        }

                                        // 2. Try global link match (choices from other passages)
                                        List<string> globalTexts;
                                        if (GlobalLinkToChoiceTexts.TryGetValue(engLink, out globalTexts))
                                        {
                                            int consumed = 0;
                                            if (globalConsumed.ContainsKey(engLink))
                                                consumed = globalConsumed[engLink];
                                            if (consumed < globalTexts.Count)
                                            {
                                                choiceTextField.SetValue(choiceObj, globalTexts[consumed]);
                                                globalConsumed[engLink] = consumed + 1;
                                                if (replacedObjects < 5)
                                                    Log.LogInfo(string.Format("[ChoiceGlobal] '{0}' link='{1}' '{2}' -> '{3}'",
                                                        passageTitle, engLink, engText, globalTexts[consumed]));
                                                continue;
                                            }
                                        }

                                        // 3. Log untranslated (no TranslateTextDirect - it produces wrong matches)
                                        if (engText != null)
                                            Log.LogWarning(string.Format("[ChoiceUntranslated] passage='{0}' link='{1}' text='{2}'",
                                                passageTitle, engLink, engText));
                                    }
                                }
                            }
                        }

                        objReplacedCount++;
                        replacedPassages++;
                    }

                    if (objReplacedCount > 0)
                    {
                        replacedObjects++;
                        if (replacedObjects <= 10)
                        {
                            Log.LogInfo(string.Format("[DialogObj] {0}: replaced {1}/{2} passages",
                                objName, objReplacedCount, passages.Count));
                        }
                    }
                }

                Log.LogInfo(string.Format("[DialogObj] {0} objects, {1} replaced ({2} passages), {3} skipped (already done)",
                    total, replacedObjects, replacedPassages, skippedObjects));
            }
            catch (Exception e)
            {
                Log.LogError(string.Format("[DialogObj] Error: {0}", e));
            }
        }

        /// <summary>
        /// Extract speaker name from a Prompter line.
        /// Handles formats: "NAME: \"text\"", "NAME : \"text\"", "NAME : \u00ab text \u00bb"
        /// Returns null if not a speaker line.
        /// </summary>
        static string ExtractSpeakerName(string line)
        {
            if (string.IsNullOrEmpty(line)) return null;
            string trimmed = line.Trim();
            if (trimmed.StartsWith("$$")) return null; // command
            if (trimmed.StartsWith("*")) return null; // choice
            if (trimmed.StartsWith("{")) return null; // variable

            // Try patterns: " : X", ": X" where X is ", «, \u201c, \u2018
            int idx = -1;
            // Pattern 1: " : X" (space-colon-space-quote)
            idx = trimmed.IndexOf(" : \"");
            if (idx < 0) idx = trimmed.IndexOf(" : \u00ab");
            if (idx < 0) idx = trimmed.IndexOf(" : \u201c");
            if (idx < 0) idx = trimmed.IndexOf(" : \u2018");
            if (idx < 0)
            {
                // Pattern 2: ": X" (colon-space-quote, no space before)
                idx = trimmed.IndexOf(": \"");
                if (idx < 0) idx = trimmed.IndexOf(": \u00ab");
                if (idx < 0) idx = trimmed.IndexOf(": \u201c");
                if (idx < 0) idx = trimmed.IndexOf(": \u2018");
            }
            if (idx <= 0) return null;

            string name = trimmed.Substring(0, idx).Trim();
            if (name.Length == 0 || name.Length > 30) return null;

            // Verify it looks like a speaker name (mostly uppercase or ?)
            bool valid = true;
            for (int i = 0; i < name.Length; i++)
            {
                char c = name[i];
                if (!char.IsUpper(c) && c != ' ' && c != '_' && c != '?' && c != '-' &&
                    !(c >= '\u0400' && c <= '\u04FF')) // allow Cyrillic
                {
                    valid = false;
                    break;
                }
            }
            return valid ? name : null;
        }

        /// <summary>
        /// Extract the text portion after the speaker name.
        /// Returns the quote-delimited text (including quotes/guillemets).
        /// </summary>
        static string ExtractSpeakerText(string line)
        {
            if (string.IsNullOrEmpty(line)) return null;
            string trimmed = line.Trim();

            // Find the separator between name and text
            int idx = trimmed.IndexOf(" : \"");
            if (idx >= 0) return trimmed.Substring(idx + 3);

            idx = trimmed.IndexOf(" : \u00ab");
            if (idx >= 0) return trimmed.Substring(idx + 3);

            idx = trimmed.IndexOf(" : \u201c");
            if (idx >= 0) return trimmed.Substring(idx + 3);

            idx = trimmed.IndexOf(": \"");
            if (idx >= 0) return trimmed.Substring(idx + 2);

            idx = trimmed.IndexOf(": \u00ab");
            if (idx >= 0) return trimmed.Substring(idx + 2);

            idx = trimmed.IndexOf(": \u201c");
            if (idx >= 0) return trimmed.Substring(idx + 2);

            return null;
        }

        void ReplaceTextAssetContents()
        {
            // TextAssets in Unity 2018 store text in native memory — can't modify via reflection
            // Instead, ensure the TextAsset.text postfix patch works
            // Log all TextAsset names for verification
            try
            {
                var allTextAssets = Resources.FindObjectsOfTypeAll<TextAsset>();
                int hasRussian = 0;
                int logged = 0;
                foreach (var ta in allTextAssets)
                {
                    if (ta == null || string.IsNullOrEmpty(ta.name)) continue;
                    if (DialogueTexts.ContainsKey(ta.name))
                    {
                        hasRussian++;
                        if (logged < 10)
                        {
                            Log.LogInfo(string.Format("[TextAsset MATCH] {0}", ta.name));
                            logged++;
                        }
                    }
                }
                Log.LogInfo(string.Format("[TextAsset] {0} total, {1} have Russian replacement", allTextAssets.Length, hasRussian));
            }
            catch (Exception e)
            {
                Log.LogError(string.Format("[TextAsset] Error scanning: {0}", e));
            }
        }

        void OnSceneLoaded(Scene scene, LoadSceneMode mode)
        {
            Log.LogInfo(string.Format("Scene loaded: {0}", scene.name));

            // Try to patch LocalizationManager on first scene load
            if (!LocalizationPatched && !object.ReferenceEquals(HarmonyInstance, null))
            {
                PatchLocalizationManager(HarmonyInstance);
            }
            else if (LocalizationPatched && !object.ReferenceEquals(LocalizationManagerType, null))
            {
                // Re-inject translations on subsequent scene loads
                try { TryInjectTranslations(); }
                catch (Exception e) { Log.LogWarning(string.Format("Re-injection failed: {0}", e.Message)); }
            }

            // Replace TextAssets in memory with Russian content
            ReplaceTextAssetsInMemory();

            // Enumerate and patch all TMP fonts (will catch newly loaded fonts)
            EnumerateAndPatchAllFonts();

            processedTextKeys.Clear();
            StartCoroutine(TranslateSceneDelayed());
        }

        IEnumerator TranslateSceneDelayed()
        {
            // Wait a bit for UI to initialize
            yield return new WaitForSeconds(0.5f);
            TranslateAllTextInScene();
            yield return new WaitForSeconds(1f);
            TranslateAllTextInScene();
        }

        void Update()
        {
            // Scanner disabled - translation now happens in TMP_Text.text setter and LocalizationManager patch
        }

        void TranslateAllTextInScene()
        {
            if (Translations.Count == 0) return;

            int translated = 0;
            int foundUIText = 0;
            int foundTMP = 0;

            // Find all UI Text components
            try
            {
                var textComponents = FindObjectsOfType<Text>();
                foundUIText = textComponents.Length;

                foreach (var text in textComponents)
                {
                    if (text == null || string.IsNullOrEmpty(text.text)) continue;

                    int id = text.GetInstanceID();
                    string currentText = text.text;

                    // Skip if already processed with same text
                    string key = string.Format("{0}:{1}", id, currentText);
                    if (processedTextKeys.Contains(key)) continue;

                    string translation = TranslateText(currentText);
                    if (translation != null)
                    {
                        text.text = translation;
                        if (CyrillicFont != null)
                        {
                            text.font = CyrillicFont;
                        }
                        translated++;
                        processedTextKeys.Add(key);
                    }
                }
            }
            catch (Exception e)
            {
                Log.LogError(string.Format("Error scanning UI.Text: {0}", e.Message));
            }

            // TMPro - translate and apply Cyrillic font if available
            try
            {
                Type tmpTextType = null;
                foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
                {
                    tmpTextType = assembly.GetType("TMPro.TMP_Text");
                    if (!object.ReferenceEquals(tmpTextType, null)) break;
                }

                if (!object.ReferenceEquals(tmpTextType, null))
                {
                    var allTmpText = FindObjectsOfType(tmpTextType);
                    foundTMP = allTmpText.Length;

                    // Get text property and font property via reflection
                    PropertyInfo textProp = tmpTextType.GetProperty("text");
                    PropertyInfo fontProp = tmpTextType.GetProperty("font");
                    PropertyInfo fontSizeProp = tmpTextType.GetProperty("fontSize");

                    if (!object.ReferenceEquals(textProp, null) && !object.ReferenceEquals(CyrillicTMPFont, null))
                    {
                        foreach (var tmp in allTmpText)
                        {
                            if (object.ReferenceEquals(tmp, null)) continue;

                            try
                            {
                                string currentText = textProp.GetValue(tmp, null) as string;
                                if (string.IsNullOrEmpty(currentText)) continue;

                                int id = tmp.GetInstanceID();
                                string key = string.Format("{0}:{1}", id, currentText);
                                if (processedTextKeys.Contains(key)) continue;

                                string translation = TranslateText(currentText);
                                if (!object.ReferenceEquals(translation, null))
                                {
                                    // Apply Cyrillic font first
                                    if (!object.ReferenceEquals(fontProp, null))
                                    {
                                        fontProp.SetValue(tmp, CyrillicTMPFont, null);
                                    }

                                    // Apply font scale if configured
                                    if (!object.ReferenceEquals(fontSizeProp, null) && FontScale != 1.0f)
                                    {
                                        try
                                        {
                                            float currentSize = Convert.ToSingle(fontSizeProp.GetValue(tmp, null));
                                            float scaledSize = currentSize * FontScale;
                                            fontSizeProp.SetValue(tmp, scaledSize, null);
                                        }
                                        catch { }
                                    }

                                    // Then set translated text
                                    textProp.SetValue(tmp, translation, null);
                                    translated++;
                                    processedTextKeys.Add(key);
                                    Log.LogInfo(string.Format("[TMP->RUS] {0} -> {1}", currentText, translation));
                                }
                            }
                            catch (Exception ex)
                            {
                                Log.LogError(string.Format("Error processing TMP component: {0}", ex.Message));
                            }
                        }
                    }
                    else if (object.ReferenceEquals(CyrillicTMPFont, null) && foundTMP > 0)
                    {
                        Log.LogWarning("TMP font not loaded - cannot translate TMP text");
                    }
                }
            }
            catch (Exception e)
            {
                Log.LogError(string.Format("Error processing TMPro: {0}", e.Message));
            }

        }

        void CreateTextOverlay(Component tmpComponent, string text, string overlayName, Color color, float fontSize)
        {
            try
            {
                // Create overlay as CHILD of TMPro - this ensures proper Canvas context
                GameObject overlayObj = new GameObject(overlayName);
                overlayObj.transform.SetParent(tmpComponent.transform, false);

                // Setup RectTransform to fill parent completely
                RectTransform overlayRect = overlayObj.AddComponent<RectTransform>();
                overlayRect.anchorMin = Vector2.zero;
                overlayRect.anchorMax = Vector2.one;
                overlayRect.offsetMin = Vector2.zero;
                overlayRect.offsetMax = Vector2.zero;
                overlayRect.localScale = Vector3.one;

                // Add Text component
                Text textComponent = overlayObj.AddComponent<Text>();
                textComponent.text = text;
                textComponent.color = color;

                // Apply Cyrillic font
                if (!object.ReferenceEquals(CyrillicFont, null))
                {
                    textComponent.font = CyrillicFont;
                }
                else
                {
                    textComponent.font = Resources.GetBuiltinResource<Font>("Arial.ttf");
                }

                // Match font size (TMPro sizes are typically larger than UI.Text)
                textComponent.fontSize = Mathf.RoundToInt(fontSize * 0.7f);
                textComponent.resizeTextForBestFit = true;
                textComponent.resizeTextMinSize = 6;
                textComponent.resizeTextMaxSize = Mathf.RoundToInt(fontSize * 1.5f);

                // Center alignment
                textComponent.alignment = TextAnchor.MiddleCenter;

                // Allow overflow
                textComponent.horizontalOverflow = HorizontalWrapMode.Overflow;
                textComponent.verticalOverflow = VerticalWrapMode.Overflow;

                // Don't block raycasts
                textComponent.raycastTarget = false;

            }
            catch (Exception e)
            {
                Log.LogError(string.Format("Error in CreateTextOverlay: {0}", e.Message));
            }
        }

        void LoadCyrillicFonts()
        {
            string gameRoot = Path.GetDirectoryName(Application.dataPath);
            string fontsPath = Path.Combine(gameRoot, "Fonts_Cyrillic");

            if (!Directory.Exists(fontsPath))
            {
                Log.LogWarning(string.Format("Fonts_Cyrillic folder not found: {0}", fontsPath));
                return;
            }

            // Load PTSans-Regular as the primary Cyrillic font
            string primaryFontPath = Path.Combine(fontsPath, "PTSans-Regular.ttf");
            if (File.Exists(primaryFontPath))
            {
                try
                {
                    CyrillicFont = new Font(primaryFontPath);
                    CyrillicFont.name = "PTSans-Cyrillic";
                    LoadedFonts["PTSans-Regular"] = CyrillicFont;
                    Log.LogInfo("Loaded Cyrillic font: PTSans-Regular");
                }
                catch (Exception e)
                {
                    Log.LogError(string.Format("Error loading PTSans-Regular: {0}", e.Message));
                }
            }

            // Load additional fonts
            foreach (var fontFile in Directory.GetFiles(fontsPath, "*.ttf"))
            {
                string fontName = Path.GetFileNameWithoutExtension(fontFile);
                if (!LoadedFonts.ContainsKey(fontName))
                {
                    try
                    {
                        var font = new Font(fontFile);
                        font.name = fontName;
                        LoadedFonts[fontName] = font;
                        Log.LogInfo(string.Format("Loaded font: {0}", fontName));
                    }
                    catch (Exception e)
                    {
                        Log.LogError(string.Format("Error loading font {0}: {1}", fontName, e.Message));
                    }
                }
            }

            Log.LogInfo(string.Format("Loaded {0} Cyrillic fonts", LoadedFonts.Count));

            // Load TMP font from asset bundle
            LoadTMPFontBundle();
        }

        void LoadTMPFontBundle()
        {
            try
            {
                string gameRoot = Path.GetDirectoryName(Application.dataPath);
                string bundlePath = Path.Combine(gameRoot, "cyrillic_font");

                if (!File.Exists(bundlePath))
                {
                    Log.LogWarning(string.Format("TMP font bundle not found: {0}", bundlePath));
                    return;
                }

                Log.LogInfo(string.Format("Loading TMP font bundle from: {0}", bundlePath));

                // Load the asset bundle
                AssetBundle bundle = AssetBundle.LoadFromFile(bundlePath);
                if (object.ReferenceEquals(bundle, null))
                {
                    Log.LogError("Failed to load asset bundle");
                    return;
                }

                Log.LogInfo("Asset bundle loaded successfully");

                // List all assets in the bundle
                string[] assetNames = bundle.GetAllAssetNames();
                Log.LogInfo(string.Format("Assets in bundle: {0}", assetNames.Length));
                foreach (string name in assetNames)
                {
                    Log.LogInfo(string.Format("  - {0}", name));
                }

                // Try to load the TMP_FontAsset
                // First, find the TMP_FontAsset type
                Type tmpFontAssetType = null;
                foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
                {
                    tmpFontAssetType = assembly.GetType("TMPro.TMP_FontAsset");
                    if (!object.ReferenceEquals(tmpFontAssetType, null)) break;
                }

                if (object.ReferenceEquals(tmpFontAssetType, null))
                {
                    Log.LogError("TMP_FontAsset type not found");
                    bundle.Unload(false);
                    return;
                }

                // Try to load the specific asset by path with explicit type
                foreach (string assetPath in assetNames)
                {
                    Log.LogInfo(string.Format("Trying to load asset: {0}", assetPath));

                    // Try loading with explicit TMP_FontAsset type
                    MethodInfo loadAssetGeneric = typeof(AssetBundle).GetMethod("LoadAsset", new Type[] { typeof(string), typeof(Type) });
                    var asset = loadAssetGeneric.Invoke(bundle, new object[] { assetPath, tmpFontAssetType });

                    if (!object.ReferenceEquals(asset, null))
                    {
                        string typeName = asset.GetType().FullName;
                        Log.LogInfo(string.Format("  Loaded with type: {0} (Type: {1})", ((UnityEngine.Object)asset).name, typeName));
                        CyrillicTMPFont = asset;
                        Log.LogInfo(string.Format("Found TMP_FontAsset: {0}", ((UnityEngine.Object)asset).name));
                        break;
                    }
                    else
                    {
                        Log.LogWarning(string.Format("  LoadAsset with TMP_FontAsset type returned null for {0}", assetPath));

                        // Try without type
                        var assetNoType = bundle.LoadAsset(assetPath);
                        if (!object.ReferenceEquals(assetNoType, null))
                        {
                            string typeName = assetNoType.GetType().FullName;
                            Log.LogInfo(string.Format("  LoadAsset without type: {0} (Type: {1})", assetNoType.name, typeName));

                            if (typeName.Contains("FontAsset") || typeName.Contains("TMP"))
                            {
                                CyrillicTMPFont = assetNoType;
                                Log.LogInfo("Using this as TMP font");
                                break;
                            }
                        }
                        else
                        {
                            Log.LogWarning("  LoadAsset without type also returned null");
                        }
                    }
                }

                // If not found by path, try LoadAllAssets
                if (object.ReferenceEquals(CyrillicTMPFont, null))
                {
                    Log.LogInfo("Trying LoadAllAssets...");
                    var allAssets = bundle.LoadAllAssets();
                    Log.LogInfo(string.Format("Loaded {0} assets from bundle", allAssets.Length));

                    foreach (var asset in allAssets)
                    {
                        string typeName = asset.GetType().FullName;
                        Log.LogInfo(string.Format("  Asset: {0} (Type: {1})", asset.name, typeName));

                        if (tmpFontAssetType.IsInstanceOfType(asset) || typeName.Contains("TMP_FontAsset"))
                        {
                            CyrillicTMPFont = asset;
                            Log.LogInfo(string.Format("Found TMP_FontAsset: {0}", asset.name));
                        }

                        // Save Material and Texture2D for later use
                        // Use type name comparison because 'is' operator can fail with bundle-loaded assets
                        string assetTypeName = asset.GetType().FullName;
                        if (assetTypeName.Contains("Material"))
                        {
                            BundleMaterial = (Material)asset;
                            Log.LogInfo("Saved bundle Material");
                        }
                        if (assetTypeName.Contains("Texture2D"))
                        {
                            BundleAtlas = (Texture2D)asset;
                            Log.LogInfo(string.Format("Saved bundle Atlas: {0}x{1}", BundleAtlas.width, BundleAtlas.height));
                        }
                    }
                }

                if (!object.ReferenceEquals(CyrillicTMPFont, null))
                {
                    Log.LogInfo("Cyrillic TMP font loaded successfully!");
                }
                else
                {
                    Log.LogWarning("No TMP_FontAsset found in bundle - TMPro version mismatch?");
                    Log.LogInfo("Trying to create TMP font from Unity Font at runtime...");

                    // Try to create font at runtime
                    if (!object.ReferenceEquals(CyrillicFont, null))
                    {
                        CreateRuntimeTMPFont(tmpFontAssetType);
                    }
                }

                // Don't unload the bundle - we need it to stay loaded
            }
            catch (Exception e)
            {
                Log.LogError(string.Format("Error loading TMP font bundle: {0}", e.Message));
            }
        }

        void CreateRuntimeTMPFont(Type tmpFontAssetType)
        {
            try
            {
                Log.LogInfo("Attempting to create TMP font from Unity Font...");

                // Look for CreateFontAsset static method
                MethodInfo createMethod = null;

                // Try simple overload: CreateFontAsset(Font)
                createMethod = tmpFontAssetType.GetMethod("CreateFontAsset",
                    BindingFlags.Public | BindingFlags.Static,
                    null,
                    new Type[] { typeof(Font) },
                    null);

                if (!object.ReferenceEquals(createMethod, null))
                {
                    Log.LogInfo("Found CreateFontAsset(Font) method, invoking...");
                    CyrillicTMPFont = createMethod.Invoke(null, new object[] { CyrillicFont });

                    if (!object.ReferenceEquals(CyrillicTMPFont, null))
                    {
                        Log.LogInfo(string.Format("Created TMP font: {0}", ((UnityEngine.Object)CyrillicTMPFont).name));
                        return;
                    }
                }

                // List all CreateFontAsset methods for debugging
                Log.LogInfo("Looking for other CreateFontAsset methods...");
                foreach (var method in tmpFontAssetType.GetMethods(BindingFlags.Public | BindingFlags.Static))
                {
                    if (method.Name == "CreateFontAsset")
                    {
                        var parms = method.GetParameters();
                        var names = new System.Collections.Generic.List<string>();
                        foreach (var p in parms)
                        {
                            names.Add(string.Format("{0} {1}", p.ParameterType.Name, p.Name));
                        }
                        Log.LogInfo(string.Format("  CreateFontAsset({0})", string.Join(", ", names.ToArray())));
                    }
                }

                // If CreateFontAsset doesn't exist, try using an existing game font as template
                Log.LogInfo("CreateFontAsset not available, trying to clone existing game font...");

                var allFontAssets = Resources.FindObjectsOfTypeAll(tmpFontAssetType);
                Log.LogInfo(string.Format("Found {0} TMP fonts in game", allFontAssets.Length));

                foreach (var fontAsset in allFontAssets)
                {
                    Log.LogInfo(string.Format("  Game TMP font: {0}", ((UnityEngine.Object)fontAsset).name));
                }

                // Try to patch an existing font with our Cyrillic SDF atlas
                if (allFontAssets.Length > 0)
                {
                    string gameRoot = Path.GetDirectoryName(Application.dataPath);
                    string sdfFolder = Path.Combine(gameRoot, "Generated_SDF");
                    string atlasPath = Path.Combine(sdfFolder, "PTSans_SDF_atlas.png");
                    string glyphsPath = Path.Combine(sdfFolder, "PTSans_SDF_glyphs.txt");

                    if (File.Exists(atlasPath) && File.Exists(glyphsPath))
                    {
                        Log.LogInfo("Found Cyrillic SDF atlas, attempting to patch game font...");
                        PatchFontWithCyrillicAtlas(allFontAssets[0], atlasPath, glyphsPath, tmpFontAssetType);
                    }
                    else
                    {
                        Log.LogWarning("Using existing game font - Cyrillic characters will show as boxes");
                        CyrillicTMPFont = allFontAssets[0];
                    }
                }
            }
            catch (Exception e)
            {
                Log.LogError(string.Format("Error creating runtime TMP font: {0}", e.Message));
            }
        }

        void PatchFontWithCyrillicAtlas(object fontAsset, string atlasPath, string glyphsPath, Type tmpFontAssetType)
        {
            try
            {
                Log.LogInfo(string.Format("Patching font with glyphs: {0}", glyphsPath));

                // Read glyph file header to get expected atlas size
                var glyphFileLines = File.ReadAllLines(glyphsPath);
                int expectedAtlasSize = 1024;
                foreach (var headerLine in glyphFileLines)
                {
                    if (headerLine.StartsWith("# Atlas:"))
                    {
                        string sizeStr = headerLine.Substring(8).Trim();
                        int xPos = sizeStr.IndexOf('x');
                        if (xPos > 0)
                        {
                            int.TryParse(sizeStr.Substring(0, xPos), out expectedAtlasSize);
                        }
                        break;
                    }
                }
                Log.LogInfo(string.Format("Glyph file expects atlas size: {0}x{0}", expectedAtlasSize));

                // Load PNG atlas and convert to Alpha8 format (required by TMP shader)
                Texture2D tempAtlas = new Texture2D(2, 2);
                byte[] atlasData = File.ReadAllBytes(atlasPath);
                tempAtlas.LoadImage(atlasData);
                Log.LogInfo(string.Format("Loaded PNG: {0}x{1}, format: {2}", tempAtlas.width, tempAtlas.height, tempAtlas.format));

                // Convert to Alpha8 - TMP shader reads SDF from alpha channel
                Texture2D atlas = new Texture2D(tempAtlas.width, tempAtlas.height, TextureFormat.Alpha8, false);
                Color[] pixels = tempAtlas.GetPixels();
                byte[] alphaData = new byte[pixels.Length];

                for (int i = 0; i < pixels.Length; i++)
                {
                    // SDF data might be in R channel (grayscale) or A channel
                    // Try R channel first (grayscale PNG)
                    alphaData[i] = (byte)(pixels[i].r * 255f);
                }

                atlas.LoadRawTextureData(alphaData);
                atlas.Apply();

                // Set texture filtering for crisp SDF rendering
                atlas.filterMode = FilterMode.Bilinear;
                atlas.wrapMode = TextureWrapMode.Clamp;

                Log.LogInfo(string.Format("Converted to Alpha8: {0}x{1}, filter: {2}", atlas.width, atlas.height, atlas.filterMode));

                // Log info about original font material for debugging
                FieldInfo origMatField = tmpFontAssetType.GetField("material", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                if (!object.ReferenceEquals(origMatField, null))
                {
                    Material origMat = origMatField.GetValue(fontAsset) as Material;
                    if (!object.ReferenceEquals(origMat, null))
                    {
                        Log.LogInfo(string.Format("Original font material shader: {0}", origMat.shader.name));
                        if (!object.ReferenceEquals(origMat.mainTexture, null))
                        {
                            Log.LogInfo(string.Format("Original mainTexture: {0}x{1}, format: {2}",
                                origMat.mainTexture.width, origMat.mainTexture.height,
                                ((Texture2D)origMat.mainTexture).format));
                        }
                    }
                }

                // Get the material from the font and replace the texture
                // List all properties and fields to find the right one
                Log.LogInfo("TMP_FontAsset properties:");
                foreach (var prop in tmpFontAssetType.GetProperties(BindingFlags.Public | BindingFlags.Instance))
                {
                    Log.LogInfo(string.Format("  Property: {0} ({1})", prop.Name, prop.PropertyType.Name));
                }
                Log.LogInfo("TMP_FontAsset fields:");
                foreach (var field in tmpFontAssetType.GetFields(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance))
                {
                    if (field.FieldType.Name.Contains("Material") || field.FieldType.Name.Contains("Texture") ||
                        field.Name.Contains("material") || field.Name.Contains("atlas") || field.Name.Contains("Atlas"))
                    {
                        Log.LogInfo(string.Format("  Field: {0} ({1})", field.Name, field.FieldType.Name));
                    }
                }

                // Try different ways to access material/atlas
                Material mat = null;

                // Try property "material" (inherited from base)
                PropertyInfo materialProp = tmpFontAssetType.GetProperty("material", BindingFlags.Public | BindingFlags.Instance | BindingFlags.FlattenHierarchy);
                if (!object.ReferenceEquals(materialProp, null))
                {
                    mat = materialProp.GetValue(fontAsset, null) as Material;
                    Log.LogInfo("Found material via property");
                }

                // Try field "material"
                if (object.ReferenceEquals(mat, null))
                {
                    FieldInfo materialField = tmpFontAssetType.GetField("material", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                    if (!object.ReferenceEquals(materialField, null))
                    {
                        mat = materialField.GetValue(fontAsset) as Material;
                        Log.LogInfo("Found material via field");
                    }
                }

                // Try atlas property
                if (object.ReferenceEquals(mat, null))
                {
                    PropertyInfo atlasProp = tmpFontAssetType.GetProperty("atlas", BindingFlags.Public | BindingFlags.Instance);
                    if (!object.ReferenceEquals(atlasProp, null))
                    {
                        // Set atlas directly
                        atlasProp.SetValue(fontAsset, atlas, null);
                        Log.LogInfo("Set atlas texture directly via atlas property");
                    }
                }

                // Replace texture on original material (keep the shader)
                if (!object.ReferenceEquals(mat, null))
                {
                    mat.mainTexture = atlas;
                    Log.LogInfo("Replaced material.mainTexture with our atlas");
                }

                // Set the atlas field directly
                FieldInfo atlasField = tmpFontAssetType.GetField("atlas", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                if (!object.ReferenceEquals(atlasField, null))
                {
                    atlasField.SetValue(fontAsset, atlas);
                    Log.LogInfo("Set atlas field directly");
                }

                // Find TMP_Glyph type
                Type tmpGlyphType = null;
                foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
                {
                    tmpGlyphType = assembly.GetType("TMPro.TMP_Glyph");
                    if (!object.ReferenceEquals(tmpGlyphType, null)) break;
                }

                if (object.ReferenceEquals(tmpGlyphType, null))
                {
                    Log.LogWarning("TMP_Glyph type not found");
                    CyrillicTMPFont = fontAsset;
                    return;
                }

                Log.LogInfo(string.Format("Found TMP_Glyph type: {0}", tmpGlyphType.FullName));

                // Log TMP_Glyph fields
                Log.LogInfo("TMP_Glyph fields:");
                foreach (var field in tmpGlyphType.GetFields(BindingFlags.Public | BindingFlags.Instance))
                {
                    Log.LogInfo(string.Format("  {0} ({1})", field.Name, field.FieldType.Name));
                }

                // Get m_glyphInfoList field
                FieldInfo glyphListField = tmpFontAssetType.GetField("m_glyphInfoList", BindingFlags.NonPublic | BindingFlags.Instance);
                if (object.ReferenceEquals(glyphListField, null))
                {
                    Log.LogWarning("m_glyphInfoList field not found");
                    CyrillicTMPFont = fontAsset;
                    return;
                }

                // Get m_characterDictionary field
                FieldInfo charDictField = tmpFontAssetType.GetField("m_characterDictionary", BindingFlags.NonPublic | BindingFlags.Instance);

                // Get the glyph list
                var glyphList = glyphListField.GetValue(fontAsset);
                MethodInfo addMethod = glyphList.GetType().GetMethod("Add");
                MethodInfo clearMethod = glyphList.GetType().GetMethod("Clear");
                MethodInfo countProp = glyphList.GetType().GetProperty("Count").GetGetMethod();

                int existingCount = (int)countProp.Invoke(glyphList, EmptyObjectArray);
                Log.LogInfo(string.Format("Existing glyph count: {0}", existingCount));

                // Clear existing glyphs - we replace everything with our atlas
                clearMethod.Invoke(glyphList, EmptyObjectArray);
                Log.LogInfo("Cleared existing glyphs");

                // Parse glyph data (reuse glyphFileLines from earlier)
                int addedGlyphs = 0;
                foreach (var line in glyphFileLines)
                {
                    if (!line.StartsWith("char=")) continue;

                    // Parse line: char=А	unicode=1040	x=228	y=284	w=24	h=28	bx=0	by=28	adv=23
                    try
                    {
                        var parts = line.Split('\t');
                        int unicode = 0;
                        float x = 0, y = 0, w = 0, h = 0, bx = 0, by = 0, adv = 0;

                        foreach (var part in parts)
                        {
                            if (part.StartsWith("unicode=")) unicode = int.Parse(part.Substring(8));
                            else if (part.StartsWith("x=")) x = float.Parse(part.Substring(2));
                            else if (part.StartsWith("y=")) y = float.Parse(part.Substring(2));
                            else if (part.StartsWith("w=")) w = float.Parse(part.Substring(2));
                            else if (part.StartsWith("h=")) h = float.Parse(part.Substring(2));
                            else if (part.StartsWith("bx=")) bx = float.Parse(part.Substring(3));
                            else if (part.StartsWith("by=")) by = float.Parse(part.Substring(3));
                            else if (part.StartsWith("adv=")) adv = float.Parse(part.Substring(4));
                        }

                        // Add ALL glyphs (both Latin and Cyrillic)
                        if (unicode > 0)
                        {
                            // Create TMP_Glyph instance
                            var glyph = Activator.CreateInstance(tmpGlyphType);

                            // No scaling - PNG atlas and glyph file match
                            SetFieldValue(tmpGlyphType, glyph, "id", unicode);
                            SetFieldValue(tmpGlyphType, glyph, "x", x);
                            SetFieldValue(tmpGlyphType, glyph, "y", y);
                            SetFieldValue(tmpGlyphType, glyph, "width", w);
                            SetFieldValue(tmpGlyphType, glyph, "height", h);
                            SetFieldValue(tmpGlyphType, glyph, "xOffset", bx);
                            SetFieldValue(tmpGlyphType, glyph, "yOffset", by);
                            SetFieldValue(tmpGlyphType, glyph, "xAdvance", adv);
                            SetFieldValue(tmpGlyphType, glyph, "scale", 1.0f);

                            // Add to list
                            addMethod.Invoke(glyphList, new object[] { glyph });
                            addedGlyphs++;
                        }
                    }
                    catch (Exception ex)
                    {
                        Log.LogWarning(string.Format("Error parsing glyph: {0}", ex.Message));
                    }
                }

                Log.LogInfo(string.Format("Added {0} Cyrillic glyphs to font", addedGlyphs));

                // Try to rebuild the character dictionary
                MethodInfo readFontDef = tmpFontAssetType.GetMethod("ReadFontDefinition", BindingFlags.Public | BindingFlags.Instance);
                if (!object.ReferenceEquals(readFontDef, null))
                {
                    Log.LogInfo("Calling ReadFontDefinition to rebuild character dictionary...");
                    readFontDef.Invoke(fontAsset, EmptyObjectArray);
                }

                // Use this font as our Cyrillic font
                CyrillicTMPFont = fontAsset;
                Log.LogInfo("Font patched successfully!");
            }
            catch (Exception e)
            {
                Log.LogError(string.Format("Error patching font: {0}", e.Message));
                Log.LogError(e.StackTrace);
            }
        }

        void SetFieldValue(Type type, object obj, string fieldName, object value)
        {
            FieldInfo field = type.GetField(fieldName, BindingFlags.Public | BindingFlags.Instance);
            if (!object.ReferenceEquals(field, null))
            {
                field.SetValue(obj, Convert.ChangeType(value, field.FieldType));
            }
        }

        internal static Font GetCyrillicFont()
        {
            return CyrillicFont;
        }

        void TryEnableCyrillicInTMPFonts()
        {
            try
            {
                Log.LogInfo("Attempting to enable Cyrillic in TMP fonts...");

                // Find TMP_FontAsset type
                Type tmpFontAssetType = null;
                foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
                {
                    tmpFontAssetType = assembly.GetType("TMPro.TMP_FontAsset");
                    if (!object.ReferenceEquals(tmpFontAssetType, null)) break;
                }

                if (object.ReferenceEquals(tmpFontAssetType, null))
                {
                    Log.LogWarning("TMP_FontAsset type not found");
                    return;
                }

                // Find all loaded TMP font assets
                var allFontAssets = Resources.FindObjectsOfTypeAll(tmpFontAssetType);
                Log.LogInfo(string.Format("Found {0} TMP font assets", allFontAssets.Length));

                // Cyrillic characters to add
                string cyrillicChars = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя";

                // Look for TryAddCharacters method
                MethodInfo tryAddMethod = null;
                foreach (var method in tmpFontAssetType.GetMethods(BindingFlags.Instance | BindingFlags.Public))
                {
                    if (method.Name == "TryAddCharacters")
                    {
                        var parms = method.GetParameters();
                        if (parms.Length == 1 && parms[0].ParameterType.Name == "String")
                        {
                            tryAddMethod = method;
                            Log.LogInfo("Found TryAddCharacters(string) method");
                            break;
                        }
                    }
                }

                // Look for fallback font property
                PropertyInfo fallbackProp = tmpFontAssetType.GetProperty("fallbackFontAssetTable",
                    BindingFlags.Instance | BindingFlags.Public);
                if (object.ReferenceEquals(fallbackProp, null))
                {
                    fallbackProp = tmpFontAssetType.GetProperty("fallbackFontAssets",
                        BindingFlags.Instance | BindingFlags.Public);
                }

                // Look for atlas population mode
                PropertyInfo atlasPopModeProp = tmpFontAssetType.GetProperty("atlasPopulationMode",
                    BindingFlags.Instance | BindingFlags.Public);

                foreach (var fontAsset in allFontAssets)
                {
                    string fontName = fontAsset.ToString();
                    Log.LogInfo(string.Format("  TMP Font: {0}", fontName));

                    // Check atlas population mode
                    if (!object.ReferenceEquals(atlasPopModeProp, null))
                    {
                        try
                        {
                            object mode = atlasPopModeProp.GetValue(fontAsset, null);
                            Log.LogInfo(string.Format("    Atlas mode: {0}", mode));
                        }
                        catch { }
                    }

                    // Try TryAddCharacters
                    if (!object.ReferenceEquals(tryAddMethod, null))
                    {
                        try
                        {
                            bool result = (bool)tryAddMethod.Invoke(fontAsset, new object[] { cyrillicChars });
                            Log.LogInfo(string.Format("    TryAddCharacters: {0}", result ? "SUCCESS" : "FAILED"));
                        }
                        catch (Exception ex)
                        {
                            Log.LogInfo(string.Format("    TryAddCharacters error: {0}", ex.InnerException != null ? ex.InnerException.Message : ex.Message));
                        }
                    }

                    // Log fallback fonts
                    if (!object.ReferenceEquals(fallbackProp, null))
                    {
                        try
                        {
                            object fallbacks = fallbackProp.GetValue(fontAsset, null);
                            if (!object.ReferenceEquals(fallbacks, null))
                            {
                                System.Collections.IList list = fallbacks as System.Collections.IList;
                                if (!object.ReferenceEquals(list, null))
                                {
                                    Log.LogInfo(string.Format("    Fallback fonts: {0}", list.Count));
                                }
                            }
                        }
                        catch { }
                    }
                }

                Log.LogInfo("TMP font Cyrillic setup complete");
            }
            catch (Exception e)
            {
                Log.LogError(string.Format("Error in TryEnableCyrillicInTMPFonts: {0}", e.Message));
            }
        }

        void CreateCyrillicTMPFont()
        {
            try
            {
                Log.LogInfo("Creating Cyrillic TMP font...");

                // Find TMP_FontAsset type
                Type tmpFontAssetType = null;
                Assembly tmpAssembly = null;
                foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
                {
                    tmpFontAssetType = assembly.GetType("TMPro.TMP_FontAsset");
                    if (!object.ReferenceEquals(tmpFontAssetType, null))
                    {
                        tmpAssembly = assembly;
                        break;
                    }
                }

                if (object.ReferenceEquals(tmpFontAssetType, null))
                {
                    Log.LogWarning("TMP_FontAsset type not found");
                    return;
                }

                // Log all CreateFontAsset methods for debugging
                Log.LogInfo("Looking for CreateFontAsset methods...");
                foreach (var method in tmpFontAssetType.GetMethods(BindingFlags.Public | BindingFlags.Static))
                {
                    if (method.Name == "CreateFontAsset")
                    {
                        var parms = method.GetParameters();
                        var names = new List<string>();
                        foreach (var p in parms)
                        {
                            names.Add(p.ParameterType.Name);
                        }
                        string sig = string.Join(", ", names.ToArray());
                        Log.LogInfo(string.Format("  Found: CreateFontAsset({0})", sig));
                    }
                }

                // Try to create font asset from Unity Font
                if (object.ReferenceEquals(CyrillicFont, null))
                {
                    Log.LogWarning("No Cyrillic font loaded");
                    return;
                }

                // Try simple overload first
                MethodInfo createMethod = tmpFontAssetType.GetMethod("CreateFontAsset",
                    BindingFlags.Public | BindingFlags.Static,
                    null,
                    new Type[] { typeof(Font) },
                    null);

                if (!object.ReferenceEquals(createMethod, null))
                {
                    Log.LogInfo("Using CreateFontAsset(Font)...");
                    CyrillicTMPFont = createMethod.Invoke(null, new object[] { CyrillicFont });
                }
                else
                {
                    // Try with more parameters - find GlyphRenderMode and AtlasPopulationMode enums
                    Type glyphRenderModeType = tmpAssembly.GetType("UnityEngine.TextCore.LowLevel.GlyphRenderMode");
                    if (object.ReferenceEquals(glyphRenderModeType, null))
                    {
                        foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
                        {
                            glyphRenderModeType = asm.GetType("UnityEngine.TextCore.LowLevel.GlyphRenderMode");
                            if (!object.ReferenceEquals(glyphRenderModeType, null)) break;
                        }
                    }

                    Type atlasPopModeType = tmpAssembly.GetType("TMPro.AtlasPopulationMode");

                    if (!object.ReferenceEquals(glyphRenderModeType, null) && !object.ReferenceEquals(atlasPopModeType, null))
                    {
                        Log.LogInfo("Found GlyphRenderMode and AtlasPopulationMode types");

                        // Get SDFAA render mode (value 4134)
                        object sdfaaMode = Enum.ToObject(glyphRenderModeType, 4134);
                        // Get Dynamic population mode (value 1)
                        object dynamicMode = Enum.ToObject(atlasPopModeType, 1);

                        // Find the full signature method
                        foreach (var method in tmpFontAssetType.GetMethods(BindingFlags.Public | BindingFlags.Static))
                        {
                            if (method.Name == "CreateFontAsset" && method.GetParameters().Length >= 6)
                            {
                                Log.LogInfo("Using full CreateFontAsset signature...");
                                try
                                {
                                    // CreateFontAsset(Font font, int samplingPointSize, int atlasPadding,
                                    //                GlyphRenderMode renderMode, int atlasWidth, int atlasHeight,
                                    //                AtlasPopulationMode atlasPopulationMode)
                                    CyrillicTMPFont = method.Invoke(null, new object[] {
                                        CyrillicFont, 90, 9, sdfaaMode, 1024, 1024, dynamicMode
                                    });
                                    break;
                                }
                                catch (Exception ex)
                                {
                                    Log.LogWarning(string.Format("CreateFontAsset failed: {0}", ex.Message));
                                }
                            }
                        }
                    }
                    else
                    {
                        Log.LogWarning("GlyphRenderMode or AtlasPopulationMode not found");
                    }
                }

                if (!object.ReferenceEquals(CyrillicTMPFont, null))
                {
                    Log.LogInfo("Created Cyrillic TMP font successfully!");
                }
                else
                {
                    Log.LogWarning("Failed to create TMP font, trying fallback...");
                    FindExistingTMPFont(tmpFontAssetType);
                }
            }
            catch (Exception e)
            {
                Log.LogError(string.Format("Error creating TMP font: {0}", e.Message));
            }
        }

        void FindExistingTMPFont(Type tmpFontAssetType)
        {
            try
            {
                // Find all loaded TMP_FontAsset and try to add Cyrillic characters
                var allFontAssets = Resources.FindObjectsOfTypeAll(tmpFontAssetType);
                Log.LogInfo(string.Format("Found {0} TMP font assets", allFontAssets.Length));

                // Cyrillic character range (А-Яа-яЁё)
                string cyrillicChars = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя";

                // Try to find TryAddCharacters method
                MethodInfo tryAddMethod = tmpFontAssetType.GetMethod("TryAddCharacters",
                    BindingFlags.Instance | BindingFlags.Public,
                    null,
                    new Type[] { typeof(string) },
                    null);

                if (object.ReferenceEquals(tryAddMethod, null))
                {
                    // Try with different signature
                    tryAddMethod = tmpFontAssetType.GetMethod("TryAddCharacters",
                        BindingFlags.Instance | BindingFlags.Public);
                }

                foreach (var fontAsset in allFontAssets)
                {
                    string fontName = fontAsset.ToString();
                    Log.LogInfo(string.Format("  TMP Font: {0}", fontName));

                    // Try to add Cyrillic characters to this font
                    if (!object.ReferenceEquals(tryAddMethod, null))
                    {
                        try
                        {
                            bool result = (bool)tryAddMethod.Invoke(fontAsset, new object[] { cyrillicChars });
                            Log.LogInfo(string.Format("    TryAddCharacters result: {0}", result));
                        }
                        catch (Exception ex)
                        {
                            Log.LogWarning(string.Format("    TryAddCharacters failed: {0}", ex.Message));
                        }
                    }

                    // Use first font with "complete" in name as our Cyrillic font
                    if (fontName.Contains("complete") && object.ReferenceEquals(CyrillicTMPFont, null))
                    {
                        CyrillicTMPFont = fontAsset;
                        Log.LogInfo(string.Format("    Selected as Cyrillic TMP font"));
                    }
                }

                // If no "complete" font found, just use the first one
                if (object.ReferenceEquals(CyrillicTMPFont, null) && allFontAssets.Length > 0)
                {
                    CyrillicTMPFont = allFontAssets[0];
                    Log.LogInfo(string.Format("Using {0} as fallback TMP font", CyrillicTMPFont));
                }
            }
            catch (Exception e)
            {
                Log.LogError(string.Format("Error finding TMP fonts: {0}", e.Message));
            }
        }

        void PatchLocalizationManager(Harmony harmony)
        {
            try
            {
                // Find LocalizationManager type in all loaded assemblies
                Type localizationManagerType = null;

                // Log all assemblies for debugging
                Log.LogInfo("Searching for LocalizationManager in loaded assemblies...");
                foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
                {
                    string asmName = assembly.GetName().Name;

                    // Focus on game assemblies
                    if (asmName.Contains("Assembly-CSharp") || asmName.Contains("Night"))
                    {
                        Log.LogInfo(string.Format("Checking assembly: {0}", asmName));

                        try
                        {
                            // Try direct name
                            Type t = assembly.GetType("LocalizationManager");
                            if (!object.ReferenceEquals(t, null))
                            {
                                localizationManagerType = t;
                                Log.LogInfo(string.Format("Found LocalizationManager in {0}", asmName));
                                break;
                            }

                            // Search all types for LocalizationManager
                            foreach (Type type in assembly.GetTypes())
                            {
                                if (type.Name == "LocalizationManager")
                                {
                                    localizationManagerType = type;
                                    Log.LogInfo(string.Format("Found {0} in {1}", type.FullName, asmName));
                                    break;
                                }
                            }

                            if (!object.ReferenceEquals(localizationManagerType, null))
                                break;
                        }
                        catch (Exception ex)
                        {
                            Log.LogWarning(string.Format("Error checking {0}: {1}", asmName, ex.Message));
                        }
                    }
                }

                if (object.ReferenceEquals(localizationManagerType, null))
                {
                    Log.LogWarning("LocalizationManager type not found in any assembly");
                    return;
                }

                // Save type for later use
                LocalizationManagerType = localizationManagerType;

                // Find GetLocalizedString method
                MethodInfo getLocalizedString = localizationManagerType.GetMethod("GetLocalizedString",
                    BindingFlags.Public | BindingFlags.Static | BindingFlags.Instance | BindingFlags.NonPublic);

                if (object.ReferenceEquals(getLocalizedString, null))
                {
                    Log.LogWarning("GetLocalizedString method not found");
                    return;
                }

                Log.LogInfo(string.Format("Found GetLocalizedString: {0}, IsStatic: {1}",
                    getLocalizedString.ReturnType.Name, getLocalizedString.IsStatic));

                // Log method parameters
                foreach (var param in getLocalizedString.GetParameters())
                {
                    Log.LogInfo(string.Format("  Param: {0} ({1})", param.Name, param.ParameterType.Name));
                }

                // Create postfix patch
                MethodInfo postfix = typeof(RussianLocalization).GetMethod("LocalizationPostfix",
                    BindingFlags.Static | BindingFlags.NonPublic);

                harmony.Patch(getLocalizedString, postfix: new HarmonyMethod(postfix));
                Log.LogInfo("LocalizationManager.GetLocalizedString patched");

                // Also try to modify cached localization data directly
                ModifyLocalizationData(localizationManagerType);

                LocalizationPatched = true;
                Log.LogInfo("LocalizationManager patching complete");
            }
            catch (Exception e)
            {
                Log.LogError(string.Format("Error patching LocalizationManager: {0}", e.Message));
            }
        }

        void ModifyLocalizationData(Type localizationManagerType)
        {
            try
            {
                // Find the singleton instance
                PropertyInfo instanceProp = localizationManagerType.GetProperty("instance",
                    BindingFlags.Public | BindingFlags.Static | BindingFlags.NonPublic);

                if (object.ReferenceEquals(instanceProp, null))
                {
                    // Try field instead
                    FieldInfo instanceField = localizationManagerType.GetField("instance",
                        BindingFlags.Public | BindingFlags.Static | BindingFlags.NonPublic);
                    if (object.ReferenceEquals(instanceField, null))
                    {
                        instanceField = localizationManagerType.GetField("_instance",
                            BindingFlags.Public | BindingFlags.Static | BindingFlags.NonPublic);
                    }
                    if (object.ReferenceEquals(instanceField, null))
                    {
                        Log.LogWarning("LocalizationManager instance field not found");

                        // Log all fields for debugging
                        Log.LogInfo("Available static fields:");
                        foreach (var f in localizationManagerType.GetFields(BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic))
                        {
                            Log.LogInfo(string.Format("  - {0} ({1})", f.Name, f.FieldType.Name));
                        }
                        return;
                    }

                    object instance = instanceField.GetValue(null);
                    if (object.ReferenceEquals(instance, null))
                    {
                        Log.LogWarning("LocalizationManager instance is null");
                        return;
                    }

                    Log.LogInfo(string.Format("Found LocalizationManager instance via field {0}", instanceField.Name));
                    InjectTranslations(instance, localizationManagerType);
                }
                else
                {
                    object instance = instanceProp.GetValue(null, null);
                    if (object.ReferenceEquals(instance, null))
                    {
                        Log.LogWarning("LocalizationManager instance is null");
                        return;
                    }
                    Log.LogInfo("Found LocalizationManager instance via property");
                    InjectTranslations(instance, localizationManagerType);
                }
            }
            catch (Exception e)
            {
                Log.LogError(string.Format("Error modifying localization data: {0}", e.Message));
            }
        }

        void InjectTranslations(object localizationManager, Type managerType)
        {
            Log.LogInfo("Searching for localization data storage...");

            // Log all instance fields
            foreach (var field in managerType.GetFields(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic))
            {
                Log.LogInfo(string.Format("  Instance field: {0} ({1})", field.Name, field.FieldType.Name));
            }

            // Find current_localization field (backing field for property)
            FieldInfo locDataField = managerType.GetField("<current_localization>k__BackingField",
                BindingFlags.Instance | BindingFlags.NonPublic);

            if (object.ReferenceEquals(locDataField, null))
            {
                // Try property
                PropertyInfo locDataProp = managerType.GetProperty("current_localization",
                    BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
                if (!object.ReferenceEquals(locDataProp, null))
                {
                    object locData = locDataProp.GetValue(localizationManager, null);
                    if (!object.ReferenceEquals(locData, null))
                    {
                        Log.LogInfo("Found current_localization via property");
                        ExploreLocalizationData(locData);
                    }
                }
                else
                {
                    Log.LogWarning("current_localization not found");
                }
                return;
            }

            object localizationData = locDataField.GetValue(localizationManager);
            if (object.ReferenceEquals(localizationData, null))
            {
                Log.LogWarning("current_localization is null");
                return;
            }

            Log.LogInfo("Found current_localization data");
            ExploreLocalizationData(localizationData);
        }

        void TryInjectTranslations()
        {
            try
            {
                Log.LogInfo("Attempting to inject translations...");

                // Get instance
                PropertyInfo instanceProp = LocalizationManagerType.GetProperty("instance",
                    BindingFlags.Public | BindingFlags.Static | BindingFlags.NonPublic);

                object instance = null;
                if (!object.ReferenceEquals(instanceProp, null))
                {
                    instance = instanceProp.GetValue(null, null);
                }
                else
                {
                    FieldInfo instanceField = LocalizationManagerType.GetField("_instance",
                        BindingFlags.Public | BindingFlags.Static | BindingFlags.NonPublic);
                    if (!object.ReferenceEquals(instanceField, null))
                    {
                        instance = instanceField.GetValue(null);
                    }
                }

                if (object.ReferenceEquals(instance, null))
                {
                    Log.LogInfo("LocalizationManager instance still null");
                    return;
                }

                // Get current_localization
                FieldInfo locDataField = LocalizationManagerType.GetField("<current_localization>k__BackingField",
                    BindingFlags.Instance | BindingFlags.NonPublic);

                object locData = null;
                if (!object.ReferenceEquals(locDataField, null))
                {
                    locData = locDataField.GetValue(instance);
                }
                else
                {
                    PropertyInfo locDataProp = LocalizationManagerType.GetProperty("current_localization",
                        BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
                    if (!object.ReferenceEquals(locDataProp, null))
                    {
                        locData = locDataProp.GetValue(instance, null);
                    }
                }

                if (object.ReferenceEquals(locData, null))
                {
                    Log.LogInfo("current_localization still null");
                    return;
                }

                Log.LogInfo("Got LocalizationData, exploring structure...");
                ExploreAndInjectTranslations(locData);
            }
            catch (Exception e)
            {
                Log.LogError(string.Format("Error in TryInjectTranslations: {0}", e.Message));
            }
        }

        void ExploreAndInjectTranslations(object locData)
        {
            Type locDataType = locData.GetType();
            Log.LogInfo(string.Format("LocalizationData type: {0}", locDataType.FullName));

            // Look for dictionary or list fields
            foreach (var field in locDataType.GetFields(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic))
            {
                object val = field.GetValue(locData);
                string valInfo = "null";
                if (!object.ReferenceEquals(val, null))
                {
                    Type valType = val.GetType();

                    // Check if it's a dictionary (use Name comparison to avoid Type.op_Equality)
                    if (valType.IsGenericType && valType.GetGenericTypeDefinition().Name == "Dictionary`2")
                    {
                        var args = valType.GetGenericArguments();
                        Log.LogInfo(string.Format("  DICTIONARY FOUND: {0} (Dict<{1},{2}>)",
                            field.Name, args[0].Name, args[1].Name));

                        // If it's Dictionary<string, string>, inject translations
                        if (args[0].Name == "String" && args[1].Name == "String")
                        {
                            InjectIntoDictionary(val as IDictionary<string, string>, field.Name);
                        }
                    }
                    else
                    {
                        System.Collections.ICollection col = val as System.Collections.ICollection;
                        System.Array arr = val as System.Array;
                        if (col != null)
                        {
                            valInfo = string.Format("Collection[{0}]", col.Count);
                            Log.LogInfo(string.Format("  {0} ({1}) = {2}", field.Name, field.FieldType.Name, valInfo));
                        }
                        else if (arr != null)
                        {
                            valInfo = string.Format("Array[{0}]", arr.Length);
                            Log.LogInfo(string.Format("  {0} ({1}) = {2}", field.Name, field.FieldType.Name, valInfo));
                        }
                        else
                        {
                            Log.LogInfo(string.Format("  {0} ({1}) = {2}", field.Name, valType.Name, val.ToString()));
                        }
                    }
                }
                else
                {
                    Log.LogInfo(string.Format("  {0} ({1}) = null", field.Name, field.FieldType.Name));
                }
            }
        }

        void InjectIntoDictionary(IDictionary<string, string> dict, string fieldName)
        {
            if (object.ReferenceEquals(dict, null))
            {
                Log.LogWarning("Dictionary is null");
                return;
            }

            Log.LogInfo(string.Format("Injecting translations into {0} (current size: {1})", fieldName, dict.Count));

            // Phase 1: KEY-based injection (most reliable)
            // Build case-insensitive lookup from KeyTranslations
            var keyTransLower = new Dictionary<string, string>();
            foreach (var kvp in KeyTranslations)
            {
                string lk = kvp.Key.ToUpperInvariant();
                if (!keyTransLower.ContainsKey(lk))
                    keyTransLower[lk] = kvp.Value;
            }

            int injectedByKey = 0;
            var keysToUpdate = new List<string>();
            var injectedKeySet = new HashSet<string>(); // track which dict keys were injected by key
            foreach (var key in dict.Keys)
            {
                keysToUpdate.Add(key);
            }

            foreach (var key in keysToUpdate)
            {
                string russianValue;
                // Try exact match first
                if (KeyTranslations.TryGetValue(key, out russianValue))
                {
                    // found
                }
                // Try case-insensitive
                else if (keyTransLower.TryGetValue(key.ToUpperInvariant(), out russianValue))
                {
                    // found via case-insensitive
                }
                else
                {
                    continue;
                }

                if (injectedByKey < 15)
                {
                    Log.LogInfo(string.Format("  [KEY] {0} = {1} -> {2}", key,
                        dict[key].Length > 30 ? dict[key].Substring(0, 30) + "..." : dict[key],
                        russianValue.Length > 30 ? russianValue.Substring(0, 30) + "..." : russianValue));
                }
                dict[key] = russianValue;
                injectedByKey++;
                injectedKeySet.Add(key);
            }

            // Phase 2: VALUE-based injection (fallback for keys not in KeyTranslations)
            var translationsLower = new Dictionary<string, string>();
            foreach (var kvp in Translations)
            {
                string keyLower = kvp.Key.ToLowerInvariant();
                if (!translationsLower.ContainsKey(keyLower))
                {
                    translationsLower[keyLower] = kvp.Value;
                }
            }

            int injectedByValue = 0;
            foreach (var key in keysToUpdate)
            {
                // Skip if already replaced by key
                if (injectedKeySet.Contains(key)) continue;

                string value = dict[key];
                if (string.IsNullOrEmpty(value)) continue;

                // Check if already Cyrillic
                bool hasCyrillic = false;
                foreach (char c in value)
                {
                    if (c >= 0x0400 && c <= 0x04FF) { hasCyrillic = true; break; }
                }
                if (hasCyrillic) continue;

                // Try exact match
                if (Translations.ContainsKey(value))
                {
                    dict[key] = Translations[value];
                    injectedByValue++;
                    continue;
                }

                // Try case-insensitive match
                string valueLower = value.ToLowerInvariant();
                if (translationsLower.ContainsKey(valueLower))
                {
                    dict[key] = translationsLower[valueLower];
                    injectedByValue++;
                }
            }

            // Log uninjected entries to file for debugging
            int uninjected = 0;
            StringBuilder uninjectedLog = new StringBuilder();
            foreach (var key in keysToUpdate)
            {
                if (KeyTranslations.ContainsKey(key)) continue;
                string value = dict[key];
                if (string.IsNullOrEmpty(value)) continue;
                bool hasCyr = false;
                foreach (char c in value) { if (c >= 0x0400 && c <= 0x04FF) { hasCyr = true; break; } }
                if (!hasCyr)
                {
                    uninjected++;
                    uninjectedLog.AppendLine(string.Format("{0} = {1}", key, value));
                }
            }

            if (uninjected > 0)
            {
                Log.LogWarning(string.Format("{0} entries NOT translated in _dict", uninjected));
                try
                {
                    string gameRoot = Path.GetDirectoryName(Application.dataPath);
                    string dumpPath = Path.Combine(gameRoot, "uninjected_keys.txt");
                    File.WriteAllText(dumpPath, uninjectedLog.ToString(), Encoding.UTF8);
                    Log.LogInfo(string.Format("Dumped uninjected keys to {0}", dumpPath));
                }
                catch (Exception ex)
                {
                    Log.LogWarning(string.Format("Failed to dump uninjected keys: {0}", ex.Message));
                }
            }

            Log.LogInfo(string.Format("Injected {0} by KEY + {1} by VALUE = {2} total ({3} dict entries, {4} still English)",
                injectedByKey, injectedByValue, injectedByKey + injectedByValue, dict.Count, uninjected));
            TranslationsInjected = true;
        }

        void ExploreLocalizationData(object locData)
        {
            Type locDataType = locData.GetType();
            Log.LogInfo(string.Format("LocalizationData type: {0}", locDataType.FullName));

            // List all fields
            Log.LogInfo("LocalizationData fields:");
            foreach (var field in locDataType.GetFields(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic))
            {
                object val = field.GetValue(locData);
                string valInfo = "null";
                if (!object.ReferenceEquals(val, null))
                {
                    System.Collections.ICollection col = val as System.Collections.ICollection;
                    System.Array arr = val as System.Array;
                    if (col != null)
                        valInfo = string.Format("Collection[{0}]", col.Count);
                    else if (arr != null)
                        valInfo = string.Format("Array[{0}]", arr.Length);
                    else
                        valInfo = val.ToString();
                }
                Log.LogInfo(string.Format("  {0} ({1}) = {2}", field.Name, field.FieldType.Name, valInfo));
            }

            // List all properties
            Log.LogInfo("LocalizationData properties:");
            foreach (var prop in locDataType.GetProperties(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic))
            {
                try
                {
                    object val = prop.GetValue(locData, null);
                    string valInfo = "null";
                    if (!object.ReferenceEquals(val, null))
                    {
                        System.Collections.ICollection col = val as System.Collections.ICollection;
                        System.Array arr = val as System.Array;
                        if (col != null)
                            valInfo = string.Format("Collection[{0}]", col.Count);
                        else if (arr != null)
                            valInfo = string.Format("Array[{0}]", arr.Length);
                        else
                            valInfo = val.GetType().Name;
                    }
                    Log.LogInfo(string.Format("  {0} ({1}) = {2}", prop.Name, prop.PropertyType.Name, valInfo));
                }
                catch { }
            }
        }

        // Postfix for LocalizationManager.GetLocalizedString
        // __0 captures the first argument (the localization key)
        static void LocalizationPostfix(ref string __result, string __0)
        {
            if (string.IsNullOrEmpty(__result))
            {
                return;
            }

            string locKey = __0;

            // Phase 1: Try key-based translation (most reliable)
            if (!string.IsNullOrEmpty(locKey))
            {
                string keyTranslation;
                if (KeyTranslations.TryGetValue(locKey, out keyTranslation))
                {
                    __result = keyTranslation;
                    return;
                }
                // Case-insensitive fallback
                if (KeyTranslations.TryGetValue(locKey.ToUpperInvariant(), out keyTranslation) ||
                    KeyTranslations.TryGetValue(locKey.ToLowerInvariant(), out keyTranslation))
                {
                    __result = keyTranslation;
                    return;
                }
            }

            // Phase 2: Try value-based translation (fallback)
            string translation = TranslateText(__result);
            if (!object.ReferenceEquals(translation, null))
            {
                __result = translation;
            }
        }

        void LoadTranslations()
        {
            string gameRoot = Path.GetDirectoryName(Application.dataPath);
            string translationPath = Path.Combine(Path.Combine(gameRoot, "Russian_UI"), "full_translation_mapping.json");

            if (!File.Exists(translationPath))
            {
                Log.LogWarning(string.Format("Translation file not found: {0}", translationPath));
                return;
            }

            try
            {
                string json = File.ReadAllText(translationPath, Encoding.UTF8);
                // Simple JSON parsing for key-value pairs
                Translations = ParseSimpleJson(json);
                int originalCount = Translations.Count;

                // Add normalized versions of keys (with standard apostrophes, etc.)
                var normalizedToAdd = new Dictionary<string, string>();
                foreach (var kvp in Translations)
                {
                    string normalizedKey = NormalizeText(kvp.Key);
                    if (normalizedKey != kvp.Key && !Translations.ContainsKey(normalizedKey) && !normalizedToAdd.ContainsKey(normalizedKey))
                    {
                        normalizedToAdd[normalizedKey] = kvp.Value;
                    }
                }
                foreach (var kvp in normalizedToAdd)
                {
                    Translations[kvp.Key] = kvp.Value;
                }

                Log.LogInfo(string.Format("Loaded {0} UI translations (+{1} normalized)", originalCount, normalizedToAdd.Count));

                // Build reverse mapping (Russian -> English) for speaker name recovery
                // Used as fallback when per-passage positional mapping fails
                RuToEngSpeaker.Clear();
                foreach (var kvp in Translations)
                {
                    string ek = kvp.Key;
                    string rv = kvp.Value;
                    if (ek.Length < 2 || ek.Length > 30 || rv.Length < 2 || rv.Length > 30) continue;
                    if (ek.IndexOf(' ') >= 0 || rv.IndexOf(' ') >= 0) continue;
                    bool keyValid = true;
                    for (int i = 0; i < ek.Length; i++)
                    {
                        char c = ek[i];
                        if (!char.IsUpper(c) && c != '-') { keyValid = false; break; }
                    }
                    if (!keyValid) continue;
                    bool valValid = true;
                    for (int i = 0; i < rv.Length; i++)
                    {
                        char c = rv[i];
                        bool cyrUpper = (c >= '\u0410' && c <= '\u042F') || c == '\u0401';
                        if (!cyrUpper && c != '-') { valValid = false; break; }
                    }
                    if (!valValid) continue;
                    if (!RuToEngSpeaker.ContainsKey(rv) || ek.Length > RuToEngSpeaker[rv].Length)
                        RuToEngSpeaker[rv] = ek;
                }
                Log.LogInfo(string.Format("Built reverse speaker map: {0} entries", RuToEngSpeaker.Count));
            }
            catch (Exception e)
            {
                Log.LogError(string.Format("Error loading translations: {0}", e.Message));
            }
        }

        void LoadDialogueTexts()
        {
            string gameRoot = Path.GetDirectoryName(Application.dataPath);
            string textsPath = Path.Combine(gameRoot, "Russian_Texts");

            if (!Directory.Exists(textsPath))
            {
                Log.LogWarning(string.Format("Russian_Texts folder not found: {0}", textsPath));
                return;
            }

            int passageCount = 0;
            foreach (var file in Directory.GetFiles(textsPath, "*.txt"))
            {
                try
                {
                    string filename = Path.GetFileNameWithoutExtension(file);
                    string assetNameEng = filename.Replace("_rus", "_eng");
                    string assetNameRaw = filename.Replace("_rus", "");
                    string content = File.ReadAllText(file, Encoding.UTF8);
                    // Store with _eng suffix (for assets like 900_intro_eng)
                    DialogueTexts[assetNameEng] = content;
                    // Also store without suffix (for assets like 099_boss_01)
                    if (assetNameRaw != assetNameEng)
                    {
                        DialogueTexts[assetNameRaw] = content;
                    }

                    // Parse passages: === title -> lines until next ===
                    // First pass: collect all passage titles
                    string[] fileLines = content.Split(new char[] { '\n' });
                    HashSet<string> passageTitles = new HashSet<string>();
                    for (int i = 0; i < fileLines.Length; i++)
                    {
                        string lt = fileLines[i].TrimEnd('\r', '\n');
                        if (lt.StartsWith("==="))
                            passageTitles.Add(lt.Substring(3).Trim());
                    }

                    // Second pass: parse lines and choices
                    string currentPassage = null;
                    List<string> currentLines = null;
                    List<string[]> currentChoices = null;

                    for (int i = 0; i < fileLines.Length; i++)
                    {
                        string line = fileLines[i].TrimEnd('\r', '\n');

                        if (line.StartsWith("==="))
                        {
                            if (currentPassage != null)
                            {
                                if (currentLines != null && currentLines.Count > 0)
                                {
                                    // Per-object qualified key (prevents cross-contamination)
                                    RussianPassages[assetNameRaw + ":" + currentPassage] = currentLines;
                                    // Global fallback (first file wins)
                                    if (!RussianPassages.ContainsKey(currentPassage))
                                        RussianPassages[currentPassage] = currentLines;
                                    passageCount++;
                                }
                                if (currentChoices != null && currentChoices.Count > 0)
                                {
                                    RussianChoices[assetNameRaw + ":" + currentPassage] = currentChoices;
                                    if (!RussianChoices.ContainsKey(currentPassage))
                                        RussianChoices[currentPassage] = currentChoices;
                                }
                            }
                            currentPassage = line.Substring(3).Trim();
                            currentLines = new List<string>();
                            currentChoices = new List<string[]>();
                            continue;
                        }

                        if (currentPassage == null) continue;
                        if (string.IsNullOrEmpty(line.Trim())) continue;
                        string trimmed = line.Trim();
                        if (trimmed.StartsWith("%%")) continue;

                        // Collect choice lines (start with *)
                        if (trimmed.StartsWith("*"))
                        {
                            // Parse: "* text -> target" or "* :silence: text -> target"
                            string choiceLine = trimmed.Substring(1).Trim();
                            string link = "";
                            int arrowIdx = choiceLine.LastIndexOf("->");
                            if (arrowIdx >= 0)
                            {
                                link = choiceLine.Substring(arrowIdx + 2).Trim();
                                choiceLine = choiceLine.Substring(0, arrowIdx).Trim();
                            }
                            // Detect and preserve emotes like :silence:, :anger:, :puzzled:
                            string emote = "";
                            if (choiceLine.StartsWith(":"))
                            {
                                int emoteEnd = choiceLine.IndexOf(":", 1);
                                if (emoteEnd > 0)
                                {
                                    emote = choiceLine.Substring(0, emoteEnd + 1);
                                    choiceLine = choiceLine.Substring(emoteEnd + 1).Trim();
                                }
                            }
                            if (choiceLine.Length > 0)
                                currentChoices.Add(new string[] { choiceLine, link, emote });
                            continue;
                        }

                        // Skip variable modifier lines { var += value }
                        if (trimmed.StartsWith("{") && trimmed.EndsWith("}")) continue;

                        // Skip navigation links (-> passage-name or -> condition ? target)
                        if (trimmed.StartsWith("->")) continue;

                        // Skip navigation links (bare passage titles)
                        if (passageTitles.Contains(trimmed)) continue;

                        // Also skip lines like "passagename" that reference passages in other files
                        if (RussianPassages.ContainsKey(trimmed)) continue;

                        // Skip navigation data conditionals (Ink branching logic)
                        // These are NOT part of compiled passage _lines[] and inflate line count
                        if (trimmed.Contains(";;")) continue;

                        // Skip choice echo artifacts (:silence:, :anger:, :puzzled:, etc.)
                        // These are choice display texts that leaked into extraction;
                        // NOT part of compiled passage _lines[] — they inflate line count
                        if (trimmed.StartsWith(":"))
                        {
                            int emoteEnd = trimmed.IndexOf(":", 1);
                            if (emoteEnd > 1)
                            {
                                bool isTag = true;
                                for (int ti = 1; ti < emoteEnd; ti++)
                                {
                                    char tc = trimmed[ti];
                                    if (tc < 'a' || tc > 'z')
                                    {
                                        isTag = false;
                                        break;
                                    }
                                }
                                if (isTag) continue;
                            }
                        }

                        // Fix missing spaces after punctuation before Cyrillic letters
                        // (skip $$ commands and repeated punctuation like ... or ?? or !!)
                        if (!trimmed.StartsWith("$$"))
                        {
                            var sb = new StringBuilder();
                            for (int ci = 0; ci < trimmed.Length; ci++)
                            {
                                char ch = trimmed[ci];
                                sb.Append(ch);
                                if ((ch == '.' || ch == '?' || ch == '!') &&
                                    ci + 1 < trimmed.Length &&
                                    trimmed[ci + 1] >= '\u0400' && trimmed[ci + 1] <= '\u04FF' &&
                                    (ci == 0 || trimmed[ci - 1] != ch))
                                {
                                    sb.Append(' ');
                                }
                            }
                            trimmed = sb.ToString();
                        }

                        currentLines.Add(trimmed);
                    }

                    if (currentPassage != null)
                    {
                        if (currentLines != null && currentLines.Count > 0)
                        {
                            RussianPassages[assetNameRaw + ":" + currentPassage] = currentLines;
                            if (!RussianPassages.ContainsKey(currentPassage))
                                RussianPassages[currentPassage] = currentLines;
                            passageCount++;
                        }
                        if (currentChoices != null && currentChoices.Count > 0)
                        {
                            RussianChoices[assetNameRaw + ":" + currentPassage] = currentChoices;
                            if (!RussianChoices.ContainsKey(currentPassage))
                                RussianChoices[currentPassage] = currentChoices;
                        }
                    }
                }
                catch (Exception e)
                {
                    Log.LogError(string.Format("Error loading {0}: {1}", file, e.Message));
                }
            }

            // Build global link -> choice text map from all passages
            foreach (var kv in RussianChoices)
            {
                for (int ci = 0; ci < kv.Value.Count; ci++)
                {
                    string link = kv.Value[ci][1];
                    if (link.Length > 0)
                    {
                        if (!GlobalLinkToChoiceTexts.ContainsKey(link))
                            GlobalLinkToChoiceTexts[link] = new List<string>();
                        // Prepend emote prefix to match game format
                        string cText = kv.Value[ci][0];
                        string cEmote = kv.Value[ci].Length > 2 ? kv.Value[ci][2] : "";
                        if (cEmote.Length > 0)
                            cText = cEmote + " " + cText;
                        GlobalLinkToChoiceTexts[link].Add(cText);
                    }
                }
            }
            Log.LogInfo(string.Format("Built global choice link map: {0} unique links", GlobalLinkToChoiceTexts.Count));

            Log.LogInfo(string.Format("Loaded {0} Russian dialogue files, {1} passages", DialogueTexts.Count, passageCount));
        }

        void LoadPassageDump()
        {
            string gameRoot = Path.GetDirectoryName(Application.dataPath);
            string dumpPath = Path.Combine(gameRoot, "passage_dump.txt");
            if (!File.Exists(dumpPath))
            {
                Log.LogInfo("No passage_dump.txt found, sequential fallback disabled");
                return;
            }

            // Parse dump file to get all known passage titles
            string[] dumpLines = File.ReadAllLines(dumpPath, Encoding.UTF8);
            for (int i = 0; i < dumpLines.Length; i++)
            {
                if (dumpLines[i].StartsWith("P "))
                {
                    // Format: "P title linecount choicecount"
                    string rest = dumpLines[i].Substring(2);
                    // Parse from the end: last token is choicecount, before that linecount, rest is title
                    string[] parts = rest.Split(' ');
                    if (parts.Length >= 3)
                    {
                        // Title may contain spaces, so rejoin all but last 2
                        string title = string.Join(" ", parts, 0, parts.Length - 2);
                        AllKnownPassageTitles.Add(title);
                    }
                }
            }
            Log.LogInfo(string.Format("Loaded {0} passage titles from dump", AllKnownPassageTitles.Count));

            // Now parse raw Russian files (from Russian_Texts_backup if exists, else Russian_Texts)
            // into content blocks separated by nav lines (lines matching known passage titles)
            string textsPath = Path.Combine(gameRoot, "Russian_Texts_backup");
            if (!Directory.Exists(textsPath))
                textsPath = Path.Combine(gameRoot, "Russian_Texts");
            if (!Directory.Exists(textsPath)) return;

            int totalBlocks = 0;
            foreach (var file in Directory.GetFiles(textsPath, "*_rus.txt"))
            {
                string fname = Path.GetFileNameWithoutExtension(file);
                string baseName = fname.Replace("_rus", "");
                string content = File.ReadAllText(file, Encoding.UTF8);

                // Skip files that already have === markers (they're handled by LoadDialogueTexts)
                if (content.Contains("=== ")) continue;

                string[] lines = content.Split(new char[] { '\n' });
                var blocks = new List<List<string>>();
                var currentBlock = new List<string>();

                for (int i = 0; i < lines.Length; i++)
                {
                    string trimmed = lines[i].Trim('\r', '\n', ' ', '\t');
                    if (string.IsNullOrEmpty(trimmed)) continue;
                    // Skip header lines
                    if (trimmed.StartsWith("%%") || trimmed.StartsWith("VAR ") || trimmed.StartsWith("+++ ")) continue;

                    // If this line is a known passage title, it's a nav marker — split here
                    if (AllKnownPassageTitles.Contains(trimmed))
                    {
                        if (currentBlock.Count > 0)
                        {
                            blocks.Add(currentBlock);
                            currentBlock = new List<string>();
                        }
                        continue;
                    }

                    // Skip $$ commands
                    if (trimmed.StartsWith("$$")) continue;

                    currentBlock.Add(trimmed);
                }
                if (currentBlock.Count > 0)
                    blocks.Add(currentBlock);

                if (blocks.Count > 0)
                {
                    RawRussianBlocks[baseName] = blocks;
                    RawBlockIndex[baseName] = 0;
                    totalBlocks += blocks.Count;
                }
            }
            Log.LogInfo(string.Format("Built raw Russian blocks: {0} files, {1} total blocks", RawRussianBlocks.Count, totalBlocks));
        }

        void LoadKeyTranslations()
        {
            string gameRoot = Path.GetDirectoryName(Application.dataPath);
            string keyPath = Path.Combine(Path.Combine(gameRoot, "Russian_UI"), "key_based_translations.json");

            if (!File.Exists(keyPath))
            {
                Log.LogWarning(string.Format("Key translations file not found: {0}", keyPath));
                return;
            }

            try
            {
                string json = File.ReadAllText(keyPath, Encoding.UTF8);
                KeyTranslations = ParseSimpleJson(json);
                Log.LogInfo(string.Format("Loaded {0} key-based translations", KeyTranslations.Count));
            }
            catch (Exception e)
            {
                Log.LogError(string.Format("Error loading key translations: {0}", e.Message));
            }
        }

        static Dictionary<string, string> ParseSimpleJson(string json)
        {
            var result = new Dictionary<string, string>();

            // Remove whitespace and braces
            json = json.Trim();
            if (json.StartsWith("{")) json = json.Substring(1);
            if (json.EndsWith("}")) json = json.Substring(0, json.Length - 1);

            // Parse key-value pairs
            int i = 0;
            while (i < json.Length)
            {
                // Skip whitespace
                while (i < json.Length && char.IsWhiteSpace(json[i])) i++;
                if (i >= json.Length) break;

                // Find key
                if (json[i] != '"') { i++; continue; }
                i++; // skip opening quote

                int keyStart = i;
                while (i < json.Length && json[i] != '"')
                {
                    if (json[i] == '\\') i++; // skip escaped char
                    i++;
                }
                string key = UnescapeJson(json.Substring(keyStart, i - keyStart));
                i++; // skip closing quote

                // Skip to colon
                while (i < json.Length && json[i] != ':') i++;
                i++; // skip colon

                // Skip whitespace
                while (i < json.Length && char.IsWhiteSpace(json[i])) i++;

                // Find value
                if (i >= json.Length || json[i] != '"') { i++; continue; }
                i++; // skip opening quote

                int valStart = i;
                while (i < json.Length && json[i] != '"')
                {
                    if (json[i] == '\\') i++; // skip escaped char
                    i++;
                }
                string value = UnescapeJson(json.Substring(valStart, i - valStart));
                i++; // skip closing quote

                if (!string.IsNullOrEmpty(key) && !string.IsNullOrEmpty(value))
                {
                    result[key] = value;
                }

                // Skip to next pair
                while (i < json.Length && json[i] != ',') i++;
                i++; // skip comma
            }

            return result;
        }

        static string UnescapeJson(string s)
        {
            return s.Replace("\\n", "\n")
                    .Replace("\\r", "\r")
                    .Replace("\\t", "\t")
                    .Replace("\\\"", "\"")
                    .Replace("\\\\", "\\");
        }

        // Case-insensitive lookup dictionary (built on first use)
        private static Dictionary<string, string> TranslationsLower = null;

        private static void BuildLowerDictionary()
        {
            if (TranslationsLower != null) return;
            TranslationsLower = new Dictionary<string, string>();
            foreach (var kvp in Translations)
            {
                // Add lowercase version
                string lowerKey = kvp.Key.ToLowerInvariant();
                if (!TranslationsLower.ContainsKey(lowerKey))
                {
                    TranslationsLower[lowerKey] = kvp.Value;
                }

                // Also add normalized lowercase version
                string normalizedKey = NormalizeText(kvp.Key).ToLowerInvariant();
                if (normalizedKey != lowerKey && !TranslationsLower.ContainsKey(normalizedKey))
                {
                    TranslationsLower[normalizedKey] = kvp.Value;
                }
            }
            Log.LogInfo(string.Format("Built case-insensitive dictionary with {0} entries", TranslationsLower.Count));
        }

        // Translate text using loaded translations
        internal static string TranslateText(string text)
        {
            if (string.IsNullOrEmpty(text)) return null;

            // Skip numeric/currency/time values - don't translate or replace font
            if (IsCurrencyOrTimeString(text)) return null;

            // Strip __ markers if present (game's localization key format)
            string cleanText = text;
            if (cleanText.StartsWith("__") && cleanText.EndsWith("__") && cleanText.Length > 4)
            {
                cleanText = cleanText.Substring(2, cleanText.Length - 4);
            }

            string translation;

            // Exact match
            if (Translations.TryGetValue(cleanText, out translation))
            {
                return translation;
            }
            if (Translations.TryGetValue(text, out translation))
            {
                return translation;
            }

            // Try trimmed match
            string trimmed = cleanText.Trim();
            if (Translations.TryGetValue(trimmed, out translation))
            {
                return translation;
            }

            // Build case-insensitive dictionary if needed
            if (TranslationsLower == null)
            {
                BuildLowerDictionary();
            }

            // Try case-insensitive match
            string lowerText = trimmed.ToLowerInvariant();
            if (TranslationsLower.TryGetValue(lowerText, out translation))
            {
                // If original was all uppercase, return uppercase translation
                if (IsAllUppercase(trimmed) && translation.Length > 0)
                {
                    return translation.ToUpperInvariant();
                }
                return translation;
            }

            // If text had __ markers but no translation found, return without markers
            // (handles already-translated text wrapped in markers)
            if (text.StartsWith("__") && text.EndsWith("__") && text.Length > 4)
            {
                return cleanText;
            }

            return null;
        }

        private static bool IsAllUppercase(string s)
        {
            foreach (char c in s)
            {
                if (char.IsLetter(c) && !char.IsUpper(c))
                {
                    return false;
                }
            }
            return true;
        }

        // Get dialogue translation
        internal static string GetDialogueText(string assetName)
        {
            string text;
            if (DialogueTexts.TryGetValue(assetName, out text))
            {
                return text;
            }
            return null;
        }

    }

    // ========== TEXT ASSET PATCHES ==========

    [HarmonyPatch(typeof(TextAsset))]
    public static class TextAssetPatches
    {

        [HarmonyPatch("get_text")]
        [HarmonyPostfix]
        static void TextAsset_get_text_Postfix(TextAsset __instance, ref string __result)
        {
            if (__instance == null || string.IsNullOrEmpty(__instance.name)) return;

            string russianText = RussianLocalization.GetDialogueText(__instance.name);
            if (russianText != null)
            {
                __result = russianText;
            }
        }

        [HarmonyPatch("get_bytes")]
        [HarmonyPostfix]
        static void TextAsset_get_bytes_Postfix(TextAsset __instance, ref byte[] __result)
        {
            if (__instance == null || string.IsNullOrEmpty(__instance.name)) return;

            string russianText = RussianLocalization.GetDialogueText(__instance.name);
            if (russianText != null)
            {
                __result = Encoding.UTF8.GetBytes(russianText);
            }
        }
    }

    // ========== UI TEXT PATCHES ==========

    [HarmonyPatch(typeof(Text))]
    public static class UnityUITextPatches
    {
        [HarmonyPatch("set_text")]
        [HarmonyPrefix]
        static void Text_set_text_Prefix(Text __instance, ref string value)
        {
            if (!RussianLocalization.IsInitialized) return;
            if (string.IsNullOrEmpty(value)) return;

            string translation = RussianLocalization.TranslateText(value);
            if (translation != null)
            {
                value = translation;

                // Replace font with Cyrillic font if available
                if (RussianLocalization.CyrillicFont != null && __instance != null)
                {
                    __instance.font = RussianLocalization.CyrillicFont;
                }
            }
        }

        [HarmonyPatch("OnEnable")]
        [HarmonyPostfix]
        static void Text_OnEnable_Postfix(Text __instance)
        {
            if (!RussianLocalization.IsInitialized) return;
            if (__instance == null || string.IsNullOrEmpty(__instance.text)) return;

            string translation = RussianLocalization.TranslateText(__instance.text);
            if (translation != null)
            {
                __instance.text = translation;
                if (RussianLocalization.CyrillicFont != null)
                {
                    __instance.font = RussianLocalization.CyrillicFont;
                }
            }
        }
    }

    // ========== RESOURCES.LOAD PATCHES ==========

    [HarmonyPatch(typeof(Resources))]
    public static class ResourcesPatches
    {
        [HarmonyPatch("Load", new Type[] { typeof(string), typeof(Type) })]
        [HarmonyPostfix]
        static void Resources_Load_Postfix(string path, Type systemTypeInstance, ref UnityEngine.Object __result)
        {
            TextAsset textAsset = __result as TextAsset;
            if (textAsset != null)
            {
                string russianText = RussianLocalization.GetDialogueText(textAsset.name);
                if (russianText != null)
                {
                    if (RussianLocalization.Log != null) RussianLocalization.Log.LogInfo(string.Format("[Resources.Load] Found Russian text for: {0}", textAsset.name));
                }
            }
        }
    }
}
