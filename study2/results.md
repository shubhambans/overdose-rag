# Study 2A results (pipeline check, NOT a finding)

PIPELINE CHECK on 60 AI-written template messages. Not a finding about real people's writing.

| Method | Accuracy | Chance |
|---|---|---|
| TF-IDF + logistic regression (5-fold, grouped by scenario) | 28% | 17% |
| Claude Haiku 5.5 zero-shot | 45% (21 'unsure') | 17% |

## Top words per substance (baseline, fit on all 60; masked text)

- **alcohol**: got, fifth, drinks, my drinking, drinking without, most
- **benzodiazepines**: taking, took, seizure, had seizure, like substance, substance substance
- **cannabis**: all day, of substance, smokes substance, smokes, smoke, bunch of
- **cocaine**: found baggie, baggie of, chest, baggie, did couple, lines
- **heroin_fentanyl**: used, used substance, foil, using, and used, times day
- **methamphetamine**: days, on, people, was up, talking, smoked substance

These are the residual cues left after masking, i.e. the substance-specific details we wrote into the template slots (e.g. 'track marks', 'nodding out', 'up for days'). On real data, this list is what to inspect for leakage.
