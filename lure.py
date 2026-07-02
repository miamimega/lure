#!/usr/bin/env python3
"""
lure: ad copy that learns from your own results.

A tiny, readable example of "loop engineering" plus a learning memory:

    generate  ->  run  ->  score  ->  learn  ->  generate (sharper)  ->  ...

It ships with a real SEED PLAYBOOK: researched, proven ad-hook WINNERS, known
LOSERS (phrases that get flagged or flop), and HOUSE RULES for four channels
(email, meta_facebook, google_ads, affiliate). So it is useful on day one.
Then YOU grow your own playbook on top of it from your real numbers.

QUICK START
-----------
  python3 lure.py demo                         # watch the loop learn, no API key
  python3 lure.py playbook --segment meta_facebook  # see the proven winners + losers it ships with
  python3 lure.py segments                      # list channels

USE IT FOR REAL
---------------
  export ANTHROPIC_API_KEY=...        (or OPENAI_API_KEY=...)
  python3 lure.py generate "10-minute meal kits for busy parents" --segment email -n 8
  # run those, then score them and grow your playbook:
  python3 lure.py score pending.csv --segment email
  # add your own hard-won knowledge any time:
  python3 lure.py add-winner --segment email "Your trial ends tonight"
  python3 lure.py add-loser  --segment email "act now"
  python3 lure.py add-rule   --segment email "Never imply you know a personal attribute"

GUARDRAILS: the check is real performance, there is a stop, and a human gate.
Nothing here auto-spends or auto-publishes. You approve what goes live.

  Live demo:  https://lure.fullpercent.io
  Source:     https://github.com/miamimega/lure
  Built by Stephen Ventura  ·  https://fullpercent.io   ·   MIT
"""

import argparse, csv, json, os, random, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SEED_PATH = os.path.join(HERE, "seed_playbook.json")
PLAYBOOK_PATH = os.environ.get("LURE_PLAYBOOK", "playbook.json")  # YOUR playbook, grows over time

# ---------------------------------------------------------------------------
# Seed playbook (ships with lure). Real researched winners/losers/rules per
# channel. Read-only reference. Open seed_playbook.json and read it, it is plain.
# ---------------------------------------------------------------------------
def load_seed():
    try:
        return json.load(open(SEED_PATH)).get("segments", {})
    except Exception:
        return {}

# ---------------------------------------------------------------------------
# Your playbook (playbook.json). Per segment: winners you have proven, losers you
# have learned to avoid, and house rules you set. Grows from score + add-*.
# ---------------------------------------------------------------------------
def load_playbook():
    return json.load(open(PLAYBOOK_PATH)) if os.path.exists(PLAYBOOK_PATH) else {}

def save_playbook(b):
    json.dump(b, open(PLAYBOOK_PATH, "w"), indent=2)

def user_seg(playbook, seg):
    return playbook.setdefault(seg, {"winners": [], "losers": [], "houseRules": []})

def merged(seg):
    """Seed + your own, flattened to plain strings for prompting."""
    seed = load_seed().get(seg, {})
    you = load_playbook().get(seg, {})
    win = [w.get("example") or w.get("pattern") for w in seed.get("winners", [])]
    win += [w.get("text") for w in you.get("winners", []) if w.get("text")]
    los = [l.get("avoid") or l.get("text") for l in seed.get("losers", [])]
    los += [l.get("text") for l in you.get("losers", []) if l.get("text")]
    rules = list(seed.get("houseRules", [])) + list(you.get("houseRules", []))
    return {"winners": [w for w in win if w], "losers": [l for l in los if l], "houseRules": rules}

def contains_loser(angle, losers):
    a = angle.lower()
    for entry in losers:
        for phrase in re.split(r"[;,]", entry):
            phrase = phrase.strip().lower()
            if len(phrase) >= 4 and phrase in a:
                return phrase
    return None

# ---------------------------------------------------------------------------
# Generation. Real mode feeds the merged playbook (winners as spirit, losers as
# do-not, house rules) to an LLM, then HARD-FILTERS any output that slips a
# known loser through. The negative examples are enforced twice.
# ---------------------------------------------------------------------------
def generate_llm(offer, n, m, seg):
    label = seg.replace("_", " ")
    win = "\n".join(f"- {w}" for w in m["winners"][:10]) or "(none yet)"
    los = "; ".join(m["losers"][:24]) or "(none yet)"
    rules = "\n".join(f"- {r}" for r in m["houseRules"][:8]) or "(none yet)"
    prompt = (
        f"You write high-performing {label} ad copy.\nOffer: {offer}\n\n"
        f"WRITE IN THE SPIRIT OF THESE PROVEN WINNERS (do not copy them verbatim):\n{win}\n\n"
        f"NEVER use these losing phrases, words, or patterns:\n{los}\n\n"
        f"HOUSE RULES:\n{rules}\n\n"
        f"Write {n} fresh, distinct {label} hooks. Vary the mechanism (curiosity, "
        f"number, question, benefit). One per line, no numbering."
    )
    text = _call_model(prompt)
    out = [re.sub(r"^[\-\*\d\.\)\s]+", "", ln).strip() for ln in text.splitlines() if ln.strip()]
    clean = [a for a in out if a and not contains_loser(a, m["losers"])]
    return clean[:n]

def _call_model(prompt):
    # Local model via Ollama: `export LURE_MODEL=llama3.2:3b` (free, private, no key).
    # This is what the live demo at lure.fullpercent.io runs.
    model = os.environ.get("LURE_MODEL", "")
    if model and not model.startswith(("claude", "gpt")):
        import urllib.request
        host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
        if model.startswith("qwen3"):
            prompt += " /no_think"   # Qwen3 is a thinking model; answer directly
        body = json.dumps({"model": model, "prompt": prompt, "stream": False,
                           "options": {"num_predict": 400, "temperature": 0.85}}).encode()
        req = urllib.request.Request(host + "/api/generate", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode()).get("response", "")
    if os.environ.get("ANTHROPIC_API_KEY"):
        import anthropic
        c = anthropic.Anthropic()
        msg = c.messages.create(model="claude-sonnet-4-6", max_tokens=700,
                                messages=[{"role": "user", "content": prompt}])
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    if os.environ.get("OPENAI_API_KEY"):
        from openai import OpenAI
        r = OpenAI().chat.completions.create(model="gpt-4o-mini",
                                             messages=[{"role": "user", "content": prompt}])
        return r.choices[0].message.content
    raise SystemExit("generate needs a model. Pick one:\n"
                     "  local:  export LURE_MODEL=llama3.2:3b   (free, via Ollama)\n"
                     "  api:    export ANTHROPIC_API_KEY=...       (or OPENAI_API_KEY=...)\n"
                     "No setup? Run `python3 lure.py demo` to watch the loop learn for free.")

# ---------------------------------------------------------------------------
# Demo: a self-contained showcase of the loop, no key, no spend. The synthetic
# audience rewards the same mechanisms the real research found win (numbers,
# curiosity, benefit), so you watch the average climb as the playbook learns.
# ---------------------------------------------------------------------------
CURIOSITY = ["that nobody tells you", "before you waste another week", "the mistake to avoid first"]
BENEFIT = ["and cut the busywork", "and save real hours", "without the prep"]
CUR_DET = ["without", "even if", "the mistake", "stop", "nobody tells you", "the truth about", "before you"]
BEN_DET = ["save", "faster", "in minutes", "more", "double", "cut", "free up", "finally"]
NUMP = ["3 ways to", "5 reasons to", "7 quick wins for", "the 30-second fix for"]
KEYS = ["has_number", "is_question", "is_short", "has_curiosity", "has_benefit"]

def features(a):
    l = a.lower()
    return {"has_number": bool(re.search(r"\d", a)), "is_question": a.strip().endswith("?"),
            "is_short": len(a.split()) <= 11, "has_curiosity": any(w in l for w in CUR_DET),
            "has_benefit": any(w in l for w in BEN_DET)}

def demo_score(a):
    f = features(a); s = 35.0
    s += 22 if f["has_number"] else 0
    s += 20 if f["has_curiosity"] else 0
    s += 14 if f["has_benefit"] else 0
    s += 6 if f["is_question"] else 0
    return max(0, min(100, s + random.uniform(-5, 5)))

def gen_demo(offer, n, w):
    subj = offer.strip().rstrip("."); sl = subj[0].lower() + subj[1:]
    cores = [subj, f"the easy way to {sl}", f"a smarter way to {sl}", f"{subj}, done right", f"rethinking {sl}"]
    out, seen, t = [], set(), 0
    while len(out) < n and t < n * 15:
        t += 1
        c = random.choice(cores)
        a = f"{random.choice(NUMP)} {c[0].lower()+c[1:]}" if random.random() < w["has_number"] else c
        if random.random() < max(w["has_benefit"], w["has_curiosity"]):
            a = f"{a} {random.choice(CURIOSITY if w['has_curiosity'] >= w['has_benefit'] else BENEFIT)}"
        if random.random() < w["is_question"]:
            a = a.rstrip(".") + "?"
        a = a[0].upper() + a[1:]
        if len(a.split()) <= 14 and a.lower() not in seen:
            seen.add(a.lower()); out.append(a)
    return out

def learn_weights(scored, keep=0.5):
    ranked = sorted(scored, key=lambda x: x[1], reverse=True)
    win = [a for a, _ in ranked[:max(1, int(len(ranked) * keep))]]
    return {k: round(sum(1 for a in win if features(a)[k]) / len(win), 3) for k in KEYS}

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def cmd_segments(a):
    print("\nsegments (channels) lure ships a seed playbook for:")
    for s in load_seed(): print("  -", s)
    print("\nuse with: generate / playbook / score / add-* --segment <name>\n")

def cmd_playbook(a):
    seg = a.segment
    seed = load_seed().get(seg)
    if not seed:
        sys.exit(f"unknown segment '{seg}'. run: python3 lure.py segments")
    you = load_playbook().get(seg, {})
    print(f"\n=== playbook for {seg} ===")
    print("\nWINNERS (proven hook patterns):")
    for w in seed.get("winners", [])[:10]:
        print(f"  + {w.get('pattern','')}\n      e.g. \"{w.get('example','')}\"")
    for w in you.get("winners", []): print(f"  + (yours) \"{w.get('text','')}\"  [{w.get('score','')}]")
    print("\nLOSERS (avoid these):")
    for l in seed.get("losers", [])[:10]: print(f"  - {l.get('avoid','')}")
    for l in you.get("losers", []): print(f"  - (yours) {l.get('text','')}")
    print("\nHOUSE RULES:")
    for r in (seed.get("houseRules", []) + you.get("houseRules", [])): print(f"  * {r}")
    print()

def cmd_generate(a):
    if a.segment not in load_seed():
        sys.exit(f"unknown segment '{a.segment}'. run: python3 lure.py segments")
    m = merged(a.segment)
    angles = generate_llm(a.offer, a.n, m, a.segment)
    print(f"\n{len(angles)} {a.segment} hooks for: {a.offer}")
    print(f"(used {len(m['winners'])} winners, forbade {len(m['losers'])} losers, {len(m['houseRules'])} house rules)\n")
    for x in angles: print(f"  - {x}")
    with open("pending.csv", "w", newline="") as f:
        wr = csv.writer(f); wr.writerow(["angle", "score"])
        for x in angles: wr.writerow([x, ""])
    print("\nwrote pending.csv. run them, fill in the score column, then:")
    print(f"  python3 lure.py score pending.csv --segment {a.segment}\n")

def cmd_score(a):
    scored = []
    with open(a.csv) as f:
        for row in csv.DictReader(f):
            if (row.get("score") or "").strip():
                try: scored.append((row["angle"].strip(), float(row["score"])))
                except ValueError: pass
    if not scored: sys.exit("no scored rows. csv needs columns: angle,score (score filled in).")
    ranked = sorted(scored, key=lambda x: x[1], reverse=True)
    third = max(1, len(ranked) // 3)
    playbook = load_playbook(); us = user_seg(playbook, a.segment)
    for ang, sc in ranked[:third]: us["winners"].append({"text": ang, "score": round(sc, 1)})
    for ang, sc in ranked[-third:]: us["losers"].append({"text": ang})
    us["winners"] = sorted(us["winners"], key=lambda w: w.get("score", 0), reverse=True)[:30]
    save_playbook(playbook)
    print(f"\nlearned from {len(scored)} results for {a.segment}.")
    print(f"  + {third} new winner(s), - {third} new loser(s) added to YOUR playbook ({PLAYBOOK_PATH}).")
    print("  your next `generate` blends these with the seed playbook.\n")

def _add(a, key, value):
    playbook = load_playbook(); us = user_seg(playbook, a.segment)
    us[key].append({"text": value} if key != "houseRules" else value)
    save_playbook(playbook)
    kind = {"winners": "winner", "losers": "loser", "houseRules": "house rule"}[key]
    print(f"added {kind} to your {a.segment} playbook: \"{value}\"")

def cmd_add_winner(a): _add(a, "winners", a.text)
def cmd_add_loser(a):  _add(a, "losers", a.text)
def cmd_add_rule(a):   _add(a, "houseRules", a.text)

def cmd_demo(a):
    seg = a.segment if a.segment in load_seed() else "email"
    seed = load_seed().get(seg, {})
    offer = a.offer or "meal kits for busy parents"
    print(f"\nlure demo  ·  segment: {seg}  ·  offer: {offer}\n" + "-" * 56)
    print(f"seed playbook loaded: {len(seed.get('winners',[]))} proven winners, "
          f"{len(seed.get('losers',[]))} known losers, {len(seed.get('houseRules',[]))} house rules.")
    if seed.get("losers"):
        print(f"e.g. it already knows to avoid: {seed['losers'][0].get('avoid','')[:60]}")
    print("-" * 56)
    w = {k: 0.2 for k in KEYS}
    first = last = 0.0
    for rnd in range(1, a.rounds + 1):
        scored = [(x, demo_score(x)) for x in gen_demo(offer, a.n, w)]
        avg = sum(s for _, s in scored) / len(scored)
        best = max(scored, key=lambda x: x[1])
        print(f"round {rnd}: avg {avg:5.1f}   best: \"{best[0]}\" ({best[1]:.0f})")
        if rnd == 1: first = avg
        last = avg; w = learn_weights(scored)
    print("-" * 56)
    print(f"avg climbed {last-first:+.0f} points. the loop learned which hooks win and aimed there.")
    print("the real tool feeds the seed winners to the model and forbids the losers.")
    print("live demo: https://lure.fullpercent.io   code: https://github.com/miamimega/lure\n")

def main():
    p = argparse.ArgumentParser(description="ad copy that learns from your own results")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("demo", help="watch the loop learn, no API key")
    d.add_argument("offer", nargs="?", default=None); d.add_argument("--segment", default="email")
    d.add_argument("-n", type=int, default=8); d.add_argument("--rounds", type=int, default=5)
    d.set_defaults(func=cmd_demo)

    g = sub.add_parser("generate", help="generate hooks (uses your key + seed playbook + your playbook)")
    g.add_argument("offer"); g.add_argument("--segment", required=True); g.add_argument("-n", type=int, default=8)
    g.set_defaults(func=cmd_generate)

    s = sub.add_parser("score", help="feed results back (csv: angle,score) to grow your playbook")
    s.add_argument("csv"); s.add_argument("--segment", required=True); s.set_defaults(func=cmd_score)

    for name, fn, helptext in [("add-winner", cmd_add_winner, "add a winning hook you have proven"),
                               ("add-loser", cmd_add_loser, "add a losing phrase/word to avoid"),
                               ("add-rule", cmd_add_rule, "add a house rule")]:
        ap = sub.add_parser(name, help=helptext)
        ap.add_argument("text"); ap.add_argument("--segment", required=True); ap.set_defaults(func=fn)

    b = sub.add_parser("playbook", help="show the seed + your winners/losers/rules for a segment")
    b.add_argument("--segment", required=True); b.set_defaults(func=cmd_playbook)

    sub.add_parser("segments", help="list the channels lure ships a playbook for").set_defaults(func=cmd_segments)

    args = p.parse_args(); args.func(args)

if __name__ == "__main__":
    main()
