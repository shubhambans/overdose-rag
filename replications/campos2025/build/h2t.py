"""Convert an HTML file to block text: one block per line, headings marked with '## '.
<sup> (citation numbers) are dropped.
Usage: python -I h2t.py file.html [out.txt]"""
import sys, html, re
from html.parser import HTMLParser

BLOCK = {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "div", "section", "article",
         "br", "tr", "td", "th", "dt", "dd", "summary", "button", "blockquote", "ul", "ol", "details"}
SKIP = {"script", "style", "noscript", "svg", "head", "template"}

class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []; self.buf = []; self.skip = 0; self.tag = None; self.sup = None
    def flush(self):
        t = re.sub(r"\s+", " ", "".join(self.buf)).strip()
        if t:
            pre = {"h1": "# ", "h2": "## ", "h3": "### ", "h4": "#### ", "h5": "##### ", "h6": "###### ",
                   "li": "* ", "summary": "?? ", "button": "[btn] ", "dt": "?? "}.get(self.tag, "")
            self.out.append(pre + t)
        self.buf = []
    def handle_starttag(self, tag, attrs):
        if tag == "sup": self.sup = len(self.buf); return
        if tag in SKIP: self.skip += 1; return
        if tag in BLOCK:
            self.flush(); self.tag = tag
    def handle_startendtag(self, tag, attrs):
        if tag == "br":
            self.flush()
    def handle_endtag(self, tag):
        if tag == "sup":
            # drop citation superscripts (digits/commas/dashes only); keep things like "th" and the registered mark
            if self.sup is not None and re.fullmatch(r"[\d,\s \-–]*", "".join(self.buf[self.sup:])):
                del self.buf[self.sup:]
            self.sup = None; return
        if tag in SKIP: self.skip = max(0, self.skip - 1); return
        if tag in BLOCK:
            self.flush(); self.tag = None
    def handle_data(self, d):
        if not self.skip: self.buf.append(d)

p = P()
raw = open(sys.argv[1], "rb").read().decode("utf-8", errors="replace")
p.feed(raw); p.flush()
txt = "\n".join(p.out)
if len(sys.argv) > 2:
    open(sys.argv[2], "w", encoding="utf-8").write(txt)
else:
    sys.stdout.reconfigure(encoding="utf-8")
    print(txt)
