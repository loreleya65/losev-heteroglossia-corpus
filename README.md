# The Poetics of Foreign-Language Inclusion in Lev Loseff’s Lyric Verse: A Corpus Study of Heteroglossia in the Early Émigré Text

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This repository contains the computational pipeline, extraction scripts, and verified dataset supporting the corpus-based study of heteroglossia and multilingual poetic devices in the early émigré poetry of **Lev Loseff (1937–2009)**.

---

## 📖 Research Overview

The study presents an exhaustive survey of foreign-language inclusions across Loseff's two foundational émigré poetry collections published by *Hermitage*:
* **«Чудесный десант»** (*The Miraculous Landing*, Tenafly, 1985)
* **«Тайный советник»** (*The Privy Councillor*, Tenafly, 1987)

**Core Corpus Volume:** 169 verse texts (~25,500 Cyrillic word tokens).  
**Control Source:** Posthumous collected edition *«Стихи»* (St. Petersburg: Ivan Limbakh Publishing House, 2012).

### Key Quantitative Findings
* **42 analytical units of inclusion** identified across 6 source languages.
* **Graphic Strategy:** 85.7% retain original Latin script; only 11.9% use Cyrillic adaptation.
* **Source Languages:** Latin dominates (31.0%), German (19.0%), French (19.0%), English (16.7%).

---

## 🛠 Methodology & Two-Step Pipeline

1. **Procedure 1 (`losev_extract.py`):** Regex extraction for Latin, Greek, and Hebrew scripts, handling multi-token units and OCR artifact filtering.
2. **Procedure 2 (`losev_oov.py`):** Cyrillic Out-of-Vocabulary (OOV) discovery using `pymorphy3` (`is_known == False`), followed by heuristic bucketing.
3. **Manual Verification:** Step-by-step collation of all candidates with the 2012 collected edition.

---

## 📂 Repository Structure

```text
.
├── losev_extract.py              # Procedure 1: Latin script extractor
├── losev_oov.py                  # Procedure 2: Cyrillic OOV extractor
├── losev_foreign_inclusions.xlsx # Master dataset with verification steps
├── losev_oov_candidates.xlsx     # Ranked Cyrillic OOV machine output
├── requirements.txt              # Python dependencies
└── README.md                     # Documentation
