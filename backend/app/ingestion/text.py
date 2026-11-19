"""
Turn job-board HTML into plain text, and small normalizing helpers.

Descriptions from other websites are untrusted. Waypoint stores and returns
them as plain text only (tags removed here), and the website always inserts
text as text, so nothing in a posting can run as code. Nothing in a posting
is ever treated as an instruction either: it's data to read and score.
"""

import html
import re
from html.parser import HTMLParser

BLOCK = {"p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section", "article"}


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0  # inside <script> or <style>

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        elif tag == "li":
            self.parts.append("\n- ")
        elif tag in BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = max(0, self.skip - 1)
        elif tag in BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_to_text(value: str | None) -> str:
    """'<p>Hello <b>there</b></p><ul><li>SQL</li></ul>' -> 'Hello there\\n\\n- SQL'"""
    if not value:
        return ""
    if "&lt;" in value:  # Greenhouse sends its HTML escaped once more
        value = html.unescape(value)
    parser = _TextExtractor()
    parser.feed(value)
    parser.close()
    text = "".join(parser.parts).replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n(- )?\n(?=- )", "\n", text)  # no blank lines between bullets
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()[:50_000]


def norm(text: str | None) -> str:
    """Lowercase, single spaces, letters and digits only. For comparing names."""
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def slug(text: str) -> str:
    return norm(text).replace(" ", "-")[:60] or "unknown"


def detect_arrangement(*texts: str | None) -> str:
    """'Remote' or 'Hybrid' in the location or title; otherwise unknown."""
    joined = " ".join(t for t in texts if t).lower()
    if "hybrid" in joined:
        return "hybrid"
    if "remote" in joined:
        return "remote"
    return "unknown"


def detect_employment_type(text: str | None) -> str:
    t = (text or "").lower()
    if "intern" in t or "co-op" in t or "coop" in t:
        return "internship"
    if "part" in t:
        return "part_time"
    if "contract" in t or "freelance" in t:
        return "contract"
    if "temp" in t or "fixed term" in t or "fixed-term" in t:
        return "temporary"
    if "full" in t or "permanent" in t or "regular" in t:
        return "full_time"
    return "unknown"
