"""
Shared rules for contract / project / traveaux document uploads (not images).
"""
import os

# Lowercase extensions only (FileExtensionValidator on models is case-insensitive on validation)
DOCUMENT_UPLOAD_EXTENSIONS = (
    "pdf",
    "csv",
    "xls",
    "xlsx",
    "xlsm",
    "xlsb",
    "xltx",
    "xltm",
    "doc",
    "docx",
    "docm",
    "dotx",
)

ALLOWED_DOCUMENT_CONTENT_TYPES = frozenset(
    {
        "application/pdf",
        "application/x-pdf",
        "text/csv",
        "application/csv",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel.sheet.macroEnabled.12",
        "application/vnd.ms-excel.sheet.binary.12",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.template",
        "application/vnd.ms-excel.template.macroEnabled.12",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-word.document.macroEnabled.12",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.template",
    }
)

ALLOWED_FORMATS_USER_MESSAGE = (
    "Allowed types: PDF, CSV, Excel (.xls, .xlsx, .xlsm, .xlsb, .xltx, .xltm), "
    "Word (.doc, .docx, .docm, .dotx)."
)


def is_allowed_document_upload(upload) -> bool:
    """
    Accept by file extension (preferred) or by browser-reported content type.
    Many desktop apps upload Excel/Word as application/octet-stream; extension then must match.
    """
    name = getattr(upload, "name", "") or ""
    base = os.path.basename(name)
    if "." in base:
        ext = base.rsplit(".", 1)[-1].lower()
        if ext in DOCUMENT_UPLOAD_EXTENSIONS:
            return True
    ct = (getattr(upload, "content_type", None) or "").lower()
    return ct in ALLOWED_DOCUMENT_CONTENT_TYPES
