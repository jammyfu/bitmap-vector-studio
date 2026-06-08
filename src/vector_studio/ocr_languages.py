from __future__ import annotations

import logging
import re
import subprocess
from typing import Any

logger = logging.getLogger(__name__)

OCR_LANGUAGE_CONFIG: dict[str, dict[str, Any]] = {
    "eng": {
        "name": "English",
        "tesseract_code": "eng",
        "font_family": "Noto Sans, Arial, sans-serif",
        "writing_mode": "horizontal",
        "preprocess": "standard",
        "direction": "ltr",
    },
    "chi_sim": {
        "name": "简体中文",
        "tesseract_code": "chi_sim",
        "font_family": "Noto Sans CJK SC, SimHei, Microsoft YaHei, sans-serif",
        "writing_mode": "horizontal",
        "preprocess": "sharpen",
        "direction": "ltr",
    },
    "chi_tra": {
        "name": "繁體中文",
        "tesseract_code": "chi_tra",
        "font_family": "Noto Sans CJK TC, Microsoft JhengHei, sans-serif",
        "writing_mode": "horizontal",
        "preprocess": "sharpen",
        "direction": "ltr",
    },
    "jpn": {
        "name": "日本語",
        "tesseract_code": "jpn",
        "font_family": "Noto Sans JP, Hiragino Sans, Yu Gothic, sans-serif",
        "writing_mode": "horizontal",
        "preprocess": "sharpen",
        "direction": "ltr",
    },
    "kor": {
        "name": "한국어",
        "tesseract_code": "kor",
        "font_family": "Noto Sans KR, Malgun Gothic, sans-serif",
        "writing_mode": "horizontal",
        "preprocess": "sharpen",
        "direction": "ltr",
    },
    "ara": {
        "name": "العربية",
        "tesseract_code": "ara",
        "font_family": "Noto Sans Arabic, Arial, sans-serif",
        "writing_mode": "horizontal",
        "preprocess": "standard",
        "direction": "rtl",
    },
    "rus": {
        "name": "Русский",
        "tesseract_code": "rus",
        "font_family": "Noto Sans, DejaVu Sans, sans-serif",
        "writing_mode": "horizontal",
        "preprocess": "standard",
        "direction": "ltr",
    },
    "deu": {
        "name": "Deutsch",
        "tesseract_code": "deu",
        "font_family": "Noto Sans, DejaVu Sans, sans-serif",
        "writing_mode": "horizontal",
        "preprocess": "standard",
        "direction": "ltr",
    },
    "fra": {
        "name": "Français",
        "tesseract_code": "fra",
        "font_family": "Noto Sans, DejaVu Sans, sans-serif",
        "writing_mode": "horizontal",
        "preprocess": "standard",
        "direction": "ltr",
    },
    "spa": {
        "name": "Español",
        "tesseract_code": "spa",
        "font_family": "Noto Sans, DejaVu Sans, sans-serif",
        "writing_mode": "horizontal",
        "preprocess": "standard",
        "direction": "ltr",
    },
}

# Map short language codes to tesseract codes
_LANG_CODE_MAP: dict[str, str] = {
    "zh": "chi_sim",
    "ja": "jpn",
    "ko": "kor",
    "ar": "ara",
    "ru": "rus",
    "en": "eng",
    "de": "deu",
    "fr": "fra",
    "es": "spa",
    "zh_tw": "chi_tra",
    "zh_cn": "chi_sim",
}

# Reverse mapping for convenience
_TESSERACT_TO_SHORT: dict[str, str] = {
    "chi_sim": "zh",
    "chi_tra": "zh_tw",
    "jpn": "ja",
    "kor": "ko",
    "ara": "ar",
    "rus": "ru",
    "eng": "en",
    "deu": "de",
    "fra": "fr",
    "spa": "es",
}


def get_tesseract_languages() -> list[str]:
    """Return the list of Tesseract language packs installed on the system.

    Runs ``tesseract --list-langs`` and parses the output. If Tesseract is not
    installed or the command fails, an empty list is returned.
    """
    try:
        result = subprocess.run(
            ["tesseract", "--list-langs"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if result.returncode != 0:
            logger.debug("tesseract --list-langs failed: %s", result.stderr)
            return []
        lines = result.stdout.strip().splitlines()
        # First line is usually a header like "List of available languages ..."
        langs: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.lower().startswith("list"):
                continue
            langs.append(stripped)
        return langs
    except FileNotFoundError:
        logger.debug("tesseract executable not found")
        return []
    except subprocess.TimeoutExpired:
        logger.debug("tesseract --list-langs timed out")
        return []
    except Exception as exc:  # noqa: BLE001
        logger.debug("Failed to list tesseract languages: %s", exc)
        return []


def check_language_available(lang: str) -> bool:
    """Check whether a given language pack is installed for Tesseract.

    Args:
        lang: Language code (e.g. ``"eng"``, ``"chi_sim"``).

    Returns:
        ``True`` if the language pack appears in ``tesseract --list-langs``.
    """
    available = get_tesseract_languages()
    return lang in available


def suggest_language_pack(lang: str) -> str:
    """Return a human-readable installation hint for a missing language pack.

    Args:
        lang: Tesseract language code (e.g. ``"chi_sim"``).

    Returns:
        Installation command or guidance string.
    """
    config = OCR_LANGUAGE_CONFIG.get(lang)
    name = config["name"] if config else lang

    hints: list[str] = [
        f"Language pack '{lang}' ({name}) is not installed.",
    ]

    # Ubuntu / Debian
    hints.append(f"  Ubuntu/Debian: sudo apt install tesseract-ocr-{lang}")
    # macOS
    hints.append(f"  macOS (Homebrew): brew install tesseract-lang")
    # Windows
    hints.append(
        f"  Windows: Download {lang}.traineddata from "
        "https://github.com/tesseract-ocr/tessdata and place it in "
        "your Tesseract tessdata directory."
    )
    # Arch
    hints.append(f"  Arch Linux: sudo pacman -S tesseract-data-{lang}")

    return "\n".join(hints)


def normalize_language_code(lang: str | None) -> str:
    """Normalize a short or full language code to a Tesseract language code.

    Args:
        lang: Short code (e.g. ``"zh"``) or Tesseract code (e.g. ``"chi_sim"``).

    Returns:
        Tesseract language code, or ``"eng"`` as the default.
    """
    if lang is None or lang == "":
        return "eng"
    lang = lang.lower().strip()
    if lang in OCR_LANGUAGE_CONFIG:
        return lang
    mapped = _LANG_CODE_MAP.get(lang)
    if mapped:
        return mapped
    return lang


def get_language_config(lang: str) -> dict[str, Any]:
    """Retrieve the full configuration dictionary for a language.

    Args:
        lang: Language code (short or Tesseract).

    Returns:
        Configuration dict. Falls back to the ``eng`` config if the language
        is not explicitly configured.
    """
    code = normalize_language_code(lang)
    return OCR_LANGUAGE_CONFIG.get(code, OCR_LANGUAGE_CONFIG["eng"].copy())
