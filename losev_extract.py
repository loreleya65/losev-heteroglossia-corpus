# -*- coding: utf-8 -*-
# РЕДАКЦИЯ 5.8 — 30.08.2026. Проверить экземпляр: python3 check_revision.py
"""
losev_extract.py — извлечение иноязычных вкраплений из поэтических сборников
Льва Лосева.

ИСПРАВЛЕННАЯ ВЕРСИЯ (v2). Что изменено по сравнению с первым вариантом
скрипта — см. блок «ЖУРНАЛ ИСПРАВЛЕНИЙ» в конце файла.

Главное методологическое разграничение
--------------------------------------
Скрипт реализует ТОЛЬКО ПРОЦЕДУРУ 1 — сплошную выборку графической латиницы
регулярным выражением. Это НЕ метод Out-of-Vocabulary: pymorphy3 работает со
словарём OpenCorpora, который содержит только кириллические словоформы, и к
латинским токенам неприменим (парсер помечает их тегом LATN и не проверяет по
словарю). Кириллические вкрапления («гемютно», «кавьяр», «мамлакат») ищутся
отдельной ПРОЦЕДУРОЙ 2 — см. losev_oov.py.

Корпус
------
  desant_1985.txt      — «Чудесный десант» (Tenafly: Эрмитаж, 1985)
  tainii_sovetnik.txt  — «Тайный советник» (Tenafly: Эрмитаж, 1987)
  stikhi_2012.txt      — «Стихи» (СПб.: Изд-во Ивана Лимбаха, 2012), полный
                         свод; в основной корпус НЕ входит, используется
                         только как контрольный источник для верификации
                         OCR-чтений прижизненных изданий.

Основной корпус исследования = «Чудесный десант» + «Тайный советник».

Запуск:  python3 losev_extract.py
Выход:   losev_foreign_inclusions.xlsx  (листы «Вкрапления», «Сводка», «Отсев»)
"""

from __future__ import annotations   # ИСПРАВЛЕНИЕ: list[str] работает и на 3.7–3.8

import os
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

# --------------------------------------------------------------------------- #
# 1. Конфигурация                                                             #
# --------------------------------------------------------------------------- #

# ИСПРАВЛЕНИЕ (ред. 5.6): абсолютные пути /mnt/user-data/... заменены на
# разрешаемые по месту. Рецензент, скачавший архив, запускает скрипт у себя,
# и жёстко зашитый путь падал бы у него с FileNotFoundError.
#
# Порядок поиска папки с текстами корпуса:
#   1) первый аргумент командной строки;
#   2) переменная окружения LOSEV_CORPUS;
#   3) ./uploads, ./corpus, ./texts рядом со скриптом;
#   4) сама папка скрипта.
BASE_DIR = Path(__file__).resolve().parent


def resolve_corpus_dir(argv: list[str] | None = None) -> Path:
    argv = argv if argv is not None else sys.argv[1:]
    if argv:
        return Path(argv[0]).expanduser().resolve()
    env = os.environ.get("LOSEV_CORPUS")
    if env:
        return Path(env).expanduser().resolve()
    for name in ("uploads", "corpus", "texts"):
        cand = BASE_DIR / name
        if cand.is_dir():
            return cand
    legacy = Path("/mnt/user-data/uploads")          # среда сборки материалов
    if legacy.is_dir():
        return legacy
    return BASE_DIR


def resolve_output_path(argv: list[str] | None = None) -> Path:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) > 1:
        return Path(argv[1]).expanduser().resolve()
    env = os.environ.get("LOSEV_OUTPUT")
    if env:
        return Path(env).expanduser().resolve()
    legacy = Path("/mnt/user-data/outputs")
    if legacy.is_dir():
        return legacy / "losev_foreign_inclusions.xlsx"
    return BASE_DIR / "losev_foreign_inclusions.xlsx"


UPLOADS = resolve_corpus_dir()
OUTPUT = resolve_output_path()
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

EARLY_AMER = "Ранний американский"
MIDDLE = "Средний"
LATE = "Поздний"

# Книги внутри собрания 2012 г.: (имя, год, период, якорь-строка).
BOOKS_IN_2012 = [
    ("Чудесный десант",                1985, EARLY_AMER, "1975–1985"),
    ("Тайный советник",                1987, EARLY_AMER, "1985–1987"),
    ("Новые сведения о Карле и Кларе", 1996, MIDDLE,     "1987–1996"),
    ("Послесловие",                    1998, MIDDLE,     "1996–1998"),
    ("Sisyphus Redux",                 2000, LATE,       "1997–2000"),
    ("Как я сказал",                   2005, LATE,       "Как я сказал"),
    ("Говорящий попугай",              2009, LATE,       "Говорящий попугай"),
]

# ИСПРАВЛЕНИЕ: имена файлов задаются шаблоном, а не точной строкой, — длинные
# имена с диакритикой и подчёркиваниями больше не ломают доступ к файлу.
FILES = [
    {
        "glob": "desant_1985*.txt",
        "title": "Чудесный десант",
        "year": 1985,
        "period": EARLY_AMER,
        "format": "ermitazh",
        "in_core_corpus": True,
        "sections": {"ПАМЯТИ ВОДКИ", "ПРОДЛЕННЫЙ ДЕНЬ",
                     "ПРОТИВ МУЗЫКИ", "УРОК ФОТОГРАФИИ"},
        "start_marker": "ПАМЯТИ ВОДКИ",
    },
    {
        "glob": "tainii_sovetnik*.txt",
        "title": "Тайный советник",
        "year": 1987,
        "period": EARLY_AMER,
        "format": "ermitazh",
        "in_core_corpus": True,
        "sections": set(),
        "start_marker": None,
    },
    {
        # Контрольный источник, в основной корпус не входит.
        # ИСПРАВЛЕНИЕ (ред. 5.6): единственный шаблон *Losiev*.txt молча
        # не находил файл, названный stikhi_2012.txt или losev_2012.txt
        # (через «e», а не «ie»), — контрольный свод тогда просто не
        # обрабатывался, без предупреждения. Задан список шаблонов.
        "glob": ["*[Ll]os*2012*.txt", "*[Ss]tikhi*2012*.txt",
                 "*Losiev*.txt", "*2012*.txt"],
        "title": "Стихи (СПб.: Изд-во Ивана Лимбаха, 2012)",
        "year": 2012,
        "period": "Полное собрание (контрольный источник)",
        "format": "limbakh_2012",
        "in_core_corpus": False,
        "sections": {"ПАМЯТИ ВОДКИ", "ПРОДЛЕННЫЙ ДЕНЬ",
                     "И ДРУГИЕ ВОСПОМИНАНИЯ", "О ХОЛОДНОЙ ПОГОДЕ",
                     "ПРОТИВ МУЗЫКИ", "УРОК ФОТОГРАФИИ", "УРОК ФОТОГ РАФИИ",
                     "ПРИЛОЖЕНИЕ 1", "ПРИЛОЖЕНИЕ 2", "ПРИЛОЖЕНИЕ 3"},
        "start_marker": "ПАМЯТИ ВОДКИ",
    },
]

STOP_MARKERS = {"СОДЕРЖАНИЕ", "ОГЛАВЛЕНИЕ", "CONTENTS"}

# --------------------------------------------------------------------------- #
# 2. Регулярные выражения                                                     #
# --------------------------------------------------------------------------- #

RE_ASTERISK_TITLE = re.compile(r"^\s*\*(?:\s*\*){1,2}\s*$")
RE_CAPS_CYR = re.compile(r"^[А-ЯЁ][А-ЯЁ\s\.\d—\-:№]*$")
RE_LATIN_TITLE = re.compile(r"^[A-ZÀ-Ý][A-Za-zÀ-ÖØ-öø-ÿĀ-ž\s\.\d—\-:’'\"]*$")
RE_NUMBERED_PREFIX = re.compile(r"^\d+(?:\.\d+)?\.\s+")
RE_SIGNATURE = re.compile(r"^[А-ЯЁA-Z]\.?\s*$")
RE_PAGE_NUM = re.compile(r"^\d{1,3}$")
RE_ROMAN = re.compile(r"^[IVXLC]{1,6}$")
RE_STANZA_SEP = re.compile(r"^\s*\*\s*\*?\s*$")
RE_YEAR_RANGE = re.compile(r"^\d{4}\s?[\u2013\u2014\-]\s?\d{4}$")
RE_TOC_LEADER = re.compile(r"\.{6,}")
# допустимый разрыв между соседними токенами одной иноязычной единицы
# Допустимый разрыв между соседними токенами ОДНОЙ иноязычной единицы.
# ИСПРАВЛЕНИЕ: добавлены запятая, двоеточие и амперсанд. Без них правило 2
# («связная иноязычная фраза = одна единица») приходилось применять вручную:
# библиографическая сноска «Loseff, On the Beneficence…» распадалась на восемь
# записей, «Voznesensky & Rosenkreuz» — на две, эпиграф из Бродского — на три.
GAP_PATTERN = r"[\s\-—‒–’'.,:&]{0,3}"

# Расширенный зазор: короткий разрыв, ВНУТРИ которого стоит число.
# ИСПРАВЛЕНИЕ: в библиографическом описании соседние иноязычные фрагменты
# разделены годом, номером страницы или ценой («…in Kommission, 1984, S. 274,
# DM38»). Обычный зазор их не перешагивает, и от сноски отваливались обрывки
# «S» и «DM» — по правилу 2 это части одной единицы, а не самостоятельные
# вкрапления. Требование цифры внутри зазора оставляет правило узким: разрыв
# без цифр (например, многоточие) по-прежнему разделяет единицы, иначе
# склеивались бы соседние, но независимые фразы.
GAP_NUMERIC = r"[\s\-—‒–’'.,:&]{0,4}\d{1,4}[\s\-—‒–’'.,:&]{0,4}"

FOREIGN_LETTER = (
    "A-Za-z"
    "\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u00FF\u0100-\u017E"   # латиница с диакритикой
    "\u0386-\u03CE"                                          # греческий
    "\u0590-\u05FF"                                          # иврит
)
RE_TOKEN = re.compile(f"[{FOREIGN_LETTER}](?:[{FOREIGN_LETTER}\u2019'\\-])*")
RE_CYRILLIC = re.compile(r"[А-Яа-яЁё]")

# ИСПРАВЛЕНИЕ (ред. 5.6): прежде короткая строка проверялась шаблоном
# r"[A-Za-z]{1,2}", то есть чистым ASCII. Отдельно стоящая строка из одной-двух
# букв с диакритикой — французское «À», «Ô», «Ça» — под него не подходила и
# отбраковывалась как OCR-мусор ещё до проверки контекста. Класс расширен до
# того же FOREIGN_LETTER, которым выделяются сами токены.
RE_SHORT_FOREIGN = re.compile(f"[{FOREIGN_LETTER}]{{1,2}}")

VOWELS = set(
    "aeiouyAEIOUY"
    "áéíóúýàèìòùỳâêîôûŷäëïöüÿåœæ"
    "ÁÉÍÓÚÝÀÈÌÒÙŶÂÊÎÔÛÄËÏÖÜŸÅŒÆ"
    "αεηιοωυάέήίόύώϊϋΑΕΗΙΟΩΥΆΈΉΊΌΎΏ"
    "אהוי"
)

# ИСПРАВЛЕНИЕ (замечание рецензента № 1): аббревиатуры без гласных больше не
# отбрасываются. Вместо «разрешить всё короче 3–4 букв» — закрытый белый список:
# сплошное разрешение коротких токенов забило бы таблицу OCR-мусором («лл», «іі»)
# и латинизированными обрывками кириллицы.
ABBREVIATIONS = {
    "ph", "phd", "d", "nb", "ps", "pp", "vs", "st", "nd", "rd", "th",
    "dm", "kg", "km", "mm", "cm", "no", "op", "cf", "ib", "ed", "bbc", "usa",
}

# Однобуквенные латинские токены допускаются только в англоязычном окружении:
# при OCR кириллическое «и» регулярно распознаётся как «i», «а» — как «a».
SINGLE_LETTER_OK = {"i", "a"}

# Латинские буквы, графически неотличимые от кириллических. Одиночная такая
# буква в кириллическом окружении — почти всегда кириллица, прочитанная как
# латиница: «Даниил Иваныч Х.» (Хармс), «Х.-Э. Сирло» (Cirlot).
HOMOGLYPHS = set("ABCEHKMOPTXY")

# Гласные с акутом, которыми в русских изданиях ставят ударение («чтó»,
# «безóбразны»). В сборниках 1985 и 1987 гг. таких знаков нет ни одного,
# но в своде 2012 г. они встречаются (30 случаев) и без этой проверки дают
# ложные «испанские» вкрапления из одной буквы.
STRESS_VOWELS = set("áóéúýíÁÓÉÚÝÍ")

# Токены, отбрасываемые как заведомый OCR-мусор (проверено по изданию 2012 г.).
OCR_NOISE = {
    "at",       # «две At, две Ж» — в изд. 2012 «две Аt» = кириллич. «А» + «т»
    "ikno",     # «Slavist-ikNo. 31» — разрыв «Slavistik No.» переносом
    "ula",      # «uLa vida es sueno» — открывающая кавычка распознана как «u»
    "iucet",    # «Ante Іисет» — «lucem», И/І смешаны при распознавании
}

# --------------------------------------------------------------------------- #
# 3. Чтение файлов                                                            #
# --------------------------------------------------------------------------- #


def read_text(path: Path) -> str:
    """ИСПРАВЛЕНИЕ: файл в cp1251 больше не роняет скрипт UnicodeDecodeError."""
    for enc in ("utf-8", "utf-8-sig", "cp1251", "koi8-r"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def resolve(pattern) -> Path | None:
    """Находит файл по шаблону или списку шаблонов.

    ИСПРАВЛЕНИЕ (ред. 5.6): принимает список и перебирает шаблоны по порядку.
    Единственный жёсткий шаблон не находил файл, названный иначе, чем ожидал
    автор, и книга молча выпадала из разбора.
    """
    patterns = [pattern] if isinstance(pattern, str) else list(pattern)
    for pat in patterns:
        hits = sorted(UPLOADS.glob(pat))
        if hits:
            return hits[0]
    return None


def normalize(s: str) -> str:
    """Нормализация строки перед сравнением с названиями разделов.

    ИСПРАВЛЕНИЕ: раньше «ПАМЯТИ ВОДКИ» с кавычками или неразрывным пробелом
    не совпадало со строкой из множества sections, и раздел терялся.
    """
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\u00a0", " ").replace("\u2019", "'")
    s = re.sub(r"[«»„“”’'‘\"]+", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip(" *†‡§•·—-").strip()


# --------------------------------------------------------------------------- #
# 4. Фильтры                                                                  #
# --------------------------------------------------------------------------- #


def _has_clean_case(token: str) -> bool:
    """lowercase / UPPERCASE / Capitalized — нормальные регистровые схемы."""
    letters = [c for c in token if c.isalpha()]
    if not letters:
        return True
    if all(c.islower() for c in letters):
        return True
    if all(c.isupper() for c in letters):
        return True
    return letters[0].isupper() and all(c.islower() for c in letters[1:])


def is_garbage_line(line: str) -> bool:
    """Отсев строк, порождённых сбоем распознавания.

    ИСПРАВЛЕНИЕ (замечание рецензента № 2): прежнее условие
        if cyr < 5 or lat < 5: return False
    возвращало «не мусор» практически для любой строки и не отсеивало ничего.
    Новая логика опирается на признаки, реально присутствующие в сканах
    «Эрмитажа»: перевёрнутые строки и смешение алфавитов внутри слова.
    """
    s = line.strip()
    # ИСПРАВЛЕНИЕ: короткая строка отбраковывается, КРОМЕ случая, когда она
    # целиком состоит из одной-двух латинских букв. Иначе изолированная
    # стихотворная строка «I» (местоимение в англоязычной цитате) не доходила
    # до looks_like_word и терялась ещё до проверки контекста.
    if len(s) < 3 and not RE_SHORT_FOREIGN.fullmatch(s):
        return True
    if not any(c.isalpha() for c in s):
        return True
    if RE_TOC_LEADER.search(s):          # строка оглавления
        return True

    tokens = re.findall(r"[A-Za-zА-Яа-яЁё]{2,}", s)
    if len(tokens) < 3:
        return False

    # (а) токены, внутри которых смешаны кириллица и латиница, — верный признак
    #     развала распознавания («HWBhBdH», «OJOHHdhOdttBC»)
    mixed = sum(
        1 for t in tokens
        if RE_CYRILLIC.search(t) and re.search(r"[A-Za-z]", t)
    )
    if mixed >= 2:
        return True

    # (б) хаотический регистр внутри длинных латинских токенов
    lat_tokens = [t for t in tokens if len(t) >= 3 and t.isascii()]
    if len(lat_tokens) >= 3:
        dirty = sum(1 for t in lat_tokens if not _has_clean_case(t))
        if dirty >= 3:
            return True

    return False


def looks_like_word(token: str, line: str = "", start: int = -1,
                    latin_context: bool = False) -> tuple[bool, str]:
    """Является ли латинский фрагмент словом. Возвращает (годен, причина отсева)."""
    t = token.lower()

    if t in OCR_NOISE:
        return False, "OCR-артефакт (сверено с изд. 2012)"

    # ИСПРАВЛЕНИЕ: латинская буква, ВПЛОТНУЮ примыкающая к кириллице, — это не
    # вкрапление, а русский знак ударения, набранный латинским омоглифом
    # («безóбразны», «чтó», «мозолéй», «ВАЛÉРИК»), либо развал распознавания.
    # Диапазон U+00C0–U+00FF содержит á é ó ý, которыми в цифровых изданиях
    # (в т. ч. в своде 2012 г.) верстается ударение. Без этой проверки скрипт
    # порождал десятки однобуквенных «испанских» и «французских» вкраплений.
    if start >= 0 and line:
        before = line[start - 1] if start > 0 else ""
        after = line[start + len(token)] if start + len(token) < len(line) else ""
        touches_cyr = bool(RE_CYRILLIC.match(before or "")
                           or RE_CYRILLIC.match(after or ""))
        if touches_cyr and any(c in STRESS_VOWELS for c in token):
            return False, "гласная с акутом внутри русского слова (знак ударения)"
        # Одиночный гомоглиф рядом с кириллицей или перед точкой/дефисом —
        # это кириллическая буква, прочитанная как латинская.
        if len(token) == 1 and token in HOMOGLYPHS:
            nearby = (line[max(0, start - 2): start]
                      + line[start + 1: start + 4])
            if touches_cyr or RE_CYRILLIC.search(nearby):
                return False, "гомоглиф кириллической буквы"
        # Прочие случаи вплотную к кириллице оставляем: именно так устроены
        # настоящие графические гибриды («Shit-c»), которые нам и нужны.

    # ИСПРАВЛЕНИЕ: прежняя проверка требовала, чтобы сразу за «I» шёл пробел и
    # строчное английское слово. Из-за этого местоимение отбрасывалось перед
    # знаком препинания и в конце строки («…as I, the poet…», «I did»).
    # Новое правило: римской цифрой считается только ИЗОЛИРОВАННОЕ вхождение —
    # токен занимает всю строку целиком (возможно, с точкой), как и бывает при
    # нумерации частей у Лосева.
    if RE_ROMAN.fullmatch(token):
        stripped = line.strip().rstrip(".") if line else token
        isolated = stripped == token
        # ИСПРАВЛЕНИЕ: изолированная строка «I» — не всегда номер части. В
        # англоязычной цитате, разбитой на стихотворные строки, местоимение
        # может занимать строку целиком. Признак latin_context вычисляется в
        # find_inclusions по соседним строкам: если хоть одна из них
        # преимущественно латинская, «I» считается местоимением.
        # В корпусе 1985/1987 гг. таких строк нет, но при переносе скрипта на
        # поздние сборники и на англоязычные цитаты правило понадобится.
        if isolated and len(token) == 1 and latin_context:
            return True, ""
        if isolated or len(token) > 1:
            return False, "римская цифра / нумерация части"

    if re.fullmatch(r"[IiLl]{2,6}", t):
        return False, "OCR-артефакт (сцепка I/l)"

    if len(token) == 1:
        # ИСПРАВЛЕНИЕ: буква с диакритикой не может быть OCR-чтением кириллицы,
        # поэтому «à» во французском «à la gitane» принимается безоговорочно.
        if not token.isascii():
            return True, ""
        # Прописная буква с точкой — инициал или часть аббревиатуры («Ph. D.»).
        if token.isupper() and start >= 0 and line[start + 1: start + 2] == ".":
            return True, ""
        if t not in SINGLE_LETTER_OK:
            return False, "однобуквенный токен"
        # «i» и «a» принимаются, только если рядом стоит латиница, а не кириллица
        left = line[max(0, start - 2): start] if start >= 0 else ""
        right = line[start + 1: start + 3] if start >= 0 else ""
        if RE_CYRILLIC.search(left + right):
            return False, "однобуквенный токен в кириллическом окружении"
        return True, ""

    if t in ABBREVIATIONS:
        return True, ""                       # аббревиатуры без гласных — годны

    if not any(c in VOWELS for c in token):
        return False, "нет гласных и не входит в список аббревиатур"

    # ИСПРАВЛЕНИЕ: порог снижен с 0.15 до 0.10 — при 0.15 отсекалось немецкое
    # schwach (одна гласная на семь букв), т. е. половина каламбура sehr schwach.
    if sum(1 for c in token if c in VOWELS) / len(token) < 0.10:
        return False, "аномально низкая доля гласных"

    if not _has_clean_case(token):
        return False, "смешанный регистр (OCR)"

    return True, ""


# ИСПРАВЛЕНИЕ (ред. 5.5). Прежняя detect_script возвращала одну строку, в
# которой графический тип был склеен с языковой атрибуцией («латиница (нем.
# диакритика)»), а атрибуция выводилась цепочкой if по классам символов. Схема
# давала систематическую ошибку на знаках, общих для нескольких орфографий:
# «ü» входит и в немецкий, и во французский ряд, но немецкая ветка стояла
# первой, поэтому capharnaüm и aiguë получали немецкую помету. Знак письма в
# принципе не определяет языка: «é» есть во французском, испанском, венгерском
# и чешском.
#
# Поэтому графика и язык разведены. detect_script отвечает только на вопрос
# «какой это алфавит», а знаки диакритики выносятся отдельным столбцом как
# наблюдаемый факт. Гипотеза о языке-источнике формулируется как МНОЖЕСТВО
# совместимых орфографий и служит подсказкой верификатору, а не решением:
# окончательная атрибуция делается по контексту вручную (§ 2.3 статьи).

#: Знак диакритики → орфографии, в которых он употребителен. Множества
#: пересекаются намеренно: это и есть содержательный факт о письме.
DIACRITIC_ORTHOGRAPHIES = {
    "ä": {"нем.", "швед.", "фин."},
    "ö": {"нем.", "швед.", "фин.", "венг."},
    "ü": {"нем.", "фр.", "венг.", "тур."},
    "ß": {"нем."},
    "à": {"фр.", "итал.", "порт."},
    "â": {"фр.", "порт.", "рум."},
    "ç": {"фр.", "порт.", "тур."},
    "é": {"фр.", "исп.", "порт.", "венг.", "чеш."},
    "è": {"фр.", "итал."},
    "ê": {"фр.", "порт."},
    "ë": {"фр.", "нидерл."},
    "î": {"фр.", "рум."},
    "ï": {"фр.", "нидерл."},
    "ô": {"фр.", "порт."},
    "û": {"фр."},
    "ù": {"фр.", "итал."},
    "ÿ": {"фр."},
    "œ": {"фр."},
    "æ": {"фр.", "дат.", "норв.", "исл."},
    "á": {"исп.", "порт.", "венг.", "чеш."},
    "í": {"исп.", "порт.", "венг.", "чеш."},
    "ó": {"исп.", "порт.", "польск.", "венг."},
    "ú": {"исп.", "порт.", "венг.", "чеш."},
    "ý": {"чеш.", "исл."},
    "ñ": {"исп."},
    "õ": {"порт.", "эст."},
    "ã": {"порт."},
    "å": {"швед.", "дат.", "норв."},
    "ø": {"дат.", "норв."},
}


def detect_script(token: str) -> str:
    """Алфавит токена — и только он. Язык здесь не определяется."""
    if any("\u0590" <= c <= "\u05FF" for c in token):
        return "иврит"
    if any("\u0370" <= c <= "\u03FF" for c in token):
        return "греческий"
    if any("\u0400" <= c <= "\u04FF" for c in token) and any(
            "a" <= c.lower() <= "z" for c in token):
        return "смешанная графика (латиница + кириллица)"
    if any(not c.isascii() and c.isalpha() for c in token):
        return "латиница с диакритикой"
    return "латиница"


def diacritics(token: str) -> str:
    """Перечень встреченных знаков латинской диакритики.

    Наблюдаемый факт, не гипотеза о языке. Кириллические и греческие буквы
    сюда не попадают: в смешанном токене они значат другое (см. detect_script).
    """
    marks = []
    for c in token:
        if not c.isalpha() or c.isascii():
            continue
        if not ("\u00C0" <= c <= "\u024F"):          # только латиница Latin-1/A/B
            continue
        if c.lower() not in marks:
            marks.append(c.lower())
    return ", ".join(marks)


def orthography_hint(token: str) -> str:
    """Орфографии, совместимые со ВСЕМИ знаками диакритики токена.

    Возвращает подсказку для ручной верификации, а не атрибуцию. Если знаки
    указывают на разные орфографии, перечисляются все совместимые; если
    пересечение пусто (знаки из несовместимых рядов) — это сигнал проверить
    токен на OCR-артефакт.
    """
    sets = [DIACRITIC_ORTHOGRAPHIES[c.lower()] for c in token
            if c.lower() in DIACRITIC_ORTHOGRAPHIES]
    if not sets:
        return ""                                  # диакритики нет — подсказки нет
    common = set.intersection(*sets)
    if not common:
        return "знаки из несовместимых рядов — проверить на OCR"
    if len(common) == 1:
        return next(iter(common))
    return " / ".join(sorted(common)) + " (неоднозначно)"


# --------------------------------------------------------------------------- #
# 5. Парсер книги                                                             #
# --------------------------------------------------------------------------- #


def looks_like_title_line(s: str, sections: set) -> bool:
    if not s:
        return False
    if RE_ASTERISK_TITLE.fullmatch(s):
        return True
    s_clean = RE_NUMBERED_PREFIX.sub("", normalize(s))
    if not s_clean:
        return False
    if RE_SIGNATURE.fullmatch(s_clean):
        return False
    if s_clean in sections:
        return False
    if RE_PAGE_NUM.fullmatch(s_clean):
        return False
    if RE_ROMAN.fullmatch(s_clean):
        return False
    if RE_CAPS_CYR.fullmatch(s_clean) and sum(c.isalpha() for c in s_clean) >= 3:
        return True
    if (RE_LATIN_TITLE.fullmatch(s_clean)
            and len(s_clean) <= 60
            and sum(c.isalpha() for c in s_clean) >= 3):
        return True
    return False


def parse_book(text: str, sections: set, start_marker: str | None,
               file_format: str = "ermitazh") -> list[dict]:
    lines = text.splitlines()
    n = len(lines)
    sections_n = {normalize(x) for x in sections}

    start_idx = 0
    if start_marker:
        marker_n = normalize(start_marker)
        for i, ln in enumerate(lines):
            if normalize(ln) == marker_n:
                start_idx = i
                break

    # ИСПРАВЛЕНИЕ: оглавление отсекается гарантированно — по маркеру
    # «СОДЕРЖАНИЕ» и, как страховка, по строкам с точечными выносками.
    end_idx = n
    for i in range(start_idx, n):
        if normalize(lines[i]).upper() in STOP_MARKERS:
            end_idx = i
            break

    poems: list[dict] = []
    cur_title = None
    cur_section = None
    cur_body: list[str] = []
    cur_start_line = None
    prev_kind = "start"

    def flush(end_line):
        if cur_title is not None and (cur_body or cur_title.startswith("*")):
            poems.append({
                "title": cur_title,
                "section": cur_section,
                "body": "\n".join(cur_body).strip(),
                "start_line": cur_start_line,
                "end_line": end_line,
            })

    for idx in range(start_idx, end_idx):
        s = lines[idx].strip()
        line_no = idx + 1
        if not s:
            continue

        s_norm = normalize(s)

        if s_norm in sections_n:
            flush(line_no - 1)
            cur_section = s_norm
            cur_title, cur_body, cur_start_line = None, [], None
            prev_kind = "section"
            continue

        # ИСПРАВЛЕНИЕ: римская цифра внутри стихотворения — номер части, а не
        # раздел книги. Прежде она обнуляла cur_title, и весь текст части
        # молча выпадал из разбора (так терялись verfluchtes Fatum, Nicolas).
        if RE_ROMAN.fullmatch(s_norm):
            parent = cur_title
            flush(line_no - 1)
            base = re.sub(r"\s*\[[IVXLC]+\]$", "", parent) if parent else None
            cur_title = f"{base} [{s_norm}]" if base else f"[Часть {s_norm}]"
            cur_body, cur_start_line = [], line_no
            prev_kind = "title"
            continue

        if RE_PAGE_NUM.fullmatch(s):
            prev_kind = "page"
            continue

        if RE_TOC_LEADER.search(s):          # остаточная строка оглавления
            continue

        if RE_STANZA_SEP.fullmatch(s) and not RE_ASTERISK_TITLE.fullmatch(s):
            continue

        if RE_ASTERISK_TITLE.fullmatch(s):
            flush(line_no - 1)
            cur_title, cur_body, cur_start_line = "* * *", [], line_no
            prev_kind = "title"
            continue

        title_allowed = prev_kind in ("page", "section", "start")
        if file_format == "limbakh_2012":
            title_allowed = title_allowed or prev_kind == "title"

        if looks_like_title_line(s, sections_n) and title_allowed:
            flush(line_no - 1)
            cleaned = RE_NUMBERED_PREFIX.sub("", normalize(s))
            cur_title, cur_body, cur_start_line = (cleaned or s), [], line_no
            prev_kind = "title"
            continue

        if cur_title is None:
            prev_kind = "body"
            continue

        cur_body.append(s)
        prev_kind = "body"

    flush(end_idx)

    if not poems:
        body = [l.strip() for l in lines[start_idx:end_idx]
                if l.strip() and not RE_PAGE_NUM.fullmatch(l.strip())]
        if body:
            poems.append({"title": "[без заголовка]", "section": "",
                          "body": "\n".join(body), "start_line": start_idx + 1,
                          "end_line": end_idx})
    return poems


def detect_book_for_2012(text: str):
    lines = text.splitlines()
    found = []
    for i, raw in enumerate(lines, 1):
        s = normalize(raw)
        for name, year, period, anchor in BOOKS_IN_2012:
            if s == anchor:
                found.append((i, name, year, period))
                break
    seen, out = set(), []
    for ln, name, year, period in sorted(found):
        if name in seen:
            continue
        seen.add(name)
        out.append((ln, name, year, period))
    return out


def book_at_line(line_no: int, transitions):
    cur = (None, None, None)
    for ln, name, year, period in transitions:
        if line_no >= ln:
            cur = (name, year, period)
        else:
            break
    return cur


# --------------------------------------------------------------------------- #
# 6. Извлечение вкраплений                                                    #
# --------------------------------------------------------------------------- #


def find_inclusions(text: str, rejects: list | None = None):
    """Возвращает список (фраза, строка-контекст).

    Соседние латинские токены, разделённые только пробелом, дефисом или
    апострофом, склеиваются в одну единицу: «pied-à-terre», «Also sprach»,
    «de gustibus» — это одно вкрапление, а не два-три.

    ИСПРАВЛЕНИЕ: склейка работает и ЧЕРЕЗ ПЕРЕНОС СТРОКИ. Прежняя версия
    обрабатывала строки независимо, и связная иноязычная цитата, занимающая
    несколько стихов, дробилась: англоязычный эпиграф из Бродского в
    «Homo ludens» давал три единицы вместо одной. Теперь фрагмент, доходящий
    до конца строки без конечного знака препинания, продолжается фрагментом,
    открывающим следующую строку, если между ними нет русского текста.
    """
    out = []
    pending = None            # незакрытая цитата с предыдущей строки

    def flush():
        nonlocal pending
        if pending is not None:
            out.append((pending[0].strip(), pending[1].strip()))
            pending = None

    all_lines = text.splitlines()

    def neighbours_are_latin(i: int) -> bool:
        """Есть ли рядом преимущественно латинская строка."""
        for j in (i - 1, i + 1):
            if 0 <= j < len(all_lines):
                letters = [c for c in all_lines[j] if c.isalpha()]
                if letters and sum(
                    1 for c in letters if not RE_CYRILLIC.match(c)
                ) / len(letters) >= 0.8:
                    return True
        return False

    for line_i, line in enumerate(all_lines):
        if is_garbage_line(line):
            flush()
            continue

        lat_ctx = neighbours_are_latin(line_i)
        spans = []
        noise_spans = []          # позиции отбракованных OCR-артефактов
        for m in RE_TOKEN.finditer(line):
            ok, reason = looks_like_word(m.group(), line, m.start(), lat_ctx)
            if ok:
                spans.append((m.start(), m.end(), m.group()))
            else:
                if "артефакт" in reason:
                    noise_spans.append((m.start(), m.end()))
                if rejects is not None and reason:
                    rejects.append({"Токен": m.group(), "Причина отсева": reason,
                                    "Строка": line.strip()[:200]})
        if not spans:
            flush()
            continue

        def gap_text(a: int, b: int) -> str:
            """Текст между двумя принятыми токенами БЕЗ OCR-артефактов.

            ИСПРАВЛЕНИЕ: отбракованный артефакт распознавания, попавший внутрь
            связной иноязычной фразы, разрывал её на две записи. Классический
            случай — библиографическая сноска Лосева: в скане 1987 г. слово
            «Slavistik» разорвано переносом на «Slavist-» и «ikNo. 31», обломок
            «ikNo» отбракован, и половины сноски переставали склеиваться.
            По правилу 2 сноска — одна единица, поэтому артефакт при проверке
            зазора считается отсутствующим: он не вкрапление и не разделитель.
            """
            chunk = line[a:b]
            for ns, ne in noise_spans:
                if a <= ns and ne <= b:
                    chunk = chunk.replace(line[ns:ne], " ", 1)
            return chunk

        groups, i = [], 0
        while i < len(spans):
            j = i
            while j + 1 < len(spans):
                gap = gap_text(spans[j][1], spans[j + 1][0])
                if re.fullmatch(GAP_PATTERN, gap) or re.fullmatch(GAP_NUMERIC, gap):
                    j += 1
                else:
                    break
            groups.append((spans[i][0], spans[j][1],
                           line[spans[i][0]: spans[j][1]]))
            i = j + 1

        head, tail = groups[0], groups[-1]
        stripped = line.strip()
        # ИСПРАВЛЕНИЕ: строка, набранная целиком прописными, — заглавие
        # («HOMO LUDENS», «DE PROFUNDIS»). Со следующей строкой она не
        # склеивается, иначе заглавие срастается с эпиграфом.
        is_title_line = stripped.isupper() and len(stripped) >= 3
        starts_line = not RE_CYRILLIC.search(line[:head[0]])
        rest = line[tail[1]:].strip()
        open_end = (rest in ("", ",", "-", "\u2014", "\u2013")) and not is_title_line

        if pending is not None and starts_line:
            merged = pending[0].rstrip() + " " + head[2]
            ctx = pending[1] + " / " + stripped
            if len(groups) == 1 and open_end:
                pending = (merged, ctx)
                continue
            out.append((merged.strip(), ctx.strip()))
            pending = None
            groups = groups[1:]
        else:
            flush()

        for k, g in enumerate(groups):
            if k == len(groups) - 1 and open_end:
                pending = (g[2], stripped)
            else:
                out.append((g[2].strip(), stripped))

    flush()
    return out


# --------------------------------------------------------------------------- #
# 7. Главное                                                                  #
# --------------------------------------------------------------------------- #


def main():
    rows, summary, rejects = [], [], []

    for book in FILES:
        path = resolve(book["glob"])
        if path is None:
            print(f"  ! файл не найден по шаблону: {book['glob']}", file=sys.stderr)
            continue

        text = read_text(path)
        poems = parse_book(text, book["sections"], book["start_marker"],
                           book["format"])

        transitions = (detect_book_for_2012(text)
                       if book["format"] == "limbakh_2012" else [])

        n_with, n_incl = 0, 0
        for p in poems:
            # ИСПРАВЛЕНИЕ: служебная пометка части «[II]», которую добавляет сам
            # парсер, снимается перед выборкой — иначе скрипт «находил»
            # собственные метки как латинские вкрапления (I, V в ядре корпуса).
            clean_title = re.sub(r"\s*\[[IVXLC]+\]$", "", p["title"])
            full = (clean_title + "\n" + p["body"]).strip()
            inclusions = find_inclusions(full, rejects)

            if book["format"] == "limbakh_2012":
                sub_book, sub_year, sub_period = book_at_line(
                    p["start_line"] or 0, transitions)
                if sub_book is None:
                    sub_book, sub_year, sub_period = "(преамбула)", None, "—"
            else:
                sub_book, sub_year, sub_period = (
                    book["title"], book["year"], book["period"])

            if inclusions:
                n_with += 1
            for fragment, context in inclusions:
                n_incl += 1
                rows.append({
                    "Источник (файл)": book["title"],
                    "Год издания": book["year"],
                    "В основном корпусе": "да" if book["in_core_corpus"] else "нет",
                    "Книга": sub_book or "",
                    "Год книги": sub_year or "",
                    "Период": sub_period or "",
                    "Раздел книги": p["section"] or "",
                    "Заголовок стих-я": p["title"],
                    "Вкрапление": fragment,
                    "Графика": detect_script(fragment),
                    # ИСПРАВЛЕНИЕ (ред. 5.5): диакритика — наблюдаемый факт,
                    # орфография — подсказка верификатору, язык-источник
                    # проставляется вручную по контексту.
                    "Диакритика": diacritics(fragment),
                    "Совместимые орфографии (подсказка)": orthography_hint(fragment),
                    "Строка-контекст": context,
                    # Столбцы ручной верификации: заполняются человеком.
                    # Именно они связывают потокенную выгрузку с единицами
                    # анализа в § 2.2–2.4 статьи.
                    "Итоговое чтение (после верификации)": "",
                    "Единица анализа": "",
                    "Статус в итоговом счёте": "",
                    "Основание": "",
                    "Язык-источник (после верификации)": "",
                })

        summary.append({
            "Источник": book["title"],
            "Год издания": book["year"],
            "В основном корпусе": "да" if book["in_core_corpus"] else "нет",
            "Стихов разобрано": len(poems),
            "Стихов с вкраплениями": n_with,
            "Вкраплений всего": n_incl,
        })
        print(f"  • {book['title']}: {len(poems)} стих., {n_incl} вкр.")

    df = pd.DataFrame(rows)
    df_sum = pd.DataFrame(summary)
    df_rej = pd.DataFrame(rejects).drop_duplicates() if rejects else pd.DataFrame(
        columns=["Токен", "Причина отсева", "Строка"])

    if df.empty:
        print("Ничего не найдено — проверьте пути к файлам.", file=sys.stderr)
        return df, df_sum

    with pd.ExcelWriter(OUTPUT, engine="openpyxl") as xw:
        df.to_excel(xw, sheet_name="Вкрапления", index=False)
        df_sum.to_excel(xw, sheet_name="Сводка", index=False)
        df_rej.to_excel(xw, sheet_name="Отсев", index=False)

        from openpyxl.styles import Alignment
        for sheet, frame in [("Вкрапления", df), ("Сводка", df_sum),
                             ("Отсев", df_rej)]:
            ws = xw.sheets[sheet]
            for col_idx, col_name in enumerate(frame.columns, start=1):
                vals = frame[col_name].astype(str)
                max_len = max([len(str(col_name))] + [min(len(v), 80) for v in vals])
                ws.column_dimensions[
                    ws.cell(row=1, column=col_idx).column_letter
                ].width = min(max_len + 2, 60)
            for row in ws.iter_rows(min_row=2):
                for cell in row:
                    cell.alignment = Alignment(wrap_text=True, vertical="top")
            ws.freeze_panes = "A2"

    print(f"\nГотово: {len(df)} вкраплений → {OUTPUT}")
    return df, df_sum


if __name__ == "__main__":
    main()

# --------------------------------------------------------------------------- #
# ЖУРНАЛ ИСПРАВЛЕНИЙ (v1 → v2)                                                #
# --------------------------------------------------------------------------- #
# 1.  Аббревиатуры. Проверка «нет гласных → не слово» отбрасывала Ph, D, NB,
#     PS, DM — то есть ровно те вкрапления, которые для Лосева существенны.
#     Добавлен закрытый список ABBREVIATIONS. Сплошное разрешение всех токенов
#     длиной ≤ 3 (как предлагалось в отзыве) отвергнуто: оно впускает в
#     таблицу OCR-мусор и латинизированные обрывки кириллицы.
# 2.  is_garbage_line. Условие «cyr < 5 or lat < 5 → не мусор» логически
#     бессодержательно: оно истинно почти для любой строки. Заменено на два
#     содержательных признака: (а) смешение алфавитов внутри слова, (б) хаос
#     регистров в латинских токенах. Добавлен отсев строк оглавления.
# 3.  Кодировка. read_text() перебирает utf-8 / utf-8-sig / cp1251 / koi8-r;
#     UnicodeDecodeError больше не роняет прогон.
# 4.  Имена файлов. Точные имена заменены на glob-шаблоны.
# 5.  Токены «i» и «a». Принимаются только в латинском окружении: при OCR
#     кириллические «и» и «а» систематически читаются как латинские.
# 6.  Римские цифры. «I» перед английским словом («I read the Bible…») больше
#     не отбрасывается как номер части.
# 7.  Оглавление. Отсечение по СОДЕРЖАНИЕ + по точечным выноскам. В прежней
#     выгрузке заголовки De profundis, Homo Ludens, Poetry Makes Nothing
#     Happen, Natürlich учитывались дважды — как заглавие и как строка
#     оглавления; это завышало частоты.
# 8.  Нормализация заголовков. normalize() снимает кавычки, неразрывные
#     пробелы и NFKC-различия перед сверкой с sections.
# 9.  Склейка соседних токенов. Разрешён разрыв до 3 служебных символов, что
#     собирает «pied-à-terre», «Ph. D.», «table d’hôte» в одну единицу.
# 10. Список OCR_NOISE. Чтения, отвергнутые по сверке с изданием 2012 г.:
#     At, ikNo, uLa, Іисет.
# 11. Лист «Отсев». Каждый отброшенный токен фиксируется с причиной — отбор
#     становится воспроизводимым и проверяемым рецензентом.
# 12. from __future__ import annotations — совместимость с Python 3.7–3.8.
# 13. ОГРАНИЧЕНИЕ, которое скрипт не снимает: атрибуция вкрапления
#     конкретному стихотворению приблизительна для текстов с внутренними
#     подзаголовками (циклы «Выписки из русской поэзии», «Амфибронхитная
#     ночь»): подзаголовок вида «Батюшков» или «3. Ante lucem» не отвечает
#     признакам заголовка и наследует заглавие предыдущего текста. Столбец
#     «Заголовок стих-я» — ориентир для ручной сверки, а не готовый результат.
# 14. Убран столбец «Полный текст стих-я»: он дублировал весь корпус в каждой
#     строке таблицы и раздувал файл в десятки раз.
#
# --------------------------------------------------------------------------- #
# ЖУРНАЛ ИСПРАВЛЕНИЙ (v2 → v3, редакция 5.5)                                  #
# --------------------------------------------------------------------------- #
# 15. detect_script разделена на три функции. Прежняя версия склеивала
#     графический тип с языковой атрибуцией и выводила язык цепочкой if по
#     классам символов. На знаках, общих для нескольких орфографий, это давало
#     систематическую ошибку: «ü» входит и в немецкий, и во французский ряд,
#     но немецкая ветка проверялась первой, поэтому французские слова с «ü»
#     (capharnaüm, aiguë) получали помету «нем. диакритика». Теперь
#     detect_script возвращает только алфавит, diacritics() — перечень
#     встреченных знаков, orthography_hint() — МНОЖЕСТВО совместимых
#     орфографий. Знак письма не определяет языка, и скрипт больше не
#     делает вида, что определяет.
# 16. orthography_hint сигнализирует о знаках из несовместимых рядов внутри
#     одного токена: такое сочетание — почти верный признак OCR-артефакта.
# 17. detect_script опознаёт смешанную графику (латиница + кириллица внутри
#     одного токена) — тип В типологии § 2.2 статьи (`Shit-c`).
# 18. В выгрузку добавлены столбцы ручной верификации: «Итоговое чтение
#     (после верификации)», «Единица анализа», «Статус в итоговом счёте»,
#     «Основание», «Язык-источник (после верификации)». Скрипт работает
#     потокенно, аналитическая единица вкрапления с токеном не совпадает
#     (прерванная формула memento … mori — две строки выгрузки и одна
#     единица счёта). Эти столбцы связывают первичную выгрузку с таблицами
#     § 2.2–2.4 статьи, так что расхождение числа строк и числа единиц
#     перестаёт выглядеть ошибкой и становится документированным шагом.
# 19. Первичная выгрузка НЕ правится задним числом. Исправленные по изданию
#     2012 г. чтения (Ante → ANTE LUCEM) вносятся в отдельный столбец, а
#     машинный токен сохраняется как есть: иначе проверить процедуру
#     верификации по приложенному файлу невозможно.
#
# --------------------------------------------------------------------------- #
# ЖУРНАЛ ИСПРАВЛЕНИЙ (v3 → v4, редакция 5.6)                                  #
# --------------------------------------------------------------------------- #
# 20. Пути перестали быть абсолютными. UPLOADS и OUTPUT разрешаются по месту:
#     аргумент командной строки → переменная окружения LOSEV_CORPUS /
#     LOSEV_OUTPUT → ./uploads, ./corpus, ./texts рядом со скриптом → папка
#     скрипта. Прежние /mnt/user-data/... падали с FileNotFoundError у любого,
#     кто скачал архив и запустил скрипт у себя. Запуск:
#         python3 losev_extract.py [папка_с_текстами] [выходной_файл]
# 21. Шаблон имени контрольного свода 2012 г. расширен до списка. Прежний
#     единственный "*Losiev*.txt" не находил файл, названный stikhi_2012.txt
#     или losev_2012.txt, и книга молча выпадала из разбора — без сообщения
#     об ошибке, что хуже падения.
# 22. Короткая строка с диакритикой. Проверка is_garbage_line отбраковывала
#     строку короче трёх символов, если та не совпадала с r"[A-Za-z]{1,2}",
#     то есть с чистым ASCII. Отдельно стоящая строка «À», «Ô», «Ça» под
#     шаблон не подходила и терялась до проверки контекста. Класс расширен
#     до FOREIGN_LETTER — того же, которым выделяются сами токены.
