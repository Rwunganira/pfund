"""Utilities for activity reports: HTML sanitization to prevent XSS."""
import re
from typing import Optional

try:
    import bleach
    HAS_BLEACH = True
except ImportError:
    HAS_BLEACH = False

# Allowed tags and attributes for rich text (headings, bold, lists, links)
ALLOWED_TAGS = [
    "p", "br", "strong", "b", "em", "i", "u", "s",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li",
    "a", "blockquote", "span", "div",
]
ALLOWED_ATTRS = {"a": ["href", "title", "target"], "span": ["class"], "div": ["class"]}


def sanitize_report_html(html: Optional[str]) -> str:
    """Sanitize HTML from the report editor. Returns safe HTML or empty string."""
    if not html or not html.strip():
        return ""
    html = html.strip()
    if HAS_BLEACH:
        return bleach.clean(
            html,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRS,
            strip=True,
        )
    # Minimal allowlist without bleach: strip all tags except allowed, remove attributes except a href
    return _minimal_sanitize(html)


def _minimal_sanitize(html: str) -> str:
    """Fallback: allow only safe tags and href on <a>. Very basic."""
    # Remove script, style, iframe, object, embed
    html = re.sub(r"<(script|style|iframe|object|embed)\b[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<(script|style|iframe|object|embed)\b[^>]*/?>", "", html, flags=re.IGNORECASE)
    # Allow only these tags; strip others (replace with content)
    allowed = set(ALLOWED_TAGS)
    # Strip dangerous attributes (onerror, onclick, etc.)
    html = re.sub(r"\s+on\w+\s*=\s*[\"'][^\"']*[\"']", "", html, flags=re.IGNORECASE)
    html = re.sub(r"\s+on\w+\s*=\s*[^\s>]+", "", html, flags=re.IGNORECASE)
    # Allow only href and title on <a>
    def clean_a(m):
        href = ""
        for attr in re.finditer(r'(\w+)\s*=\s*["\']([^"\']*)["\']', m.group(1)):
            if attr.group(1).lower() in ("href", "title", "target"):
                if attr.group(1).lower() == "href":
                    url = attr.group(2).strip()
                    if url.startswith("http://") or url.startswith("https://") or url.startswith("/") or url.startswith("#"):
                        href = f' href="{url}"'
        return f"<a{href}>"
    html = re.sub(r"<a\s+([^>]*)>", clean_a, html, flags=re.IGNORECASE)
    return html
