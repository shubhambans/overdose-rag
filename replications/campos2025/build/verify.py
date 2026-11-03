"""Independent check: every 6-word window of each answer (and the question) must occur in the raw HTML
of its source page after crude tag stripping. Usage: python -I verify.py HTML_DIR CSV"""
import csv, html, re, sys
sys.stdout.reconfigure(encoding="utf-8")
HTML, CSV = sys.argv[1], sys.argv[2]
URL2FILE = {
 "medications-opioid-use-disorder": "nida_moud", "research-topics/fentanyl": "nida_fentanyl",
 "research-topics/opioids": "nida_opioids", "drugfacts/naloxone": "nida_naloxone",
 "stigma-discrimination": "nida_stigma", "research-topics/treatment": "nida_treatment",
 "medlineplus": "medline_opioid", "northern-california": "va_ncal", "portal.ct.gov": "ct_dcp",
 "oregon.gov": "or_reverse", "pa.gov": "pa_nalox", "naloxone-instructions": "wa_nalox",
 "opioid-prescribing/patients": "wa_rxfaq", "yalemedicine": "yale_oud", "opioid-withdrawal": "cc_withdrawal",
 "neonatal-abstinence": "cc_nows", "familydoctor": "famdoc"}
def norm(s):
    s = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", s)
    s = re.sub(r"(?is)<sup>(?:[\d,\s\-–]|&nbsp;)*</sup>", "", s)       # citation numbers
    s = re.sub(r"(?is)</?(a|span|strong|em|b|i|sup|u|abbr)\b[^>]*>", "", s)  # inline tags: no space
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = html.unescape(s).replace("​", "")
    return re.sub(r"\s+", " ", s).strip()
pages = {}
bad = 0
for r in csv.DictReader(open(CSV, encoding="utf-8")):
    f = next(v for k, v in URL2FILE.items() if k in r["url"])
    if f not in pages:
        pages[f] = norm(open(f"{HTML}/{f}.html", "rb").read().decode("utf-8", "replace"))
    page = pages[f]
    miss = []
    for field in ("question", "answer"):
        w = r[field].split()
        n = min(6, len(w))
        for i in range(0, len(w) - n + 1):
            frag = " ".join(w[i:i + n])
            if frag not in page:
                miss.append(frag)
    print(r["id"], f, "OK" if not miss else f"MISSING {len(miss)}: {miss[:3]}")
    bad += bool(miss)
print("rows with problems:", bad)
