# BrainFlow Self-Rewrite (Level-4) – Scaffolding

This folder is the **runway** for upgrading from **Self-repair agent (L3)** to **Self-rewrite agent (L4)**.

## Principles

- **Proposal-first**: changes are written as a proposal (with diff/patch) before being applied.
- **Measurable verification**: each proposal must define a check ("how we know it worked").
- **Rollback-ready**: always provide a revert path.
- **Shadow mode preferred**: run new logic in parallel and compare metrics before switching.

## Folder structure

- `proposals/` – pending proposals (one folder per proposal)
- `applied/` – archived applied proposals
- `rejected/` – archived rejected proposals

## Proposal template (minimum)

Each proposal folder should include:

- `proposal.md`
  - Goal
  - Risk & blast radius
  - Files touched
  - Rollback plan
  - Verification plan (commands + expected outputs)

- `patch.diff` (or `patch.ps1`)

## Safety gates

A proposal can be applied only if:

1. It has a rollback plan
2. It has a verification plan
3. It passes a dry-run / shadow run (when applicable)
