"""Build faqs.csv from page text extracted by h2t.py.
Each entry: (txt_file, source_org, source_type, url, question_line_in_page, end_line_prefix or None, question_override)
Answer = page lines after the question line, up to (not including) the first line that starts with a
heading/accordion marker or with end_line_prefix. Image captions / ad lines are dropped.
Usage: python -I build.py TXT_DIR OUT_CSV"""
import csv, os, re, sys

TXT, OUT = sys.argv[1], sys.argv[2]
NIDA, NLM, VA = "National Institute on Drug Abuse (NIDA)", "MedlinePlus (National Library of Medicine)", "U.S. Department of Veterans Affairs (VA)"
CT, OR, PA, WA = ("Connecticut Department of Consumer Protection", "Oregon Health Authority",
                  "Pennsylvania Department of Health", "Washington State Department of Health")
YALE, CC, AAFP = "Yale Medicine", "Cleveland Clinic", "American Academy of Family Physicians (familydoctor.org)"
F, S, A, P = "federal_agency", "state_agency", "academic_center", "professional_society"

U_MOUD = "https://nida.nih.gov/research-topics/medications-opioid-use-disorder"
U_FENT = "https://nida.nih.gov/research-topics/fentanyl"
U_OPI = "https://nida.nih.gov/research-topics/opioids"
U_NAL = "https://nida.nih.gov/publications/drugfacts/naloxone"
U_STIG = "https://nida.nih.gov/research-topics/stigma-discrimination"
U_TX = "https://nida.nih.gov/research-topics/treatment"
U_MED = "https://medlineplus.gov/opioidsandopioidusedisorderoud.html"
U_VA = "https://www.va.gov/northern-california-health-care/programs/opioid-overdose-and-naloxone-education/"
U_CT = "https://portal.ct.gov/DCP/Drug-Control-Division/Drug-Control/Opioid-Overdose-PreventionNaloxone-Frequently-Asked-Questions"
U_OR = "https://www.oregon.gov/oha/ph/preventionwellness/substanceuse/opioids/pages/reverseoverdose.aspx"
U_PA = "https://www.pa.gov/agencies/health/programs/opioids/naloxone"
U_WAN = "https://doh.wa.gov/you-and-your-family/drug-user-health/overdose-education-naloxone-distribution/naloxone-instructions"
U_WAR = "https://doh.wa.gov/public-health-provider-resources/healthcare-professions-and-facilities/prescription-monitoring-program-pmp/opioid-prescribing/patients/frequently-asked-questions"
U_YALE = "https://www.yalemedicine.org/conditions/opioid-use-disorder"
U_CCW = "https://my.clevelandclinic.org/health/diseases/opioid-withdrawal"
U_CCN = "https://my.clevelandclinic.org/health/diseases/23226-neonatal-abstinence-syndrome"
U_AAFP = "https://familydoctor.org/condition/opioid-addiction/"

E = [
 ("nida_moud", NIDA, F, U_MOUD, "## What is opioid use disorder?", None),
 ("nida_moud", NIDA, F, U_MOUD, "## What is methadone?", None),
 ("nida_moud", NIDA, F, U_MOUD, "## Where can people get methadone treatment?", None),
 ("nida_moud", NIDA, F, U_MOUD, "## What is buprenorphine?", None),
 ("nida_moud", NIDA, F, U_MOUD, "## Where can people get buprenorphine?", None),
 ("nida_moud", NIDA, F, U_MOUD, "## What is naltrexone?", None),
 ("nida_moud", NIDA, F, U_MOUD, "## Do medications for opioid use disorder work?", None),
 ("nida_moud", NIDA, F, U_MOUD, "## Are medications for opioid use disorder addictive?", None),
 ("nida_moud", NIDA, F, U_MOUD, "## Why do so few people get medications for opioid use disorder?", None),
 ("nida_moud", NIDA, F, U_MOUD, "## Are medications for opioid use disorder safe to use during pregnancy and breastfeeding?", None),
 ("nida_moud", NIDA, F, U_MOUD, "## Do medications for opioid use disorder interfere with pain treatment?", None),
 ("nida_fentanyl", NIDA, F, U_FENT, "## What is fentanyl?", None),
 ("nida_fentanyl", NIDA, F, U_FENT, "## Why is fentanyl dangerous?", None),
 ("nida_fentanyl", NIDA, F, U_FENT, "## How can I find out if my drugs or pills contain fentanyl?", None),
 ("nida_fentanyl", NIDA, F, U_FENT, "## What should I do if I think someone is overdosing?", None),
 ("nida_opioids", NIDA, F, U_OPI, "## Are opioids addictive?", None),
 ("nida_naloxone", NIDA, F, U_NAL, "### Is Narcan® the same as naloxone?", None),
 ("nida_naloxone", NIDA, F, U_NAL, "## Can I give naloxone to someone who has overdosed?", None),
 ("nida_stigma", NIDA, F, U_STIG, "## What is stigma against substance use and addiction? Why does it occur?", None),
 ("nida_stigma", NIDA, F, U_STIG, "## How do language and criminalization perpetuate stigma against people who use drugs or have substance use disorders?", None),
 ("nida_treatment", NIDA, F, U_TX, "## If someone relapses, does that mean the treatment failed?", None),
 ("medline_opioid", NLM, F, U_MED, "### What are opioids?", None),
 ("medline_opioid", NLM, F, U_MED, "### What are the side effects and risks of opioids?", None),
 ("medline_opioid", NLM, F, U_MED, "### How are opioid use disorder (OUD) and opioid overdose treated?", None),
 ("va_ncal", VA, F, U_VA, "### What is naloxone?", "To learn more about how to use naloxone"),
 ("ct_dcp", CT, S, U_CT, "How does naloxone work?", "What are the risks associated with naloxone use?"),
 ("ct_dcp", CT, S, U_CT, "Where do I store the naloxone?", "Who do I call if I use my naloxone"),
 ("ct_dcp", CT, S, U_CT, "Will naloxone work if the person overdosed on something other than an opioid?", "Is naloxone available over the counter?"),
 ("ct_dcp", CT, S, U_CT, "What increases/decreases risk of an opioid overdose?", "Are all overdoses the same?"),
 ("ct_dcp", CT, S, U_CT, "Will the person who recovers from an overdose be violent?", "Can a person re-overdose"),
 ("ct_dcp", CT, S, U_CT, "Can a person re-overdose after the naloxone has been given?", "Overdose kits are a handy way"),
 ("or_reverse", OR, S, U_OR, "5. Will insurance cover naloxone?", "6. How much do OORM cost?"),
 ("or_reverse", OR, S, U_OR, "8. What are my risks if I use OORM on someone?", "9. How many doses"),
 ("or_reverse", OR, S, U_OR, "9. How many doses of OORM do I give a person?", "10. Can OORM be given"),
 ("pa_nalox", PA, S, U_PA, "[btn] How do I administer naloxone?", None),
 ("pa_nalox", PA, S, U_PA, "[btn] How can someone with an addiction to prescription pain medicines, heroin, fentanyl, or other drugs get help?", None),
 ("wa_nalox", WA, S, U_WAN, "Does the law protect against any other charges?", "If I don't call 911"),
 ("wa_nalox", WA, S, U_WAN, "If I don't call 911 but I take the overdose victim to the emergency room, will the law still apply?", "Does the law apply if the person dies"),
 ("wa_rxfaq", WA, S, U_WAR, "?? What do I do with my unused opioid medications?", None),
 ("yale_oud", YALE, A, U_YALE, "## What are the risk factors for opioid use disorder?", None),
 ("yale_oud", YALE, A, U_YALE, "## What is medically managed withdrawal or \"detoxification\"?", None),
 ("yale_oud", YALE, A, U_YALE, "## How does opioid use disorder affect pregnant women and newborns?", None),
 ("yale_oud", YALE, A, U_YALE, "## What is the outlook for people who have opioid use disorder?", None),
 ("cc_withdrawal", CC, A, U_CCW, "#### How long do withdrawal symptoms last?", None),
 ("cc_withdrawal", CC, A, U_CCW, "### What are the complications of opioid withdrawal?", None),
 ("cc_withdrawal", CC, A, U_CCW, "### What are treatments for opioid withdrawal?", "Care at Cleveland Clinic"),
 ("cc_nows", CC, A, U_CCN, "### Can I breastfeed my newborn if I take drugs?", "Care at Cleveland Clinic"),
 ("famdoc", AAFP, P, U_AAFP, "What is the difference between drug tolerance, dependence, and addiction?", "How is opioid addiction diagnosed?"),
 ("famdoc", AAFP, P, U_AAFP, "How is opioid addiction diagnosed?", "Can opioid addiction be prevented or avoided?"),
 ("famdoc", AAFP, P, U_AAFP, "Can opioid addiction be prevented or avoided?", None),
]

DROP = [re.compile(p) for p in [r"^Advertisement$", r"^Cleveland Clinic is a non-profit academic medical center",
        r"^Image$", r"^Figure: ", r"^Care at Cleveland Clinic$"]]
STOP = re.compile(r"^(#|\[btn\] |\?\? )")

cache = {}
rows, seen = [], set()
for i, (f, org, typ, url, qline, end) in enumerate(E, 1):
    lines = cache.setdefault(f, open(os.path.join(TXT, f + ".txt"), encoding="utf-8").read().split("\n"))
    idx = [k for k, l in enumerate(lines) if l == qline]
    assert len(idx) >= 1, (f, qline)
    k = idx[0] + 1
    parts = []
    while k < len(lines):
        l = lines[k]
        if STOP.match(l) or (end and l.startswith(end)):
            break
        if not any(d.search(l) for d in DROP):
            parts.append(re.sub(r"^\* ", "", l).strip())
        k += 1
    if end:
        assert k < len(lines) and lines[k].startswith(end), ("end not found", f, qline)
    q = re.sub(r"^(#+ |\[btn\] |\?\? |\d+\. )", "", qline).strip()
    a = " ".join(p for p in parts if p).replace("​", "")  # zero-width spaces (HTML artifact)
    a = re.sub(r"\s+", " ", a).strip()
    assert a, (f, q)
    assert q.lower() not in seen, q
    seen.add(q.lower())
    rows.append({"id": f"f{i:02d}", "source_org": org, "source_type": typ, "url": url,
                 "question": q, "answer": a, "accessed": "2026-11-02"})

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["id", "source_org", "source_type", "url", "question", "answer", "accessed"])
    w.writeheader(); w.writerows(rows)
sys.stdout.reconfigure(encoding="utf-8")
for r in rows:
    print(r["id"], len(r["answer"].split()), "|", r["question"])
print("rows:", len(rows))
