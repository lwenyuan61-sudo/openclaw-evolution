
- `config/tick.json` (60 / 120 / 300 seconds)
- `config/front_back_mode.json` (front‑drives‑back handshake)

---

## Controlled Front↔Back Mode
The system runs in **front‑drives‑back** mode by default. After each front‑end turn, it decides whether to spawn a back‑end task. The back‑end must report completion/failure to the front‑end before the loop closes. This ensures **stronger capability without runaway noise**.

You can change this behavior via:
- `config/front_back_mode.json`

---

## High Token Cost Notice
Evolution loops can be **token‑intensive**. If cost is a concern, increase tick seconds or switch to conservative mode.
