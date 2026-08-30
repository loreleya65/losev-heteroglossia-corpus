# The Poetics of Foreign-Language Inclusion in Lev Loseff’s Lyric Verse: A Corpus Study of Heteroglossia in the Early Émigré Text

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)

This repository contains the computational pipeline, extraction scripts, and verified dataset supporting the corpus-based study of heteroglossia and multilingual poetic devices in the early émigré poetry of **Lev Loseff (1937–2009)**.

---

## 📖 Research Overview

The study presents an exhaustive survey of foreign-language inclusions across Loseff's two foundational émigré poetry collections published by *Hermitage*:
* **«Чудесный десант»** (*The Miraculous Landing*, Tenafly, 1985)
* **«Тайный советник»** (*The Privy Councillor*, Tenafly, 1987)

**Core Corpus Volume:** 169 verse texts (~25,500 Cyrillic word tokens).  
**Control Source:** Posthumous collected edition *«Стихи»* (St. Petersburg: Ivan Limbakh Publishing House, 2012), used strictly for manual OCR verification and doubtful reading collation.

### Key Quantitative Findings
* **42 analytical units of inclusion** identified across 6 source languages.
* **Graphic Strategy:** 85.7% retain original Latin script (visual heteroglossia); only 11.9% use Cyrillic adaptation.
* **Source Languages:** Latin dominates (31.0%), followed by German and French (19.0% each). English ranks only 4th (16.7%), refuting the assumption of rapid lexical Americanization.

---

## 🛠 Methodology & Two-Step Pipeline

Due to morphological analyzer architecture (`pymorphy3` uses OpenCorpora with Cyrillic-only lexicons and assigns the `LATN` tag without dictionary lookup), the extraction is separated into two independent procedures:
