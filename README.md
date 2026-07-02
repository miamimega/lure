# Lure

[![Live demo](https://img.shields.io/badge/live%20demo-lure.fullpercent.io-00d4aa)](https://lure.fullpercent.io)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org)
[![Star on GitHub](https://img.shields.io/github/stars/miamimega/lure?style=social)](https://github.com/miamimega/lure/stargazers)

**Ad copy that learns which hooks actually catch.**

You cast a batch of hooks, tie on the ones you'll actually run, log the real numbers, and a per-channel **Tacklebox** learns which patterns win. The next cast is sharper. Every hook is a lure — this makes better lures from *your* results.

```
cast  ->  run  ->  catch  ->  learn  ->  cast (sharper)  ->  ...
```

### 🔗 Play with it right now (no install): **[lure.fullpercent.io](https://lure.fullpercent.io)**

The live demo casts real hooks from a local open model (Llama 3.2, self-hosted — not a paid API), lets you tie on the ones you'd use, log results, and watch the next cast lean into what caught. Everything you do there stays in your browser.

---

## What makes it different

Most "AI ad copy" tools are a fancy prompt box: they forget everything the second you close the tab. Lure keeps a **learning memory** — a **Tacklebox** per channel. It ships with a researched seed tacklebox of **Keepers** (patterns that lift results) and **Throwbacks** (phrases that get flagged or flop), plus house rules — so it's useful on day one. Then it grows a second tacklebox from *your* logged results and steers every future cast with it.

It knows four channels out of the box: **email**, **Meta / Facebook**, **Google Ads**, and **affiliate**.

> Want it to *close* the loop for you — pull your real numbers automatically, unlock more channels, run on stronger models, and share it with a team? That's **Lure Pro (hosted)**. The open-source version below always stays free. See [**Free vs Lure Pro**](#free-vs-lure-pro).

---

## The workflow (four tabs, one loop)

The app speaks fishing on purpose — every term maps cleaner than the generic label did.

| Tab | What it does |
|---|---|
| **Cast** | Pick a channel + offer, generate hooks that lean on proven Keepers and refuse known Throwbacks |
| **In the Water** | The hooks you've **tied on** — with the date and channel(s) you ran them on |
| **The Catch** | Log each hook's result, **1–100**, on the metric you live by |
| **Tacklebox** | Your learned memory: **Keepers** it leans into, **Throwbacks** it drops |

**The loop:** Cast → tie on the ones you'll run → log the catch → the Tacklebox learns → cast again, sharper.

### How to log a catch (do this part right)

There's no universal scale — **1–100 is relative to *your* numbers.**

- **80–100** = a Keeper you'd scale
- **40–70** = middling
- **1–30** = a Throwback you'd cut

Pick whatever metric is your guiding light:

| Metric | Meaning |
|---|---|
| **EPC** | Earnings per click (affiliate) |
| **CTR** | Click-through rate = clicks ÷ impressions |
| **CVR** | Conversion rate = conversions ÷ clicks |
| **ROAS** | Return on ad spend = revenue ÷ spend |
| **CPA / CPL** | Cost per acquisition / lead (lower is better) |
| **Open / Reply rate** | Email |
| **Custom** | Whatever number you actually trust |

High scores teach the Tacklebox what wins; low scores teach it what to avoid. The demo ships seeded with a few Keepers and Throwbacks so the loop has something to learn from immediately — hit **Empty the tacklebox** to wipe them and start from your own data.

---

## Run it yourself (the CLI)

Watch the loop learn with zero setup and no API key:

```bash
python3 lure.py demo --segment meta_facebook
```

See what it ships with:

```bash
python3 lure.py segments                        # the channels it knows
python3 lure.py playbook --segment meta_facebook # the proven Keepers + Throwbacks + rules
```

---

## Cast with a real LLM (three ways)

The live demo runs a local model. You can do exactly the same, or use an API key.

### A) Local model with Ollama — free, private (this is what the live demo runs)

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:3b            # fast + clean — what lure.fullpercent.io runs
# alternatives:  ollama pull glm4:9b   (heavier)  ·  ollama pull qwen2.5:7b

export LURE_MODEL=llama3.2:3b
python3 lure.py generate "10-minute meal kits for busy parents" --segment meta_facebook -n 8
```

### B) An API key (Anthropic or OpenAI)

```bash
export ANTHROPIC_API_KEY=...        # or OPENAI_API_KEY=...
python3 lure.py generate "your offer" --segment email -n 8
```

### C) The web demo with your own model — Docker

The whole playable demo, self-hosted, one command:

```bash
docker compose up          # brings up Ollama + the Lure proxy + the demo on http://localhost:8080
```

`docker-compose.yml` runs a local model via Ollama and serves the demo — your Keepers never leave your machine. `deploy/lure_llm.py` is the tiny (~150-line, stdlib-only) proxy the live site runs.

Lure feeds the model the proven Keepers (as spirit), forbids the Throwbacks (twice — in the prompt and a hard output filter), and applies the house rules.

---

## Grow your own Tacklebox

```bash
python3 lure.py score results.csv --segment email      # csv: hook,score(1-100) -> top third become Keepers, bottom third Throwbacks
python3 lure.py add-winner --segment email "Your trial ends tonight"    # a Keeper
python3 lure.py add-loser  --segment email "act now"                    # a Throwback
python3 lure.py add-rule   --segment email "Never imply you know a personal attribute"
```

Your additions live in `playbook.json` (plain JSON — edit it directly) and blend with the seed tacklebox on every cast.

---

## How each marketer uses it

- **Email**: subject lines varying the mechanism (curiosity vs number vs question vs benefit) + preview text. Log on open / reply rate.
- **Meta / Facebook**: 10–20 primary-text hooks front-loaded to the first 125 characters, varied mechanism. Log on CPA / thumb-stop. Policy-rejection phrasing is auto-refused.
- **Google Ads**: 8–10 non-overlapping RSA headlines across types (USP, benefit, CTA, price, proof), no near-duplicates. Log on CVR / CTR; Ad Strength is the leading indicator.
- **Affiliate**: a core angle plus mini-angles and advertorial/listicle hooks. Week 1: cast 10–20 hooks on one offer to find the Keepers. Log on EPC.

---

## Free vs Lure Pro

**This repo is the free, open-source, MIT version — and it stays that way.** It runs the whole loop: four channels, the Tacklebox, a local model *or your own API key*, self-hosted, your data never leaving your machine.

**Lure Pro** is the hosted, automated layer on top. The one that matters: **it closes the loop for you.** Instead of typing scores by hand, Pro pulls your *real* CTR / EPC / ROAS / CPA straight from your ad and affiliate accounts and auto-scores every hook — the metric lands back on the exact hook that earned it, matched by a stamped tracking key.

| Capability | Free — MIT, self-host | Lure Pro — hosted |
|---|---|---|
| **Channels** | 4 (Email, Meta/Facebook, Google Ads, Affiliate) | 10 (+ SMS, Native, TikTok/Reels, YouTube/VSL, Landing, Advertorial) |
| **The full loop + Tacklebox** | ✅ Full — cast → tie on → catch → learn | ✅ Full — same loop, shared across the team |
| **Hook scoring** | Manual (you enter 1–100) | **Automatic** from real CTR / EPC / ROAS / CPA |
| **Ad + affiliate integrations** | — | Meta, Google, TikTok **+ 8 affiliate networks** |
| **AI model** | Local model (Ollama / Llama 3.2) or your own API key | **Anthropic Claude (Sonnet) + OpenAI (GPT-4o class)**, managed — local fallback |
| **Storage & privacy** | Browser-only / self-host — data stays with you | Managed hosted app + API, cross-device sync |
| **Teams & roles** | Single user | Multi-seat (owner / admin / agent) |
| **Deploy** | Docker one-command self-host | Hosted, nothing to run |
| **License / price** | MIT, free forever | Waitlist — pricing TBA |

**Auto-scoring pulls from real reporting APIs:**

- **Ad platforms** — Meta Ads, Google Ads, TikTok Ads
- **Affiliate networks (8)** — Everflow, Offer18, TUNE (HasOffers), ClickBank, CAKE, Impact.com, CJ Affiliate, Rakuten Advertising (plus a generic S2S postback for any other network)

**Sharper models on Pro & Hosted.** The free version already lets you plug in your own Anthropic or OpenAI key (see [Cast with a real LLM](#cast-with-a-real-llm-three-ways)). **Lure Pro runs those premium models for you** — Anthropic Claude (Sonnet) and OpenAI (GPT-4o class) — with the same prompt discipline and the local model as a fallback. No keys to wrangle, nothing to host.

Free stays generous and open source. Pro is the automation layer on top — it never takes features away.

👉 **[Join the Lure Pro waitlist](mailto:stephen@fullpercent.io?subject=Lure%20Pro%20waitlist)** — pricing isn't set yet, no card, just early access.

---

## The guardrails (don't skip)

1. **The check is real performance, not vibes.** Score is a number you actually trust.
2. **There is a stop.** Cap spend per round before you scale a Keeper.
3. **There is a human gate.** Nothing here auto-spends or auto-publishes. For regulated offers, you review for compliance every time.

## Make it yours

It's a pattern, not a product. Add a segment to `seed_playbook.json`, change the scoring to your niche's metric, or point the loop at SMS templates, landing-page headlines, video hooks — anything you can test and score.

---

## ⭐ Star it

If Lure is useful, **[star the repo](https://github.com/miamimega/lure)** — it's the one thing that helps other marketers find it. Found a bug or want a channel added? Open an issue.

Built by **Stephen "MEGA" Ventura** · [FullPercent.io](https://fullpercent.io) · MIT licensed, use it however you like.
