# invoice_system/extractor.py
import json, re, os
from pathlib import Path

import fitz  # PyMuPDF
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import easyocr
from dateutil import parser as dateparser

try:
    from langchain_zunno import create_zunno_llm
except Exception:
    create_zunno_llm = None  # allow running without LLM

# ---------- helpers ----------
def normalize_date(s):
    if not s:
        return None
    try:
        return dateparser.parse(str(s), fuzzy=True, dayfirst=True).strftime("%d-%m-%Y")
    except Exception:
        return None

def clean_text(s: str) -> str:
    return " ".join((s or "").split())

def clean_numeric(value):
    """Return float or None from strings like '1,62,840.00', '45000-', '₹ 12,345.67'."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value)
    # keep leading minus if present; strip everything except digits and dots
    s = s.replace(",", "")
    s = re.sub(r"[^\d.\-]", "", s)
    # if ends with '-', move it to front (e.g. 45000- -> -45000)
    if s.endswith("-") and not s.startswith("-"):
        s = "-" + s[:-1]
    try:
        return float(s) if s else None
    except Exception:
        return None

# ---------- type detection ----------
def detect_file_type(file_path: str) -> str:
    p = file_path.lower()
    if p.endswith(".pdf"):
        try:
            doc = fitz.open(file_path)
            has_text, has_image = False, False
            for page in doc:
                if (page.get_text() or "").strip():
                    has_text = True
                if page.get_images(full=True):
                    has_image = True
            doc.close()
            if has_text and not has_image:
                return "Digital PDF"
            if has_image and not has_text:
                return "Scanned PDF"
            if has_text and has_image:
                return "Mixed PDF"
            return "Unknown PDF"
        except Exception as e:
            return f"Error detecting PDF type: {e}"
    if p.endswith((".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff")):
        return "Image File"
    return "Unsupported"

# ---------- text extraction ----------
def extract_text_digital(file_path: str) -> str:
    try:
        text = []
        doc = fitz.open(file_path)
        for page in doc:
            text.append(page.get_text() or "")
        doc.close()
        s = "\n".join(text)
        if not s.strip():
            # fallback to PyPDF2
            reader = PdfReader(file_path)
            s = "\n".join([(pg.extract_text() or "") for pg in reader.pages])
        return s.strip()
    except Exception as e:
        print(f"[extract_text_digital] {e}")
        return ""

def extract_text_scanned(pdf_path: str) -> str:
    try:
        images = convert_from_path(pdf_path)
        out = []
        for img in images:
            out.append(pytesseract.image_to_string(img, lang="eng") or "")
        return "\n".join(out).strip()
    except Exception as e:
        print(f"[extract_text_scanned] {e}")
        return ""

def extract_text_easyocr_pdf(pdf_path: str) -> str:
    try:
        reader = easyocr.Reader(["en"])
        images = convert_from_path(pdf_path)
        out = []
        for img in images:
            res = reader.readtext(img)
            out.extend([t for (_b, t, _c) in res])
        return "\n".join(out).strip()
    except Exception as e:
        print(f"[extract_text_easyocr_pdf] {e}")
        return ""

def extract_text_image(image_path: str) -> str:
    try:
        img = Image.open(image_path)
        s = pytesseract.image_to_string(img, lang="eng") or ""
        if not s.strip():
            reader = easyocr.Reader(["en"])
            res = reader.readtext(image_path)
            s = " ".join([t for (_b, t, _c) in res])
        return s.strip()
    except Exception as e:
        print(f"[extract_text_image] {e}")
        return ""

# ---------- JSON safety & fallbacks ----------
def safe_json_loads(raw: str):
    """Try hard to convert LLM output into a dict."""
    if raw is None:
        return None
    s = raw.strip()

    # strip code fences
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s)
        s = re.sub(r"\s*```$", "", s)

    # grab the outermost JSON object
    m = re.search(r"\{.*\}", s, re.DOTALL)
    if m:
        s = m.group()

    # lazy fixes
    s = s.replace("'", '"')
    s = re.sub(r",\s*}", "}", s)
    s = re.sub(r",\s*]", "]", s)

    try:
        return json.loads(s)
    except Exception:
        return None

def validate_and_fix_json(data: dict) -> dict:
    if not isinstance(data, dict):
        data = {}
    req = [
        "vendor_name", "invoice_number", "invoice_date", "total_amount",
        "currency", "line_items", "tax_amount", "billing_address", "due_date"
    ]
    for k in req:
        data.setdefault(k, None)

    # normalize date
    data["invoice_date"] = normalize_date(data.get("invoice_date"))

    # default currency
    if not data.get("currency"):
        data["currency"] = "INR"

    # numeric normalization
    data["total_amount"] = clean_numeric(data.get("total_amount"))
    data["tax_amount"] = clean_numeric(data.get("tax_amount"))

    # line items
    if not isinstance(data.get("line_items"), list):
        data["line_items"] = []
    for it in data["line_items"]:
        if not isinstance(it, dict): 
            continue
        it["qty"] = clean_numeric(it.get("qty"))
        it["unit_price"] = clean_numeric(it.get("unit_price"))
        it["total"] = clean_numeric(it.get("total"))
        it["description"] = clean_text(it.get("description") or "")

    return data

def regex_fallback_fields(text: str, data: dict) -> dict:
    t = text or ""

    if not data.get("invoice_number"):
        m = re.search(r"(?:Invoice\s*(?:#|No\.?|Number)?)[:\s]*([A-Za-z0-9\-\/]+)", t, re.I)
        if m:
            data["invoice_number"] = m.group(1).strip()

    if not data.get("invoice_date"):
        m = re.search(r"(?:Invoice\s*Date|Date)[:\s]*([^\n]+)", t, re.I)
        if m:
            data["invoice_date"] = normalize_date(m.group(1))

    if not data.get("total_amount"):
        for pat in [r"grand\s*total[:\s]+([\d,.\-]+)",
                    r"balance\s*due[:\s]+([\d,.\-]+)",
                    r"\btotal[:\s]+([\d,.\-]+)"]:
            m = re.search(pat, t, re.I)
            if m:
                data["total_amount"] = clean_numeric(m.group(1))
                break

    if not data.get("tax_amount"):
        m = re.search(r"(?:GST|Tax|VAT)[:\s]+([\d,.\-]+)", t, re.I)
        if m:
            data["tax_amount"] = clean_numeric(m.group(1))

    if not data.get("vendor_name"):
        m = re.search(r"(?:From|Vendor|Supplier)[:\s]*([^\n]+)", t, re.I)
        if m:
            data["vendor_name"] = clean_text(m.group(1))

    if not data.get("billing_address"):
        m = re.search(r"(?:Bill\s*To|Billing\s*Address)[:\s]*([\s\S]+?)(?:Ship\s*To|Invoice|Total|$)", t, re.I)
        if m:
            data["billing_address"] = clean_text(m.group(1))

    return data

# ---------- LLM extraction ----------
def extract_with_llm(text: str, filename: str) -> dict:
    """Try LLM; be resilient to bad JSON."""
    if not create_zunno_llm:
        # LLM not available -> regex-only minimal result
        base = {
            "vendor_name": None, "invoice_number": None, "invoice_date": None,
            "total_amount": None, "currency": "INR", "line_items": [],
            "tax_amount": None, "billing_address": None, "due_date": None
        }
        return regex_fallback_fields(text, base)

    try:
        llm = create_zunno_llm(model_name="mistral:latest")
        schema_hint = """
Respond with a single JSON object, no prose, no markdown, with keys:
vendor_name (string|null),
invoice_number (string|null),
invoice_date (DD-MM-YYYY or null),
total_amount (number|null),
currency (string|null),
line_items (array of {description (string), qty (number|null), unit_price (number|null), total (number|null)}),
tax_amount (number|null),
billing_address (string|object|null),
due_date (DD-MM-YYYY or null).
"""
        prompt = f"""{schema_hint}
TEXT:
{text[:8000]}
"""

        resp = llm.invoke(prompt)
        raw = getattr(resp, "content", str(resp))

        parsed = safe_json_loads(raw)
        if not parsed:
            # last resort: empty dict; we will fill with regex
            parsed = {}

        parsed = validate_and_fix_json(parsed)
        parsed = regex_fallback_fields(text, parsed)
        return parsed

    except Exception as e:
        print(f"[extract_with_llm:{filename}] {e}")
        base = {
            "vendor_name": "extraction_failed",
            "invoice_number": None,
            "invoice_date": None,
            "total_amount": None,
            "currency": "INR",
            "line_items": [],
            "tax_amount": None,
            "billing_address": None,
            "due_date": None,
            "error": str(e),
        }
        return regex_fallback_fields(text, base)

