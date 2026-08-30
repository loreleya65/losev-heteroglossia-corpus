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

Due to morphological analyzer architecture (`pymorphy3` uses OpenCorpora with Cyrillic-only lexicons and assigns the `LATN` tag without dictionary lookup), the extraction is separated into two independent procedures:1. **Procedure 1 (`losev_extract.py`):** High-precision regex extraction for Latin/Greek/Hebrew scripts, handling inter-token punctuation gaps, multi-line spanning, OCR artifact filtering, and script-diacritic mapping.
2. **Procedure 2 (`losev_oov.py`):** Cyrillic Out-of-Vocabulary (OOV) discovery using `pymorphy3` (`is_known == False` across all parses), heuristic bucketing, and backmatter/frontmatter filtering.
3. **Phonotactic Sieve:** Additional dictionary-independent completeness check targeting non-native consonant clusters and vowel hiatuses.

---

## 📂 Repository Structure

```text
.
├── losev_extract.py              # Procedure 1: Latin script extractor
├── losev_oov.py                  # Procedure 2: Cyrillic OOV candidate extractor
├── losev_foreign_inclusions.xlsx # Master dataset with verification steps
├── losev_oov_candidates.xlsx     # Ranked Cyrillic OOV machine output (577 candidates)
├── requirements.txt              # Python dependencies
├── corpus/                       # Text files directory (place .txt corpus here)
│   ├── desant_1985.txt
│   ├── tainii_sovetnik.txt
│   └── stikhi_2012.txt
└── README.md                     # Documentation
git clone https://github.com/<your-username>/losev-heteroglossia-corpus.git
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -r requirements.txt
# Procedure 1: Extract non-Cyrillic tokens
python3 losev_extract.py ./corpus ./losev_foreign_inclusions.xlsx

# Procedure 2: Extract Cyrillic OOV candidates
python3 losev_oov.py ./corpus ./losev_oov_candidates.xlsx
@article{loseff_heteroglossia_2026,
  author    = {Author, Name},
  title     = {The Poetics of Foreign-Language Inclusion in Lev Loseff’s Lyric Verse: A Corpus Study of Heteroglossia in the Early {\'{E}}migr{\'{e}} Text},
  journal   = {Journal Title},
  year      = {2026},
  volume    = {00},
  number    = {0},
  pages     = {000--000},
  doi       = {10.00000/0000}
}
@dataset{loseff_corpus_data_2026,
  author    = {Author, Name},
  title     = {Replication Package: Poetics of Foreign-Language Inclusion in Lev Loseff’s Lyric Verse (Extraction Pipeline and Master Dataset)},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.XXXXXXX}
}
cd losev-heteroglossia-corpus
