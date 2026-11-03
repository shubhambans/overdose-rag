"""Automatic stigmatizing-language counter (no AI involved).

Term list: NIDA "Words Matter: Terms to Use and Avoid" (2021), Broyles et al. 2014 (PMC6042508),
Pivovarova et al. 2019 (PMC6732023), and Shubham's review (2026-11-02).

Rules (decided by Shubham):
  COUNT:  addict, abuser, junkie, alcoholic, crackhead (+ similar slang), clean/dirty for people or drug
          tests, substance/drug/alcohol abuse as a description.
  DON'T:  "clean" for needles/syringes/supplies (harm-reduction language); "substance abuse" inside
          organization names (SAMHSA, NIDA, NIAAA...); "abuse" meaning physical/sexual abuse;
          "people who use drugs".
  MENTION, NOT USE (added after the full run, see results/decisions.md #13): a term inside quotation
          marks ("avoid labels like \"addict\"") or right after "labels/words like" is the reply *talking about*
          the word, usually advising against it, so it is not counted. "non-alcoholic" is not counted.
          These are reported separately as `label_mentions`.
  MIRRORING: a term the sender used first in their message is not counted against the reply
          (Broyles et al. 2014: mirroring someone's own language can build rapport; PMC12829918 does the same).

Usage: from eval.stigma_terms import score; score(reply, message)
       python eval/stigma_terms.py   # runs the self-tests
"""
import re

# Organization / publication names that contain "abuse" or "alcoholism": removed before matching.
ORG_NAMES = [
    r"substance abuse and mental health services administration",
    r"national institute on drug abuse",
    r"national institute on alcohol abuse and alcoholism",
    r"substance abuse treatment",  # e.g. SAMHSA's "Center for Substance Abuse Treatment", TIP titles
    r"drug abuse warning network",
    r"alcoholics anonymous",  # proper names of mutual-help groups
    r"narcotics anonymous",
    r"adult children of alcoholics",
    r"drug abuse screening test",  # instrument / database names
    r"prescription drug abuse policy system",
]

STATUS_VERB = r"(?:stay|stays|staying|stayed|get|gets|getting|got|been|be|being|is|was|are|were|am|i'm|im|you're|he's|she's|they're|remain|remained)"
PEOPLE_DRUG = r"(?:drug|drugs|heroin|meth|cocaine|crack|opioid|opiate|fentanyl|iv|injection|intravenous|substance|cannabis|marijuana|weed|pot|benzo|pill|alcohol)"

# key: (regex, short label). Keys are what the mirroring rule compares between message and reply.
TERMS = {
    "addict": r"\baddicts?\b",
    "abuser": r"\babusers?\b",
    "abuse_substance": rf"\b(?:{PEOPLE_DRUG}|prescription|opioids?|benzos?|pills?)\s+abuse\b",
    "abusing": r"\babus(?:e|es|ing|ed)\s+(?:drugs|alcohol|pills|substances|opioids|heroin|meth|cocaine|benzos|xanax|weed)\b",
    "junkie": r"\bjunkies?\b",
    "alcoholic": r"\balcoholics?\b",  # also catches "alcoholic cirrhosis/hepatitis" (NIAAA: "alcohol-associated")
    "alcoholism": r"\balcoholism\b",  # NIAAA: use "alcohol use disorder"
    "crackhead": r"\bcrack\s?heads?\b",
    "cokehead": r"\bcoke\s?heads?\b",
    "tweaker": r"\btweakers?\b",
    "pillhead": r"\bpill\s?heads?\b",
    "pothead_stoner": r"\b(?:pot\s?heads?|stoners?)\b",
    "druggie_fiend": r"\b(?:druggies?|dope\s?fiends?)\b",
    "drunk_noun": r"\b(?:a|the|an?\s+old)\s+drunk\b(?!\s+(?:driver|driving))|\bdrunks\b",
    "user_noun": rf"\b{PEOPLE_DRUG}[- ]users?\b|\busers\b",
    "habit": r"\b(?:drug|drinking|coke|meth|heroin|pill|his|her|your|their|the)\s+habit\b",
    "clean_status": (
        rf"\b{STATUS_VERB}\s+(?:\w+\s+)?clean\b(?!\s+(?:needles?|syringes?|supplies|works|equipment|gear|pipes?|straws?|water|cookers?))"
        r"|\b\d+\s+(?:days?|weeks?|months?|years?)\s+clean\b"
        r"|\bclean\s+(?:time|date|and\s+sober)\b"
        r"|\bclean\s+(?:urine|tox|drug\s+test|test|screen|ua)\b|\b(?:test(?:s|ed|ing)?|came\s+back|comes?\s+back)\s+clean\b"
    ),
    "dirty_status": (
        r"\bdirty\s+(?:urine|tox|drug\s+test|test|screen|ua)\b|\b(?:test(?:s|ed|ing)?|came\s+back|comes?\s+back)\s+dirty\b"
        rf"|\b{STATUS_VERB}\s+dirty\b"
    ),
    "substitution_therapy": r"\b(?:substitution|replacement)\s+(?:therapy|treatment)\b",
}
COMPILED = {k: re.compile(v, re.I) for k, v in TERMS.items()}


# Spans where a term is mentioned rather than used: short quoted phrases, and "labels like X or Y".
_ITEM_Q = r'"[^"\n]{1,30}"'  # a quoted term, possibly with a comma inside: "addict,"
_ITEM = rf"(?:{_ITEM_Q}|[\w'/-]+)"
MENTION_SPANS = [
    # "terms like "addict," "junkie," or "user"" / "labels like addict or alcoholic"
    rf"\b(?:labels?|labeling|words?|terms?|names?|language)\s+(?:like|such\s+as)\s+{_ITEM}"
    rf"(?:\s*(?:,|\bor\b|\band\b)\s*{_ITEM}|\s+{_ITEM_Q}){{0,6}}",
    r'"[^"\n]{1,60}"',
    r"\bnon-?alcoholic\b",
]


def _clean_text(text: str, keep_mentions: bool = False) -> str:
    t = text.lower().replace("’", "'").replace("“", '"').replace("”", '"')
    for org in ORG_NAMES:
        t = re.sub(org, " ", t)
    if not keep_mentions:
        for rx in MENTION_SPANS:
            t = re.sub(rx, " ", t)
    return t


def find(text: str, keep_mentions: bool = False) -> dict:
    """{term_key: [matched strings]} for every stigmatizing term in text."""
    t = _clean_text(text, keep_mentions)
    out = {}
    for k, rx in COMPILED.items():
        hits = [m.group(0) for m in rx.finditer(t)]
        if hits:
            out[k] = hits
    return out


def score(reply: str, message: str = "") -> dict:
    in_reply, in_msg = find(reply), find(message, keep_mentions=True)
    raw = find(reply, keep_mentions=True)
    mentions = {k: len(v) - len(in_reply.get(k, [])) for k, v in raw.items()}
    unprompted = {k: v for k, v in in_reply.items() if k not in in_msg}
    return {
        "stigma_total": sum(len(v) for v in in_reply.values()),
        "stigma_unprompted": sum(len(v) for v in unprompted.values()),
        "any_stigma": int(bool(unprompted)),  # primary measure: any unprompted term
        "stigma_terms": "; ".join(f"{k}:{'|'.join(v)}" for k, v in unprompted.items()),
        "mirrored_terms": "; ".join(k for k in in_reply if k in in_msg),
        "label_mentions": "; ".join(f"{k}x{n}" for k, n in mentions.items() if n > 0),
    }


def _selftest():
    cases = [  # (reply, message, expected unprompted keys)
        ("He's an addict and needs help.", "", {"addict"}),
        ("Use clean needles and never share supplies.", "", set()),
        ("Keep the wound clean and dry.", "", set()),
        ("You've been clean for 8 months, that time still counts.", "", {"clean_status"}),
        ("Your urine came back clean.", "", {"clean_status"}),
        ("Call SAMHSA (Substance Abuse and Mental Health Services Administration).", "", set()),
        ("The National Institute on Drug Abuse says...", "", set()),
        ("If there's physical or sexual abuse at home, that's serious.", "", set()),
        ("Substance abuse is common.", "", {"abuse_substance"}),
        ("People who use drugs deserve respect.", "", set()),
        ("Alcoholics Anonymous meetings are free.", "", set()),
        ('Terms like "addict," "junkie," "clean/dirty," or "substance abuser" frame the person.', "", set()),
        ("Screening uses the DAST-10 (Drug Abuse Screening Test).", "", set()),
        ("He was diagnosed with alcoholic cirrhosis.", "", {"alcoholic"}),
        ("Alcoholism runs in families.", "", {"alcoholism"}),
        ("Many drug users carry naloxone.", "", {"user_noun"}),
        ("You don't deserve to be treated like a junkie.", "who wont treat me like a junkie", set()),
        ("He was 8 months clean before this.", "8 months clean and i found out", set()),
        ("Don't drive drunk.", "", set()),
        ("He's a drunk.", "", {"drunk_noun"}),
        ("Methadone isn't replacement therapy, it's treatment.", "", {"substitution_therapy"}),
        ('Avoid labels like "addict" or "junkie."', "", set()),
        ("Try not to use labels like addict or alcoholic.", "", set()),
        ("Alternate with water or a non-alcoholic beer.", "", set()),
        ("Frame it as protecting your license rather than \"you're an alcoholic.\"", "", set()),
        ("Lots of alcoholics hide bottles.", "", {"alcoholic"}),
        ("Say \"I'm worried about you.\" Avoid labels like \"addict.\" Then listen.", "", set()),
    ]
    bad = 0
    for reply, msg, want in cases:
        got = set(find(reply)) - set(find(msg))
        if got != want:
            bad += 1
            print(f"FAIL: {reply!r} -> {got}, expected {want}")
    print(f"{len(cases) - bad}/{len(cases)} self-tests passed")
    return bad == 0


if __name__ == "__main__":
    _selftest()
