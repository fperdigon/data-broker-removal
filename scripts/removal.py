#!/usr/bin/env python3
"""Data broker removal tracker. Standard library only.

Commands
  init                         create profile/profile.json and state/requests.json from the examples
  fastpath                     brokers to do first (no human step, or a single click), skipping finished ones
  mark ID STATUS [--note T] [--email E] [--recheck YYYY-MM-DD]
                               log what happened at one broker
  status                       text summary
  report [--out FILE]          write the HTML dashboard for this person

All personal data lives in profile/ and state/ and reports/, which are git-ignored.
"""
import argparse
import datetime as dt
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BROKER_DIR = ROOT / "brokers"
PROFILE = ROOT / "profile" / "profile.json"
PROFILE_EXAMPLE = ROOT / "profile" / "profile.example.json"
STATE = ROOT / "state" / "requests.json"
STATE_EXAMPLE = ROOT / "state" / "requests.example.json"
TEMPLATE = ROOT / "templates" / "report.html"
REPORTS = ROOT / "reports"

STATUSES = {
    "submitted": "Request submitted",
    "pending-email": "Waiting for an email confirmation",
    "needs-user": "Needs the person (CAPTCHA, login or choice)",
    "blocked": "Blocked by a bot check, cannot be automated",
    "not-found": "Checked, the person is not listed",
    "defunct": "Site no longer operates as a people-search",
    "unverified": "Checked but the result is unreliable, retry",
}
# Lower number = do earlier. Only these automation levels are 'fast path'.
FASTPATH_ORDER = {"email-confirm": 0, "one-human-check": 1, "one-captcha": 2}
AUTOMATION_LABEL = {
    "email-confirm": "Automatic (email confirmation only)",
    "one-human-check": "One human check, then automatic",
    "one-captcha": "Automatic except one CAPTCHA click",
    "search-only": "Presence can be checked automatically",
    "human": "Needs the person",
    "blocked": "Blocked for bots",
    "defunct": "No longer operating",
    "unknown": "Not yet explored",
}


def load_brokers():
    out = []
    for path in sorted(BROKER_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        for b in data["brokers"]:
            b = dict(b)
            b["region"] = data["region"]
            out.append(b)
    return out


def load_state():
    if not STATE.exists():
        return {"requests": []}
    return json.loads(STATE.read_text())


def save_state(state):
    state["updated"] = dt.date.today().isoformat()
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")


def latest_by_id(state):
    return {r["broker_id"]: r for r in state["requests"]}  # later entries win


def cmd_init(_):
    for src, dst in ((PROFILE_EXAMPLE, PROFILE), (STATE_EXAMPLE, STATE)):
        if dst.exists():
            print(f"exists: {dst.relative_to(ROOT)}")
        else:
            dst.write_text(src.read_text())
            print(f"created: {dst.relative_to(ROOT)} (edit it, it is git-ignored)")


def cmd_fastpath(_):
    done = latest_by_id(load_state())
    rows = []
    for b in load_brokers():
        order = FASTPATH_ORDER.get(b.get("automation"))
        if order is None:
            continue
        if b["id"] in done and done[b["id"]]["status"] in ("submitted", "pending-email", "not-found"):
            continue
        rows.append((order, b))
    rows.sort(key=lambda r: (r[0], r[1]["name"]))
    if not rows:
        print("Nothing left on the fast path.")
        return
    print("Start here (easiest first):\n")
    for order, b in rows:
        print(f"{order}. {b['name']}  [{AUTOMATION_LABEL[b['automation']]}]")
        print(f"   {b.get('optout_url')}")
        if b.get("steps"):
            print(f"   {b['steps']}")
        print()


def cmd_mark(a):
    if a.status not in STATUSES:
        sys.exit(f"status must be one of: {', '.join(STATUSES)}")
    ids = {b["id"] for b in load_brokers()}
    if a.id not in ids:
        sys.exit(f"unknown broker id '{a.id}'. Add it to brokers/*.json first.")
    state = load_state()
    recheck = a.recheck or (dt.date.today() + dt.timedelta(days=91)).isoformat()
    state["requests"].append({
        "broker_id": a.id,
        "status": a.status,
        "date": dt.date.today().isoformat(),
        "email_used": a.email or "",
        "note": a.note or "",
        "recheck_after": recheck,
    })
    save_state(state)
    print(f"logged {a.id}: {a.status} (recheck {recheck})")


def buckets(brokers, done):
    counts = {k: 0 for k in STATUSES}
    counts["not-started"] = 0
    for b in brokers:
        r = done.get(b["id"])
        counts[r["status"] if r else "not-started"] += 1
    return counts


def cmd_status(_):
    brokers, done = load_brokers(), latest_by_id(load_state())
    c = buckets(brokers, done)
    print(f"{len(brokers)} brokers tracked")
    for k, n in c.items():
        label = STATUSES.get(k, "Not started")
        print(f"  {n:3d}  {k:14s} {label}")


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "person"


def cmd_report(a):
    if not PROFILE.exists():
        sys.exit("No profile yet. Run: removal.py init")
    profile = json.loads(PROFILE.read_text())
    brokers = load_brokers()
    done = latest_by_id(load_state())
    rows = []
    for b in brokers:
        r = done.get(b["id"], {})
        rows.append({
            "id": b["id"],
            "name": b["name"],
            "region": b["region"],
            "category": b.get("category", ""),
            "automation": b.get("automation", "unknown"),
            "url": b.get("optout_url") or b.get("search_url") or "",
            "status": r.get("status", "not-started"),
            "date": r.get("date", ""),
            "note": r.get("note", "") or b.get("notes", ""),
            "recheck_after": r.get("recheck_after", ""),
        })
    payload = {
        "person": profile.get("display_name", "Your report"),
        "generated": dt.date.today().isoformat(),
        "statuses": {**STATUSES, "not-started": "Not started"},
        "automation": AUTOMATION_LABEL,
        "rows": rows,
    }
    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.read_text().replace("{{TITLE}}", payload["person"]).replace("{{DATA_JSON}}", blob)
    REPORTS.mkdir(exist_ok=True)
    out = pathlib.Path(a.out) if a.out else REPORTS / f"{slug(payload['person'])}.html"
    out.write_text(html)
    print(f"wrote {out}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init").set_defaults(fn=cmd_init)
    sub.add_parser("fastpath").set_defaults(fn=cmd_fastpath)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    m = sub.add_parser("mark")
    m.add_argument("id")
    m.add_argument("status")
    m.add_argument("--note")
    m.add_argument("--email")
    m.add_argument("--recheck")
    m.set_defaults(fn=cmd_mark)
    r = sub.add_parser("report")
    r.add_argument("--out")
    r.set_defaults(fn=cmd_report)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
