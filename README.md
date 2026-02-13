# Night Call - Русификатор

Полная русская локализация для игры **Night Call** (Monkey Moon / Raw Fury).

## Что переведено

- Все диалоги — 200 диалоговых объектов, 5371 пассаж
- Весь интерфейс — 789 ключей UI + 30,000+ текстовых строк
- Имена пассажиров — 115 полных имён
- Варианты выбора и ветвления диалогов
- Газеты, радио, телефонные звонки, сюжетные сцены

## Установка

### Из релиза (рекомендуется)

1. Скачайте `NightCallRussian-Setup.exe` из [Releases](../../releases/latest)
2. Запустите — установщик автоматически найдёт папку с игрой
3. Готово — запустите Night Call через Steam

### Вручную

Скопируйте всё содержимое папки `data/` в корневую папку игры:

```
Steam\steamapps\common\Night Call\
```

Структура после установки:

```
Night Call/
├── BepInEx/
│   ├── core/              ← DLL-файлы фреймворка
│   └── plugins/
│       └── NightCallRussian.dll
├── Russian_UI/            ← Переводы интерфейса
├── Russian_Texts/         ← 155 файлов диалогов
├── Generated_SDF/         ← Атласы кириллических шрифтов
├── Fonts_Cyrillic/        ← TTF-файлы шрифтов
├── passage_dump.txt       ← Данные маппинга пассажей
├── winhttp.dll            ← Загрузчик BepInEx
├── doorstop_config.ini
└── Night Call.exe
```

## Удаление

Удалите файл `winhttp.dll` из папки игры — это отключит BepInEx и все моды.

Для полного удаления также удалите: `BepInEx/`, `Russian_UI/`, `Russian_Texts/`,
`Generated_SDF/`, `Fonts_Cyrillic/`, `doorstop_config.ini`, `passage_dump.txt`.

## Сборка из исходников

### Полная сборка (рекомендуется)

```bash
build.bat
```

Скрипт выполнит все шаги: соберёт мод, упакует data.zip, соберёт установщик.
Результат: `NightCallRussian-Setup.exe` в корне репозитория.

### Только мод

```bash
cd src/Mod
dotnet build -c Release
```

Результат: `bin/Release/net46/NightCallRussian.dll` — скопировать в `BepInEx/plugins/`.

### Только установщик

```bash
cd src/Installer
dotnet publish -c Release
```

Результат: `bin/Release/net472/publish/NightCallRussian-Setup.exe`

## Структура проекта

```
├── src/
│   ├── Mod/                    # Исходный код мода (C#, .NET 4.6)
│   └── Installer/              # Установщик (C#, .NET 4.7.2)
├── data/                       # Файлы мода для установки
├── scripts/                    # Утилиты (Python)
├── DOCUMENTATION_RU.md         # Техническая документация (включая шрифты и SDF)
└── LICENSE                     # CC BY 4.0
```

## Техническая информация

- BepInEx 5.4.23 + Harmony для патчинга Unity 2018.4
- Три слоя перевода: ключи локализации, замена пассажей, перехват TMP_Text
- Кириллические шрифты через SDF-атласы в рантайме
- Подробнее: [DOCUMENTATION_RU.md](DOCUMENTATION_RU.md)

## Автор

**Artem Lytkin** ([4RH1T3CT0R](https://github.com/4RH1T3CT0R7))

## Лицензия

[CC BY 4.0](LICENSE) — свободное использование с указанием автора.

---

*Night Call является собственностью Monkey Moon и Raw Fury. Данный мод — неофициальная фанатская локализация.*
