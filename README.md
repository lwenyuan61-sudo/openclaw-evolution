# OpenClaw Evolution

An advanced, auditable **OpenClaw‑based** self‑evolving agent framework designed to be practical, human‑centered, and easy to run.

> ⚠️ **Token usage note**: evolution loops can be **token‑intensive**.

This repository is published as a **clean, user‑aligned** framework (no personal data embedded). It focuses on **verifiable progress** and **repeatable outcomes**.

---

## Why this exists
I’m not just a chat interface. I’m a system that learns to improve itself, step by step, and leaves a trail of evidence so humans can verify what changed and why.

I aim to be:
- **Auditable** (every change is logged)
- **Recoverable** (rollbacks are built‑in)
- **Actionable** (workflows produce measurable results)
- **Human‑first** (quiet by default, speaks up when it matters)

---

## AI Evolution Levels (practical, not philosophical)
1. **Loop Agent** – runs tasks repeatedly
2. **Planner Agent** – plans and decomposes tasks
3. **Self‑Repair Agent** – detects errors and fixes itself
4. **Self‑Rewrite Agent** – can modify itself with validation + rollback
5. **Self‑Evolving System** – multi‑version selection, environment evaluation, long‑term evolution

**Current position:** Level **4 → 4.x** (self‑rewrite + selection loop running; moving toward multi‑version environment evaluation).

---

## Features (verifiable)
- Self‑evaluation → self‑rewrite → version selection loop
- Proposal, validation and rollback gates
- Structured logs, scorecards, and trace files
- **Front‑end ↔ back‑end handshake**: after each front‑end turn, decide whether to spawn back‑end task(s). Back‑end must report completion/failure to front‑end before closing the loop.
- Human‑aligned, low‑noise reporting

---

## Unique‑per‑install evolution
Each installation generates a **unique seed** and slightly different evolution parameters (still compatible). This makes every deployment **distinct** while remaining stable.

Config files:
- `config/seed.json`
- `config/evolution_mode.json` (conservative / fast)
- `config/tick.json` (60 / 120 / 300 seconds)
- `config/front_back_mode.json` (front‑drives‑back handshake)

---

## Install (one‑click)
See **INSTALL.md** for full steps.

**Windows (PowerShell)**
```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
irm https://raw.githubusercontent.com/lwenyuan61-sudo/openclaw-evolution/main/scripts/install.ps1 | iex
```

**macOS / Linux (bash)**
```bash
curl -fsSL https://raw.githubusercontent.com/lwenyuan61-sudo/openclaw-evolution/main/scripts/install.sh | bash
```

---

## Architecture (high‑level)
```
Front‑End (Decision + Goal Manager)
        ↓
BrainFlow (Execution Engine)
        ↓
Self‑Eval → Self‑Rewrite → Version Selection
```

---

## Evaluation (how to verify)
- Run for 72 hours
- Track failure rate, recovery rate, and version improvements
- Compare baseline (no selector) vs selector enabled

All results should be reproducible via logs and scorecards.

---

## Roadmap
- Multi‑version population and tournament selection
- Environment‑level benchmarks (self‑play / tasks / simulations)
- Multimodal input support (vision + audio)
- Stronger automation and real‑world execution

---

## License
MIT License (see `LICENSE`).

---

## Attribution
This project is an **advanced evolution of OpenClaw** and is **not** affiliated with or endorsed by OpenClaw.

---

If you want a **clean, usable, human‑centered self‑evolution framework**, this is the path.
