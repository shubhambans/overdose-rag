"""Download full text for every paper in papers/papers.csv from PubMed Central.

Usage: python src/fetch_papers.py

Papers are saved to docs/papers/ (git-ignored), so the public repo only stores
the list of papers, not copies of them. To add papers, add rows to papers.csv.
"""
import csv
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIST = ROOT / "papers" / "papers.csv"
OUT = ROOT / "docs" / "papers"
EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&rettype=xml&id={}"


def text(el):
    return " ".join("".join(el.itertext()).split()) if el is not None else ""


def parse(xml: bytes):
    art = ET.fromstring(xml).find(".//article")
    if art is None:
        return None
    meta = art.find("front/article-meta")
    title = text(meta.find("title-group/article-title"))
    doi = text(meta.find("article-id[@pub-id-type='doi']"))
    license_ = text(meta.find("permissions/license")) or text(meta.find("permissions/copyright-statement"))
    authors = meta.findall("contrib-group/contrib[@contrib-type='author']/name/surname")
    first_author = authors[0].text if authors else ""
    abstract = "\n".join(text(p) for p in meta.findall("abstract//p")) or text(meta.find("abstract"))

    body_parts = []
    body = art.find("body")
    if body is not None:
        for sec in body.iter("sec"):
            heading = text(sec.find("title"))
            paras = [text(p) for p in sec.findall("p")]
            if paras:
                body_parts.append((f"## {heading}\n" if heading else "") + "\n".join(paras))
        if not body_parts:  # papers with no <sec> structure
            body_parts = [text(p) for p in body.iter("p")]
    return dict(title=title, doi=doi, license=license_[:300], first_author=first_author,
                abstract=abstract, body="\n\n".join(body_parts))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(LIST.open()))
    full, abstract_only, failed = 0, 0, []
    for r in rows:
        pmcid = r["pmcid"]
        path = OUT / f"paper_{r['topic']}_{pmcid}.txt"
        if path.exists():
            full += 1
            continue
        try:
            with urllib.request.urlopen(EFETCH.format(pmcid.replace("PMC", "")), timeout=30) as resp:
                p = parse(resp.read())
        except Exception as e:  # network or XML error
            failed.append(f"{pmcid} ({e})")
            continue
        if not p or not (p["body"] or p["abstract"]):
            failed.append(f"{pmcid} (no text)")
            continue
        kind = "full text" if p["body"] else "abstract only"
        full += bool(p["body"])
        abstract_only += not p["body"]
        path.write_text(
            f"Title: {p['title']}\nAuthors: {p['first_author']} et al. ({r['year']})\n"
            f"Source: PubMed Central {pmcid}, PMID {r['pmid']}, doi:{p['doi']}\n"
            f"License: {p['license']}\nContent: {kind}\n\n"
            f"ABSTRACT\n{p['abstract']}\n\n{p['body']}\n"
        )
        print(f"{pmcid}: {kind}  {p['title'][:70]}")
        time.sleep(0.4)  # NCBI allows ~3 requests/second without an API key
    print(f"\n{full} full text, {abstract_only} abstract only, {len(failed)} failed")
    for f in failed:
        print("  failed:", f)


if __name__ == "__main__":
    main()
