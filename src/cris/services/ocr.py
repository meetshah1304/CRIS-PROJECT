from __future__ import annotations

from pathlib import Path

from PIL import Image

from src.cris.config import get_settings
from src.cris.core.models import FIRDocument, OCRExtractionResult

try:
    import fitz
except ImportError:  # pragma: no cover
    fitz = None

try:
    import pypdfium2 as pdfium
except ImportError:  # pragma: no cover
    pdfium = None

try:
    import pytesseract
except ImportError:  # pragma: no cover
    pytesseract = None


def extract_text(document: FIRDocument) -> OCRExtractionResult:
    """
    OCR/text extraction strategy:

    1. Use PyMuPDF as the primary digital PDF text extractor.
    2. If a PDF yields no useful text, render pages with pypdfium2 and OCR them.
    3. For image files, OCR directly.
    4. If optional libraries are unavailable, return a deterministic fallback sample.
    """
    path = Path(document.source_path)
    settings = get_settings()

    if pytesseract is not None and settings.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd

    if document.file_type == "pdf":
        text, page_count = _extract_pdf_text_pymupdf(path)
        if _is_useful_text(text):
            return OCRExtractionResult(
                raw_text=text,
                confidence=0.94,
                page_count=page_count,
                extraction_method="pymupdf_text",
                extraction_notes=["Digital PDF text extracted with PyMuPDF"],
            )

        rendered_text, rendered_pages = _extract_pdf_text_via_rendered_ocr(path)
        if _is_useful_text(rendered_text):
            return OCRExtractionResult(
                raw_text=rendered_text,
                confidence=0.7,
                page_count=rendered_pages,
                extraction_method="pypdfium2_render_plus_tesseract",
                extraction_notes=["Rendered PDF pages with pypdfium2 and OCRed with Tesseract"],
            )

    if document.file_type == "image":
        image_text = _extract_image_text(path)
        if _is_useful_text(image_text):
            return OCRExtractionResult(
                raw_text=image_text,
                confidence=0.68,
                page_count=1,
                extraction_method="image_tesseract",
                extraction_notes=["OCRed uploaded image with Tesseract"],
            )

    return OCRExtractionResult(
        raw_text=_fallback_sample_text(path),
        confidence=0.42,
        page_count=1 if document.file_type == "image" else None,
        extraction_method="fallback_sample",
        extraction_notes=["Used fallback sample because configured extraction could not recover usable text"],
    )


def _extract_pdf_text_pymupdf(path: Path) -> tuple[str, int | None]:
    if fitz is None:
        return "", None

    text_chunks: list[str] = []
    try:
        with fitz.open(path) as pdf:
            page_count = len(pdf)
            for page in pdf:
                page_text = page.get_text("text") or ""
                if page_text.strip():
                    text_chunks.append(page_text.strip())
    except Exception:
        return "", None
    return "\n".join(text_chunks).strip(), page_count


def _extract_pdf_text_via_rendered_ocr(path: Path) -> tuple[str, int | None]:
    if pdfium is None or pytesseract is None:
        return "", None

    text_chunks: list[str] = []
    try:
        pdf = pdfium.PdfDocument(str(path))
        page_count = min(len(pdf), 8)
        for page_index in range(page_count):
            page = pdf[page_index]
            bitmap = page.render(scale=2.0)
            pil_image = bitmap.to_pil()
            text = pytesseract.image_to_string(pil_image)
            if text.strip():
                text_chunks.append(text.strip())
    except Exception:
        return "", None
    return "\n".join(text_chunks).strip(), page_count


def _extract_image_text(path: Path) -> str:
    if pytesseract is None:
        return ""

    try:
        with Image.open(path) as image:
            return pytesseract.image_to_string(image).strip()
    except Exception:
        return ""


def _is_useful_text(text: str) -> bool:
    cleaned = " ".join(text.split())
    return len(cleaned) >= 40 and any(char.isalpha() for char in cleaned)


def _fallback_sample_text(path: Path) -> str:
    return (
        f"FIR No {path.stem} registered at Sample Police Station. "
        f"Offence sections 420, 406. Incident location Ahmedabad. "
        f"Accused John Doe. Victim Jane Roe."
    )
