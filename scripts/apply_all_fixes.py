#!/usr/bin/env python3
"""Apply all fixes from fix_manifest.json to Russian text files."""
import os, sys, json, re
from collections import defaultdict

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXTS_DIR = os.path.join(BASE_DIR, "data", "Russian_Texts")
MANIFEST_PATH = os.path.join(BASE_DIR, "_dev", "output", "fix_manifest.json")

# ============================================================
# CHOICE TRANSLATIONS: eng_text -> Russian display text
# Format preserves emotes, uses Russian «» without spaces
# ============================================================
CHOICE_TR = {
    # --- Very common (10+ occurrences) ---
    "(Lie.)": "(Солгать.)",
    "« No. »": "«Нет.»",
    ":negative: « No. »": ":negative: «Нет.»",
    "(Do nothing.)": "(Ничего не делать.)",
    # --- Common (3-9 occurrences) ---
    "« No… »": "«Нет…»",
    "(Let him sleep.)": "(Дать ему поспать.)",
    "(Let her be.)": "(Оставить её.)",
    ":silence: (Let her be.)": ":silence: (Оставить её.)",
    "(Leave him alone.)": "(Оставить его в покое.)",
    ":silence: (Leave him alone.)": ":silence: (Оставить его в покое.)",
    ":silence: (Ignore him.)": ":silence: (Игнорировать его.)",
    "« Where to? »": "«Куда едем?»",
    "« What's going on? »": "«Что случилось?»",
    "« Why? »": "«Почему?»",
    ":taxi: (Drive away.)": ":taxi: (Уехать.)",
    "« No problem. »": "«Без проблем.»",
    ":smile: (Lie.)": ":smile: (Солгать.)",
    ":irony: (Lie.)": ":irony: (Солгать.)",
    ":love: (Lie.)": ":love: (Солгать.)",
    ":smoking: (Lie.)": ":smoking: (Солгать.)",
    "« How? »": "«Как?»",
    "« Yes? »": "«Да?»",
    # --- Emoted short phrases ---
    ":puzzled: « I don't understand… »": ":puzzled: «Я не понимаю…»",
    ":puzzled: « I don't understand. »": ":puzzled: «Я не понимаю.»",
    "« I don't understand… »": "«Я не понимаю…»",
    "« I don't understand. »": "«Я не понимаю.»",
    ":puzzled: « Huh? »": ":puzzled: «А?»",
    "« Huh? »": "«А?»",
    ":taxi: (Start the cab.)": ":taxi: (Завести такси.)",
    ":radio: (Turn off the radio.)": ":radio: (Выключить радио.)",
    ":radio: (Turn the radio off.)": ":radio: (Выключить радио.)",
    ":anger: (Throw her out of the cab.)": ":anger: (Выгнать её из такси.)",
    ":silence: (Let her go on.)": ":silence: (Дать ей продолжить.)",
    "(Let her go on.)": "(Дать ей продолжить.)",
    ":violence: « I attack Xenofex. »": ":violence: «Я атакую Ксенофекса.»",
    ":violence: « I rotate the ring. »": ":violence: «Я поворачиваю кольцо.»",
    ":silence: (Let the passenger decide.)": ":silence: (Пусть пассажир решит.)",
    ":smile: « Let's start? »": ":smile: «Начнём?»",
    ":smile: «Are you OK?»": ":smile: «Вы в порядке?»",
    # --- Short dialogue ---
    "« So? »": "«И что?»",
    "« But… »": "«Но…»",
    "« Hey! »": "«Эй!»",
    "« It's… »": "«Это…»",
    "« Spy. »": "«Шпион.»",
    "« I know. »": "«Я знаю.»",
    "« Will do. »": "«Сделаю.»",
    "« Listen… »": "«Послушайте…»",
    "« Understood. »": "«Понял.»",
    "« Airport? »": "«Аэропорт?»",
    "« Don't know… »": "«Не знаю…»",
    "« I can't… »": "«Я не могу…»",
    "« No idea. »": "«Понятия не имею.»",
    "« That's it. »": "«Вот и всё.»",
    "« All the time. »": "«Постоянно.»",
    "« Let's start? »": "«Начнём?»",
    "« Why not? »": "«Почему бы и нет?»",
    "« Leave it be. »": "«Оставьте это.»",
    "« Can I leave? »": "«Я могу идти?»",
    "« Calm down… »": "«Успокойтесь…»",
    "« A celebrity? »": "«Знаменитость?»",
    "« A bucket list? »": "«Список желаний?»",
    "« You're welcome. »": "«Не за что.»",
    "« Something wrong? »": "«Что-то не так?»",
    "« I can handle this. »": "«Я справлюсь.»",
    "« That's insane… »": "«Это безумие…»",
    "« It's complicated… »": "«Это сложно…»",
    "« I had no choice. »": "«У меня не было выбора.»",
    "« I'd spend it all. »": "«Я бы всё потратил.»",
    "« I'd do the same… »": "«Я бы поступил так же…»",
    "« I'd rather not. »": "«Лучше не надо.»",
    "« Your seatbelt… »": "«Ваш ремень безопасности…»",
    "« Where are you going? »": "«Куда вы едете?»",
    "« What are you talking about? »": "«О чём вы говорите?»",
    "« It feels… dangerous. »": "«Это кажется… опасным.»",
    "« I. Do not. Understand. »": "«Я. Не. Понимаю.»",
    "« You've drunk too much. »": "«Вы слишком много выпили.»",
    "« I look around… »": "«Я осматриваюсь…»",
    "« I held up my end of the deal. »": "«Я выполнил свою часть сделки.»",
    "« Let's stop talking about it… »": "«Давайте не будем об этом…»",
    "« What exactly brings you here? »": "«Что именно привело вас сюда?»",
    "« Couldn't find a good restaurant? »": "«Не нашли хороший ресторан?»",
    "« You shouldn't be doing this… »": "«Вам не стоит этого делать…»",
    "« It's so cold out… »": "«На улице так холодно…»",
    "« If you don't like it, I'm happy to stop. »": "«Если вам не нравится, я могу прекратить.»",
    "« So, who taught you how to play? »": "«И кто научил вас играть?»",
    "« I take a closer look at the tapestries… »": "«Я рассматриваю гобелены поближе…»",
    "« I hope to do the same when I retire. »": "«Надеюсь сделать то же самое, когда выйду на пенсию.»",
    "« You tried but couldn't reach her? »": "«Вы пытались, но не смогли до неё дозвониться?»",
    "« Some weird guy started following you… »": "«Какой-то странный парень начал вас преследовать…»",
    "« Your driver needed someone to talk to… »": "«Вашему водителю нужен был кто-то, с кем поговорить…»",
    ":love: « Sorry… I lost my dad too. »": ":love: «Простите… Я тоже потерял отца.»",
    ":irony: « Good luck with that. »": ":irony: «Удачи с этим.»",
    ":irony: « They're missing out on a great deal… »": ":irony: «Они многое теряют…»",
    ":puzzled: « I don't know what you're talking about. »": ":puzzled: «Я не знаю, о чём вы говорите.»",
    ":puzzled: « Who is Micheline? »": ":puzzled: «Кто такая Мишлин?»",
    ":puzzled: « Who is Mathilde? »": ":puzzled: «Кто такая Матильда?»",
    ":puzzled: « Wait, wasn't Mathilde your wife? »": ":puzzled: «Подождите, разве Матильда — не ваша жена?»",
    # --- Action choices ---
    "(Shoo the cat away.)": "(Прогнать кота.)",
    "(Go back to the driver's seat.)": "(Вернуться на водительское место.)",
    "(Leave her alone for now.)": "(Пока оставить её в покое.)",
    "(Break the ice.)": "(Начать разговор.)",
    "(Talk about the hospital.)": "(Заговорить о больнице.)",
    "(Change subjects.)": "(Сменить тему.)",
    "(Turn the heat all the way up.)": "(Включить отопление на максимум.)",
    "(Remain calm.)": "(Сохранять спокойствие.)",
    "(Smile at him.)": "(Улыбнуться ему.)",
    "(Say nothing more.)": "(Больше ничего не говорить.)",
    "(Apologize and move on.)": "(Извиниться и продолжить.)",
    "(Contradict her.)": "(Возразить ей.)",
    "(Ask how she guessed.)": "(Спросить, как она догадалась.)",
    "(Ask why she is going to Montparnasse.)": "(Спросить, зачем она едет на Монпарнас.)",
    "(Say nothing. Stare at her.)": "(Молчать. Смотреть на неё.)",
    "(Say nothing, stare at her. )": "(Молчать, смотреть на неё.)",
    "(Change your mind.)": "(Передумать.)",
    "(Let Pierre decide.)": "(Пусть Пьер решит.)",
    "(Let Sangrenat play.)": "(Пусть Сангренат сыграет.)",
    # --- Longer dialogue without «» (some files use different format) ---
    "«I can imagine.»": "«Могу представить.»",
    "«Can I help you?»": "«Могу я вам помочь?»",
    "«Good evening.»": "«Добрый вечер.»",
    "«The Masked Joker?»": "«Джокер в маске?»",
    "«You learn from your mistakes.»": "«На ошибках учатся.»",
    "«You're crazy.»": "«Вы с ума сошли.»",
    "«Talk to me about what?»": "«Поговорить о чём?»",
    "«Yeah, I think so.»": "«Да, думаю, что так.»",
    "«Are you sure?»": "«Вы уверены?»",
    "«This isn't the first time?»": "«Это не первый раз?»",
}

# ============================================================
# GARBAGE TRANSLATIONS: eng_text -> full Russian line
# Speaker names use Russian equivalents from SPEAKER_MAP
# ============================================================
GARBAGE_TR = {
    # --- Speaker dialogue ---
    'HUGO : « You think we\'ll get there on time? »':
        'ЮГО : «Думаете, мы доберёмся вовремя?»',
    'CAMILLE: « He must know some hotels. I\'m sure of it. Go ahead, ask. »':
        'КАМИЛЬ : «Он наверняка знает какие-нибудь отели. Я уверена. Давай, спроси.»',
    'ALICE: "A video game? Is that it? Or a movie?"':
        'АЛИСА : «Видеоигра? Вот как? Или фильм?»',
    'CAROLINA: "I keep calling it a hotel because my guests need to realize they are only passing through, that their real life is out there waiting for them…"':
        'КАРОЛИНА : «Я продолжаю называть это отелем, потому что мои гости должны понять, что они здесь лишь проездом, что их настоящая жизнь ждёт их где-то там…»',
    'CAROLINA: "You and I… we\'re on the same wavelength. We\'re working for the common good."':
        'КАРОЛИНА : «Мы с вами… на одной волне. Мы работаем на общее благо.»',
    'CAROLINA: "Here are my rules… or requests, if you would rather."':
        'КАРОЛИНА : «Вот мои правила… или просьбы, если вам так больше нравится.»',
    'CHIARA: "Nah, I shouldn\'t complain, really… At least I can take it easy, on my bike."':
        'КЬЯРА : «Не, мне не стоит жаловаться, правда… По крайней мере, я могу расслабиться на своём велосипеде.»',
    'CHIARA: "There\'s no one to REALLY mess around with me."':
        'КЬЯРА : «Нет никого, кто бы РЕАЛЬНО ко мне приставал.»',
    'SHOHREH: "It\'s the frequency that causes it."':
        'ШОХРЕ : «Это из-за частоты.»',
    'AMÉLIE: "Well personally, I think it\'s natural."':
        'АМЕЛИ : «Лично я считаю, что это естественно.»',
    "LÉONIE: 'African music?'":
        'ЛЕОНИ : «Африканская музыка?»',
    'PAULINE : « It\'s probably their way of preventing people like me from making a huge fucking mistake. »':
        'ПОЛИН : «Это, наверное, их способ не дать таким, как я, совершить чудовищную ошибку.»',
    'PAULINE : « Charles de Gaulle airport, please. »':
        'ПОЛИН : «Аэропорт Шарль-де-Голль, пожалуйста.»',
    'ANNABELLE: "Any chance of putting on some music?"':
        'АННАБЕЛЬ : «Не включите музыку?»',
    'MARC : « Plus, it\'ll be easier for everyone. »':
        'МАРК : «К тому же, так всем будет проще.»',
    'SOPHIE : « I\'ll call you tomorrow if that\'s ok? »':
        'СОФИ : «Я позвоню тебе завтра, хорошо?»',
    'PIERRE: « Shaïne… »':
        'ПЬЕР : «Шейн…»',
    'SHAÏNE: « No, it\'s because he\'s incapable of saying \'no.\' He\'s a… total doormat. »':
        'ШЕЙН : «Нет, это потому что он не способен сказать "нет". Он… полная тряпка.»',
    'SHAÏNE: « Well then? Do you dare open the door? »':
        'ШЕЙН : «Ну что? Осмелитесь открыть дверь?»',
    'SHAÏNE: « Why don\'t I explain it to our newcomer? »':
        'ШЕЙН : «Может, я объясню правила нашему новичку?»',
    'SHAÏNE: « But Xenofex would die too. »':
        'ШЕЙН : «Но Ксенофекс тоже умрёт.»',
    'AMIRA : «I screwed up. People are going to tear me apart.»':
        'АМИРА : «Я облажалась. Люди меня разорвут.»',
    'LOLA: "Cabbie took one look at me, heard my accent. Started going on about immigrants, how bad they were for French culture."':
        'ЛОЛА : «Таксист посмотрел на меня, услышал мой акцент. Начал рассуждать об иммигрантах, о том, как плохо они влияют на французскую культуру.»',
    'ROKSANA : «No, no. That\'s what he wants you to believe. What he wants you to think.»':
        'РОКСАНА : «Нет, нет. Это то, во что он хочет заставить вас поверить. То, что он хочет, чтобы вы думали.»',
    'JIM: "They aren\'t filling, if you know what I mean…"':
        'ДЖИМ : «Они не насыщают, если вы понимаете, о чём я…»',
    # --- Narration ---
    'There is a long pause. You are getting closer to Nation.':
        'Наступает долгая пауза. Вы приближаетесь к площади Насьон.',
    'The couple has begun whispering in the back again.':
        'Пара снова начала шептаться на заднем сиденье.',
    'The show aired on Wednesday afternoons, after school.':
        'Шоу выходило по средам после обеда, после школы.',
    'Her eyes meet yours. There\'s more to the kind grandmother in the back seat of your cab than meets the eye…':
        'Её глаза встречаются с вашими. В доброй бабушке на заднем сиденье вашего такси скрывается больше, чем кажется на первый взгляд…',
    'Classical music again… The flute grates on your ears.':
        'Снова классическая музыка… Флейта режет вам слух.',
    'She hands you the fare then exits the cab without a word.':
        'Она протягивает вам плату за проезд и выходит из такси, не сказав ни слова.',
    'Her voice is warm and deep and has a stunning accent…':
        'Её голос тёплый и глубокий, с потрясающим акцентом…',
    'The passenger looks at you and lets out a bitter laugh.':
        'Пассажир смотрит на вас и горько смеётся.',
    'She closes her eyes, collecting her thoughts, trying to dispel her negative emotions.':
        'Она закрывает глаза, собираясь с мыслями, пытаясь отогнать негативные эмоции.',
    'She looks at you closely, not sure what to think.':
        'Она внимательно смотрит на вас, не зная, что думать.',
    'This place has a calming effect on you, too. Some summer nights, you come here to take a nap.':
        'Это место действует успокаивающе и на вас. Иногда летними ночами вы приезжаете сюда вздремнуть.',
    'Her voice too is tinged with a note of sadness now.':
        'В её голосе тоже теперь слышится нотка грусти.',
    'Only when you hear the door closing again do you realize your passenger is back.':
        'Только когда вы слышите, как снова закрывается дверь, вы понимаете, что ваша пассажирка вернулась.',
    'You nod, put your notebook away, then turn the key in the ignition.':
        'Вы киваете, убираете блокнот и поворачиваете ключ зажигания.',
    'Back in the cab, you take a look at the back seat. It seems emptier than usual.':
        'Вернувшись в такси, вы бросаете взгляд на заднее сиденье. Оно кажется пустее обычного.',
    'The boy nods.':
        'Мальчик кивает.',
    'They swap numbers, throwing unfamiliar words at each other. You feel a slight migraine coming on.':
        'Они обмениваются числами, бросая друг другу незнакомые слова. Вы чувствуете приближение лёгкой мигрени.',
    'He attempts a smile while she buries herself in her papers.':
        'Он пытается улыбнуться, пока она зарывается в свои бумаги.',
    'A few minutes later, you arrive at Place de l\'Étoile.':
        'Через несколько минут вы прибываете на площадь Этуаль.',
    'He stares at you.':
        'Он пристально смотрит на вас.',
    'In a flash, he plunges a needle into your neck. Icy liquid spreads under your skin.':
        'В мгновение ока он втыкает иглу вам в шею. Ледяная жидкость растекается под кожей.',
    'The cops have only just let you back in your taxi.':
        'Полицейские только что позволили вам вернуться в такси.',
    'You\'ve barely gotten downstairs when you catch sight of Busset.':
        'Вы едва успели спуститься, как заметили Бюссе.',
    'You exit your place… and see Busset leaning up against your cab.':
        'Вы выходите из дома… и видите Бюссе, прислонившегося к вашему такси.',
    'Many long minutes later, you return to the pick up point.':
        'Через долгие минуты вы возвращаетесь к месту встречи.',
    'The atmosphere has turned tense, and in these situations you find it best to just… let the conversation end.':
        'Атмосфера стала напряжённой, и в таких ситуациях вы считаете лучшим просто… дать разговору завершиться.',
    'She sucks a gallon of air into her lungs and continues.':
        'Она делает глубокий вдох и продолжает.',
    'She enunciates each word as it rolls off her tongue.':
        'Она чётко произносит каждое слово.',
    'When he talks his tone is changed. It is smoother. More confident.':
        'Когда он говорит, его тон меняется. Он мягче. Увереннее.',
    'The cat has stopped meowing.':
        'Кот перестал мяукать.',
    'You can feel a whisker tickle your fingertips.':
        'Вы чувствуете, как ус щекочет кончики ваших пальцев.',
    'He pays his fare. You\'re unable to say anything.':
        'Он платит за проезд. Вы не можете вымолвить ни слова.',
    'Yes… later… you\'ll have time.':
        'Да… потом… у вас ещё будет время.',
    # --- Player narrated dialogue (in guillemets, no speaker) ---
    '« Anything I want? »':
        '«Всё, что захочу?»',
    '« What do you call the Japanese mafia again? »':
        '«Как там называется японская мафия?»',
    '« What about you? »':
        '«А как насчёт вас?»',
    # --- Quoted dialogue without speaker prefix ---
    '"And I\'m looking for the person who did it."':
        '«И я ищу того, кто это сделал.»',
    # --- EMPTY passage content ---
    'She withdraws into herself, staring out the window at the road.':
        'Она замыкается в себе, глядя в окно на дорогу.',
}


def norm(s):
    """Normalize Unicode quotes to ASCII for reliable matching."""
    return (s
        .replace('\u2018', "'").replace('\u2019', "'")   # curly single quotes
        .replace('\u201c', '"').replace('\u201d', '"')    # curly double quotes
        .replace('\u2013', '-').replace('\u2014', '-')    # en/em dash
    )

# Pre-normalize all dict keys
CHOICE_N = {norm(k): v for k, v in CHOICE_TR.items()}
GARBAGE_N = {norm(k): v for k, v in GARBAGE_TR.items()}


def main():
    with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
        fixes = json.load(f)

    # Group by file
    by_file = defaultdict(list)
    for fix in fixes:
        by_file[fix['file']].append(fix)

    total_applied = 0
    total_skipped = 0
    skipped = []

    for fname in sorted(by_file):
        filepath = os.path.join(TEXTS_DIR, fname)
        if not os.path.exists(filepath):
            print(f"SKIP: {fname} not found")
            continue

        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        applied = 0
        for fix in by_file[fname]:
            ln = fix['line']
            ft = fix['type']
            eng = fix.get('eng_text', '')

            if ft in ('CHOICE', 'TARGET'):
                target = fix['eng_target']
                tr = CHOICE_N.get(norm(eng))
                if tr:
                    lines[ln - 1] = f"*{tr} -> {target}\n"
                    applied += 1
                else:
                    skipped.append((fname, ln, ft, eng))

            elif ft == 'GARBAGE':
                tr = GARBAGE_N.get(norm(eng))
                if tr:
                    lines[ln - 1] = tr + '\n'
                    applied += 1
                else:
                    skipped.append((fname, ln, ft, eng))

            elif ft == 'EMPTY':
                tr = GARBAGE_N.get(norm(eng), '')
                if tr:
                    passage = fix['passage']
                    header = f"=== {passage}"
                    for i, line in enumerate(lines):
                        if line.strip() == header:
                            # Insert after header + blank line
                            idx = i + 1
                            while idx < len(lines) and lines[idx].strip() == '':
                                idx += 1
                            lines.insert(idx, tr + '\n')
                            applied += 1
                            break
                else:
                    skipped.append((fname, ln, ft, eng))

        if applied:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            print(f"  {fname}: {applied} fixes applied")

        total_applied += applied
        total_skipped += len([s for s in skipped if s[0] == fname])

    print(f"\n=== TOTAL: {total_applied} applied, {len(skipped)} skipped ===")
    if skipped:
        print("\nMissing translations:")
        for fname, ln, ft, eng in skipped:
            print(f"  [{ft}] {fname}:{ln} -> {eng[:100]}")


if __name__ == "__main__":
    main()
