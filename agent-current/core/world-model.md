# World Model Layer

Purpose: turn raw state files into a small predictive belief layer before choosing actions.

This is inspired by the world-model direction Lee asked about: useful intelligence should not only react to text, but maintain a compact model of current state, likely future state, action consequences, and verification signals.

## Role in the control plane

`world-state -> predictions -> action candidates -> expected outcome -> verification -> learning`

The world model does **not** replace S2 deliberation. It is a low-cost S1/S2 bridge:

- summarize current belief from self / perception / action / continuity / goals
- predict likely near-future risks or opportunities
- estimate which action candidates are worth trying
- state what evidence would verify or falsify the prediction
- write a compact `core/world-state.json` snapshot for later wakes

## Boundaries

- No external action by itself.
- No irreversible action by itself.
- Predictions are hypotheses, not facts.
- If uncertainty or stakes are high, route to S2 deliberation.
- If action affects reality, pass through `core/reality-bridge.md` and `core/scripts/reality_action.py`.

## Current minimal implementation

`core/scripts/world_model_tick.py` reads:

- `core/self-state.json`
- `core/perception-state.json`
- `core/action-state.json`
- `core/learning-state.json`
- `core/procedural-memory.json`
- `autonomy/continuity-state.json`
- `autonomy/goal-register.json`
- `autonomy/upgrade-state.json`
- `state/resident_reflection.json`
- `state/lee_opportunity_review.json`

It writes:

- `core/world-state.json`

The first version is deliberately simple and interpretable. It is a connector, not a neural JEPA model.
