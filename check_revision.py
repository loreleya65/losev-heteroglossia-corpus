# -*- coding: utf-8 -*-
# РЕДАКЦИЯ 5.8 — 30.08.2026. Проверить экземпляр: python3 check_revision.py
"""
check_revision.py — проверка того, какая редакция файлов лежит перед вами.

Зачем нужен
-----------
Аудит трижды подряд сообщал, что правки «не попали в файлы», описывая при этом
состояние, которого в выданных файлах нет. Причина такого расхождения обычно
одна: проверяется не тот экземпляр (старое вложение, копия из «Загрузок»,
кэш просмотрщика). Спорить об этом бессмысленно — проще проверить.

Скрипт берёт файлы из указанной папки и печатает по каждому пункту чек-листа
ЕСТЬ / НЕТ. Если хотя бы один пункт «НЕТ» — перед вами старая копия.

Запуск:
    python3 check_revision.py                 # проверить текущую папку
    python3 check_revision.py путь/к/папке    # проверить конкретную папку

Зависимости: только стандартная библиотека. Проверка .docx делается через
распаковку zip, никаких сторонних пакетов не требуется.

СЛУЖЕБНЫЙ ФАЙЛ. Это авто-тест редакции, а не часть исследовательского
инструментария. В комплект материалов, подаваемый в журнал или выкладываемый
в репозиторий статьи, он не входит: приложением к статье являются только
losev_extract.py (процедура 1) и losev_oov.py (процедура 2). Место этого
файла — служебная папка tests/ рядом с ними.
"""

from __future__ import annotations

import html
import re
import sys
import zipfile
from pathlib import Path

REVISION = "5.8"                      # см. шапку каждого файла
# Обязательные файлы комплекта: без них проверка не имеет смысла.
FILES = {
    "article_md": "Лосев_статья_ИСПРАВЛЕННАЯ.md",
    "article_docx": "Лосев_статья_ИСПРАВЛЕННАЯ.docx",
    "log58": "Журнал_правок_ред_5.8.md",
    "extract": "losev_extract.py",
    "oov": "losev_oov.py",
}

# ИСПРАВЛЕНИЕ (ред. 5.6): вспомогательные файлы вынесены отдельно. Прежде их
# отсутствие давало «НЕТ» по шести пунктам, и чек-лист сообщал «это НЕ
# актуальная редакция», хотя редакция актуальна, — просто рабочие материалы в
# комплект для журнала не входят. Теперь относящиеся к ним пункты добавляются
# только если файлы лежат рядом, а их отсутствие отмечается справкой.
OPTIONAL_FILES = {
    "lists": "Лосев_списки_слов_ИСПРАВЛЕННЫЕ.md",
    "log": "Разбор_замечаний_и_журнал_правок.md",
}


def read(path: Path) -> str:
    if not path.exists():
        return ""
    if path.suffix == ".docx":
        # ИСПРАВЛЕНИЕ (ред. 5.8). Прежде все теги удалялись без замены, и текст
        # соседних абзацев склеивался: «…метаязык самоописания.Ключевые слова:».
        # Поиск подстроки, попадающей на такой стык, давал ложное «НЕТ».
        #
        # Замена ВСЕХ тегов на пробел — решение неверное: Word разбивает абзац
        # на run'ы по начертанию, и фраза «42 единицы вкрапления; сверх того»
        # разорвана полужирным. Пробел на месте </w:r><w:r> разрывал бы и её,
        # ломая проверки, которые сейчас проходят.
        #
        # Правильная граница — конец абзаца, разрыв строки и табуляция; внутри
        # абзаца run'ы склеиваются встык, как это делает и сам Word.
        try:
            with zipfile.ZipFile(path) as z:
                xml = z.read("word/document.xml").decode("utf-8", "replace")
            xml = re.sub(r"</w:p>|<w:br\s*/>|<w:tab\s*/>", "\n", xml)
            text = re.sub(r"<[^>]+>", "", xml)
            return html.unescape(text)
        except Exception:
            return ""
    for enc in ("utf-8", "utf-8-sig", "cp1251"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def main(folder: str = ".") -> int:
    base = Path(folder)
    src = {k: read(base / v) for k, v in FILES.items()}
    opt = {k: read(base / v) for k, v in OPTIONAL_FILES.items()}
    src.update(opt)

    missing = [FILES[k] for k in FILES if not src.get(k)]
    if missing:
        print("Обязательные файлы не найдены или пусты:")
        for m in missing:
            print("   •", m)
        print()
    skipped = [OPTIONAL_FILES[k] for k in OPTIONAL_FILES if not opt.get(k)]

    lists, article, docx = src["lists"], src["article_md"], src["article_docx"]
    extract, oov, log = src["extract"], src["oov"], src["log"]
    log58 = src["log58"]

    nums = [int(m.group(1)) for m in re.finditer(r"^\| (\d+) \| \*\*", lists, re.M)]
    dupes = sorted({n for n in nums if nums.count(n) > 1})

    # --- таблица онимов: заголовок против содержимого
    onym_block, onym_header, onym_rows = "", -1, 0
    m = re.search(r"## 4\. Онимы[^\n]*?\((\d+) позиц", lists)
    if m:
        onym_header = int(m.group(1))
        tail = lists[m.start():]
        end = tail.find("## 5.")
        onym_block = tail[:end if end > 0 else len(tail)]
        onym_rows = sum(1 for l in onym_block.split("\n")
                        if l.startswith("| ") and not l.startswith("| Слово"))

    # --- внутритекстовые ссылки против списка литературы
    dangling, uncited = [], []
    if "# ЛИТЕРАТУРА" in article:
        body, lit = article.split("# ЛИТЕРАТУРА", 1)
        lit = lit.split("# REFERENCES", 1)[0]     # латинский список считается отдельно
        known = {int(x.group(1)) for x in re.finditer(r"^(\d+)\. ", lit, re.M)}
        cited = set()
        for ref in re.finditer(r"\[(\d+(?:[;,]\s*\d+)*)\]", body):
            for n in re.findall(r"\d+", ref.group(1)):
                cited.add(int(n))
                if int(n) not in known:
                    dangling.append(int(n))
        # требование ВАК/RSCI: каждая позиция списка хотя бы раз цитируется
        uncited = sorted(known - cited)

    # --- русский список и латинский References должны совпадать по объёму
    ru_count = en_count = 0
    if "# ЛИТЕРАТУРА" in article:
        tail = article.split("# ЛИТЕРАТУРА", 1)[1]
        ru_part = tail.split("# REFERENCES", 1)[0]
        ru_count = len(re.findall(r"^\d+\. ", ru_part, re.M))
        if "# REFERENCES" in tail:
            en_count = len(re.findall(r"^\d+\. ", tail.split("# REFERENCES", 1)[1], re.M))

    checks = []
    if lists:
        checks += [
            ("Списки: заголовок § 1 разводит латиницу и смешанную графику",
             "36 в чистой латинице" in lists),
            ("Списки: подраздел § 1.3 «Смешанная графика» существует",
             "### 1.3." in lists),
            ("Списки: сквозная нумерация без дубликатов",
             bool(nums) and not dupes),
            ("Списки: таблица онимов совпадает с заголовком § 4",
             onym_header == onym_rows and onym_rows > 0),
            ("Списки: «Квисисана» в таблице онимов", "Квисисана" in onym_block),
            ("Списки: нет устаревших ссылок вида «§ 2, № NN»",
             "§ 2, №" not in lists),
        ]
    if log:
        checks += [("Журнал правок: разделы H–O",
                    all(f"# {x}." in log for x in "HIJKLMNO"))]

    checks += [
        ("Статья (.md): каламбур описан как наращение корня",
         "наращивает корень" in article and "меняет одну букву" not in article),
        ("Статья (.docx): то же самое",
         "наращивает корень" in docx),
        ("Статья (.md): персонаж «назвавшись монахом»",
         "назвавшись монахом" in article),
        ("Статья (.docx): то же самое",
         "назвавшись монахом" in docx),
        ("Статья: страницы Скворцова (С. 124–130)",
         "124" in article and "130" in article),
        ("Статья: отсылки на позиции 19–21 в тексте",
         "[19; 20]" in article and "[21]" in article),
        ("Статья: правила 3-бис и 3-тер введены",
         "3-бис" in article and "3-тер" in article),
        ("Статья: итог 42 единицы",
         "42 единицы вкрапления" in article),
        ("losev_oov.py: порог длины поднят до 12",
         "len(word) >= 12" in oov),
        ("losev_oov.py: служебные разделы режутся по второй половине файла",
         "floor = len(lines) // 2" in oov),
        ("losev_extract.py: latin_context для изолированного «I»",
         extract.count("latin_context") >= 3),
        ("losev_extract.py: OCR-артефакт прозрачен внутри фразы",
         "def gap_text" in extract),
        ("losev_extract.py: зазор с числом (GAP_NUMERIC)",
         "GAP_NUMERIC" in extract),
        ("losev_extract.py: гомоглифы и знаки ударения",
         "HOMOGLYPHS" in extract and "STRESS_VOWELS" in extract),
        ("Статья: ссылки на Леонтьева [8] и Листрову-Правду [9]",
         "Леонтьева [8]" in article and "Листровой-Правды [9]" in article),
        ("Статья: все внутритекстовые ссылки существуют в списке литературы",
         not dangling),
        ("Статья: каждая позиция литературы процитирована в тексте",
         not uncited),
        ("Статья: англоязычные Abstract и Keywords",
         "**Abstract**" in article and "**Keywords:**" in article),
        ("Статья: References в латинице совпадает по числу позиций",
         ru_count > 0 and ru_count == en_count),

        # --- редакция 5.5: правки по замечаниям рецензента ---
        ("Ред. 5.5 — статья: заполнена дата обращения в REFERENCES, поз. 20",
         "__.__.20__" not in article and "accessed 27.08.2026" in article),
        ("Ред. 5.5 — статья: снята оговорка о недоступности pymorphy3",
         "не располагала" not in article and "не воспроизводился" not in article),
        ("Ред. 5.5 — статья (.docx): то же самое",
         bool(docx) and "не располагала" not in docx),
        ("Ред. 5.5 — статья: § 2.1 объясняет потокенную выгрузку memento/mori",
         "Примечание о соотношении первичной выгрузки" in article
         and "45 потокенных записей" in article),
        ("Ред. 5.5 — статья (.docx): то же самое",
         "Примечание о соотношении первичной выгрузки" in docx),
        ("Ред. 5.5 — статья: § 1.5 о первичной выгрузке без правки задним числом",
         "без ретроспективной правки" in article),
        ("Ред. 5.5 — статья: § 4.1 содержит оговорку о полноте",
         "Оговорка к пункту 1" in article),
        ("Ред. 5.5 — статья: приложение не ссылается на невоспроизведённый прогон",
         "проверенный, но не гарантированно исчерпывающий" in article
         and "повторным прогоном не снимается" in article),
        ("Ред. 5.5 — losev_extract.py: графика и язык-источник разведены",
         "def orthography_hint" in extract
         and 'return "латиница (нем. диакритика)"' not in extract),
        ("Ред. 5.5 — losev_extract.py: столбцы ручной верификации в выгрузке",
         '"Единица анализа"' in extract
         and '"Итоговое чтение (после верификации)"' in extract),
        ("Ред. 5.5 — losev_oov.py: отсев короткого OCR-мусора на кириллице",
         "if len(low) <= 2:" in oov),
        ("Ред. 5.5 — losev_oov.py: пороги не задевают нормативный материал",
         "длинношеее" in oov and 'word.split("-")' in oov),
        # --- редакция 5.6 ---
        ("Ред. 5.6 — статья: § 2.1 раскрывает переход 45 → 37 по операциям",
         "45 − 8 = 37" in article and "36 в оригинальной латинице" in article),
        ("Ред. 5.6 — статья (.docx): то же самое",
         "45 − 8 = 37" in docx),
        ("Ред. 5.6 — статья: приложение сверено по немецким заглавиям",
         "8 французских и 6 немецких" in article),
        ("Ред. 5.6 — статья (.docx): то же самое",
         "8 французских и 6 немецких" in docx),
        ("Ред. 5.6 — losev_oov.py: мёртвая проверка длины удалена",
         "if len(word) < 3:\n        return False" not in oov),
        ("Ред. 5.6 — losev_oov.py: убраны неиспользуемые параметры",
         "def looks_like_ocr_noise(word: str) -> bool:" in oov
         and "def bucket(word: str) -> str:" in oov),
        ("Ред. 5.6 — скрипты: пути разрешаются по месту, а не /mnt/user-data",
         "BASE_DIR = Path(__file__).resolve().parent" in extract
         and "BASE_DIR = Path(__file__).resolve().parent" in oov),
        ("Ред. 5.6 — losev_extract.py: шаблон файла 2012 г. не единственный",
         '"*[Ll]os*2012*.txt"' in extract),
        ("Ред. 5.6 — losev_extract.py: короткая строка с диакритикой не теряется",
         "RE_SHORT_FOREIGN" in extract),
        # --- редакция 5.7 ---
        ("Ред. 5.7 — статья: титульный аппарат (УДК, автор, ORCID)",
         "УДК" in article and "ORCID" in article),
        ("Ред. 5.7 — статья (.docx): то же самое",
         "УДК" in docx and "ORCID" in docx),
        ("Ред. 5.7 — статья: блок «Для цитирования» / «For citation»",
         "Для цитирования" in article and "For citation" in article),
        ("Ред. 5.7 — статья (.docx): то же самое",
         "Для цитирования" in docx and "For citation" in docx),
        ("Ред. 5.7 — статья: правило 3 действует независимо от графики",
         "независимо от графики" in article),
        ("Ред. 5.7 — статья: § 2.5 учитывает латинографические онимы",
         "пятнадцать онимов" in article and "15 онимов" in article),
        ("Ред. 5.7 — статья (.docx): то же самое",
         "пятнадцать онимов" in docx),
        ("Ред. 5.7 — статья: § 2.3 оговаривает округление долей",
         "100,1 %" in article),
        ("Ред. 5.7 — статья: единица счёта корпуса уточнена в аннотации",
         "25 500 кириллических словоупотреблений" in article
         and "25,500 Cyrillic word tokens" in article),
        ("Ред. 5.8 — журнал правок редакции присутствует",
         bool(log58)),

        # --- редакция 5.8 ---
        ("Ред. 5.8 — статья: три гибридных окказионализма названы поимённо",
         all(w in article for w in ("доллареску", "ньюхемпширский", "прирейнском"))),
        ("Ред. 5.8 — статья (.docx): то же самое",
         all(w in docx for w in ("доллареску", "ньюхемпширский", "прирейнском"))),
        ("Ред. 5.8 — статья: англоязычный блок автора перед Abstract",
         "Author’s Name in English" in article),
        ("Ред. 5.8 — статья (.docx): то же самое",
         "Author’s Name in English" in docx),
        ("Ред. 5.8 — статья: отсылка [18] при первом упоминании монографии",
         "Modern Russian Literature» (1984) [18]" in article),
        ("Ред. 5.8 — статья (.docx): то же самое",
         "Modern Russian Literature» (1984) [18]" in docx),
        ("Ред. 5.8 — скрипты: шапка редакции синхронизирована",
         f"РЕДАКЦИЯ {REVISION}" in extract and f"РЕДАКЦИЯ {REVISION}" in oov),
        ("Ред. 5.8 — авто-тест: текст .docx не склеивается на границе абзацев",
         "Ключевые слова" in docx and "самоописания.Ключевые" not in docx),
    ]

    width = max(len(n) for n, _ in checks)
    ok = 0
    print(f"Проверка редакции {REVISION} — папка: {base.resolve()}\n")
    for name, passed in checks:
        print(f"  {'ЕСТЬ' if passed else 'НЕТ '}  {name:<{width}}")
        ok += passed

    print(f"\nПройдено {ok} из {len(checks)}.")
    if skipped:
        print("  i вспомогательные материалы не приложены, их пункты пропущены:")
        for s in skipped:
            print("     •", s)
    if dupes:
        print(f"  ! дублирующиеся номера строк в списках: {dupes}")
    if lists and onym_header != onym_rows:
        print(f"  ! § 4 списков: в заголовке {onym_header}, в таблице {onym_rows}")
    if dangling:
        print(f"  ! ссылки на несуществующие позиции литературы: {sorted(set(dangling))}")
    if uncited:
        print(f"  ! позиции литературы без ссылки в тексте: {uncited}")
    if ru_count != en_count:
        print(f"  ! ЛИТЕРАТУРА: {ru_count} позиций, REFERENCES: {en_count}")
    # ------------------------------------------------------------------ #
    # Предупреждения перед подачей. Это не признак устаревшей редакции:   #
    # редакция может быть актуальной, а статья — ещё не готовой к отправке.
    # ------------------------------------------------------------------ #
    warn = []
    ph_md = article.count("\u27e8")
    ph_docx = docx.count("\u27e8")
    if ph_md or ph_docx:
        warn.append(f"незаполненные поля \u27e8…\u27e9: в .md {ph_md}, в .docx {ph_docx} "
                    f"(УДК, ФИО, организация, ORCID, e-mail, выходные данные)")
    if ("гибридных окказионализма" in article
            and not all(w in article for w in ("доллареску", "ньюхемпширский",
                                               "прирейнском"))):
        warn.append("три гибридных окказионализма упомянуты в счёте, но нигде "
                    "не названы поимённо — рецензент спросит, какие именно")
    if warn:
        print("\nПеред подачей в журнал:")
        for w in warn:
            print("   !", w)

    if ok == len(checks):
        print("\nЭто актуальная редакция. Все пункты чек-листа на месте.")
        return 0
    print("Это НЕ актуальная редакция: часть правок отсутствует.")
    print("Возьмите файлы из последнего сообщения, а не из более раннего вложения.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
