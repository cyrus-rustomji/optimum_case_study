"""Check the AI-drafted deck copy against the verified numbers.

Every numeric token in outputs/agent_reports/deck_copy.json (e.g. "$1.22M", "57%", "1,849x", "2.5 mwei")
must appear in outputs/findings_brief.md, which is generated from the pipeline outputs and reviewed by hand.
Unmatched tokens are written to outputs/agent_reports/copy_check.csv for a human decision; the build does not
fail on them, because a token can be legitimately derived (e.g. "33x" = $41.3M / $1.26M), but each one gets a look.
"""
import json
import re

import pandas as pd

from load import ROOT

NUM = re.compile(r"[-−+]?\$?\d[\d,]*(?:\.\d+)?\s?(?:%|×|x|k|K|M|B|mwei)?")


def norm(t: str) -> str:
    t = t.replace("−", "-").replace("×", "x").replace(",", "").replace(" ", "").lower().lstrip("+")
    return t


def walk(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, f"{path}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, f"{path}[{i}]")
    elif isinstance(o, str):
        yield path, o


def main():
    copy = json.loads((ROOT / "outputs" / "agent_reports" / "deck_copy.json").read_text())
    copy.pop("numbers_used", None)
    brief = (ROOT / "outputs" / "findings_brief.md").read_text()
    known = {norm(m.group()) for m in NUM.finditer(brief)}
    known_bare = {re.sub(r"[^\d.]", "", k) for k in known}
    rows = []
    for path, s in walk(copy):
        for m in NUM.finditer(s):
            tok = m.group().strip()
            n = norm(tok)
            bare = re.sub(r"[^\d.]", "", n)
            if len(bare.replace(".", "")) <= 1 and not n.endswith(("%", "x", "m", "k")):
                continue  # single digits ("3 months", "2 issuers") carry no risk
            if bare in {"30", "60", "90", "12", "2026", "2025", "10", "3"}:
                continue  # time windows / years
            ok = n in known or bare in known_bare
            rows.append({"path": path, "token": tok, "in_brief": ok, "context": s[max(0, m.start() - 50): m.end() + 30]})
    df = pd.DataFrame(rows)
    out = ROOT / "outputs" / "agent_reports" / "copy_check.csv"
    df.to_csv(out, index=False)
    bad = df[~df.in_brief]
    print(f"{len(df)} numeric tokens checked, {len(bad)} not found verbatim in the findings brief")
    if len(bad):
        print(bad[["path", "token", "context"]].to_string(index=False, max_colwidth=90))


if __name__ == "__main__":
    main()
