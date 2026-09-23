#!/usr/bin/env python3
"""Markdown -> print-ready HTML -> PDF (Chrome headless). Tuned for Chinese study notes."""
import html
import re
import subprocess
import sys
from pathlib import Path

import markdown

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

CSS = """
@page { size: A4; margin: 17mm 16mm 18mm 16mm; }

:root {
  --ink: #1c1c1e;
  --ink-soft: #4a4a4f;
  --rule: #d8d8dd;
  --rule-soft: #ebebef;
  --accent: #b0451f;
  --quote-bg: #faf7f3;
  --quote-bar: #c9713f;
}

* { box-sizing: border-box; }

body {
  font-family: "PingFang SC", "Hiragino Sans GB", "Songti SC", sans-serif;
  font-size: 10.5pt;
  line-height: 1.78;
  color: var(--ink);
  margin: 0;
  text-align: justify;
  text-justify: inter-ideograph;
  -webkit-font-smoothing: antialiased;
}

/* ---------- title block ---------- */
h1 {
  font-size: 20pt;
  line-height: 1.35;
  font-weight: 600;
  letter-spacing: 0.01em;
  margin: 0 0 6mm;
  padding-bottom: 4mm;
  border-bottom: 2px solid var(--ink);
}

h2 {
  font-size: 14pt;
  font-weight: 600;
  line-height: 1.4;
  margin: 11mm 0 4mm;
  padding-bottom: 2mm;
  border-bottom: 1px solid var(--rule);
  break-after: avoid;
  break-inside: avoid;
}

h3 {
  font-size: 11.5pt;
  font-weight: 600;
  color: var(--accent);
  margin: 7mm 0 2.5mm;
  break-after: avoid;
  break-inside: avoid;
}

h2 + h3 { margin-top: 4mm; }

p { margin: 0 0 3mm; orphans: 2; widows: 2; }

strong { font-weight: 600; }

/* ---------- lists ---------- */
ul, ol { margin: 0 0 3.5mm; padding-left: 6.5mm; }
li { margin-bottom: 1.6mm; }
li > ul, li > ol { margin: 1.6mm 0 0; }
li:last-child { margin-bottom: 0; }
ul { list-style-type: disc; }
ul ul { list-style-type: circle; }
li::marker { color: var(--accent); }
ol > li::marker { color: var(--ink-soft); font-weight: 600; }

/* ---------- blockquote (used heavily for key lines) ---------- */
blockquote {
  margin: 3.5mm 0;
  padding: 3mm 4mm 3mm 4.5mm;
  border-left: 2.5pt solid var(--quote-bar);
  background: var(--quote-bg);
  border-radius: 0 1.5mm 1.5mm 0;
  break-inside: avoid;
}
blockquote p { margin: 0 0 2mm; }
blockquote p:last-child { margin-bottom: 0; }
blockquote blockquote {
  margin: 2mm 0 0;
  background: transparent;
  border-left-width: 1.5pt;
  padding: 0 0 0 3mm;
}

/* ---------- tables ---------- */
table {
  width: 100%;
  border-collapse: collapse;
  margin: 3.5mm 0 4.5mm;
  font-size: 9.8pt;
  line-height: 1.6;
  break-inside: avoid;
}
th, td {
  border: 0.5pt solid var(--rule);
  padding: 2mm 2.6mm;
  text-align: left;
  vertical-align: top;
}
th {
  background: #f4f4f6;
  font-weight: 600;
  white-space: nowrap;
}
td:first-child { white-space: nowrap; }
/* A first column that carries real prose must wrap, or it eats the table.
   `wrap-first` is set by the converter when any first cell is long. */
table.wrap-first td:first-child { white-space: normal; }

/* ---------- inline code ---------- */
code {
  font-family: "SF Mono", Menlo, monospace;
  font-size: 0.88em;
  background: #f2f2f5;
  padding: 0.4mm 1.2mm;
  border-radius: 1mm;
  color: #3a3a3f;
}

/* ---------- rules ---------- */
hr {
  border: none;
  border-top: 0.5pt solid var(--rule-soft);
  margin: 7mm 0;
}

/* the note's own "先记住三句" / 来源说明 read better slightly dimmed */
h2:last-of-type ~ ul { color: var(--ink-soft); }
"""


def widen_nesting(text: str) -> str:
    """Python-Markdown needs 4-space nesting; these notes are written with 2.

    Doubling every even leading indent turns 2->4, 4->8 and keeps depth order.
    Safe here because the notes use no fenced code blocks.
    """
    out = []
    for line in text.split("\n"):
        indent = len(line) - len(line.lstrip(" "))
        if indent and indent % 2 == 0:
            line = " " * (indent * 2) + line.lstrip(" ")
        out.append(line)
    return "\n".join(out)


def unwrap_long_first_column(body: str, limit: int = 14) -> str:
    """Tag tables whose first column holds prose rather than a short label.

    `td:first-child { white-space: nowrap }` keeps short label columns tidy, but
    on a table like a term-restoration list it forces column one to the width of
    its longest sentence and crushes the rest. Measure instead of guessing.
    """
    def tag(m: re.Match) -> str:
        table = m.group(0)
        firsts = [re.sub(r"<[^>]+>", "", c)
                  for c in re.findall(r"<tr>\s*<td[^>]*>(.*?)</td>", table, re.S)]
        if any(len(c.strip()) > limit for c in firsts):
            return table.replace("<table>", '<table class="wrap-first">', 1)
        return table

    return re.sub(r"<table>.*?</table>", tag, body, flags=re.S)


def convert(md_path: Path, pdf_path: Path) -> None:
    text = widen_nesting(md_path.read_text(encoding="utf-8"))
    body = markdown.markdown(
        text,
        extensions=["tables", "sane_lists", "attr_list"],
        output_format="html5",
    )
    body = unwrap_long_first_column(body)
    title = html.escape(md_path.stem)
    page = (
        "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
        f"<title>{title}</title><style>{CSS}</style></head><body>{body}</body></html>"
    )
    html_path = pdf_path.with_suffix(".html")
    html_path.write_text(page, encoding="utf-8")

    subprocess.run(
        [
            CHROME,
            "--headless",
            "--disable-gpu",
            "--no-pdf-header-footer",
            "--run-all-compositor-stages-before-draw",
            "--virtual-time-budget=6000",
            f"--print-to-pdf={pdf_path}",
            html_path.as_uri(),
        ],
        check=True,
        capture_output=True,
    )
    html_path.unlink()


if __name__ == "__main__":
    convert(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
