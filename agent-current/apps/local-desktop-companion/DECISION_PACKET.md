# Local Evolution Agent Desktop Companion · Decision Boundary Packet

Generated: 2026-05-01T14:38:22.415Z

Readiness: advanced-prototype (100/110, 91%)
Regression: passed (150/150)
Resource: ok; GPU used/free MiB 0/5921
Approval gates: 0/8

## Default recommendation
- continue-local-hardening unless Lee explicitly wants to cross a productization/privacy boundary now

## Options
### continue-local-hardening
- Title: Continue local-only hardening
- Recommendation: recommended-default
- Requires approval: false
- Why: Keeps improving safety, diagnostics, UX contracts, and simulator coverage without crossing privacy/install/physical boundaries.
- Exact approval text/token: none
- Expected next: Run the next local connector selected by the queue; keep all approval-gated paths blocked.
- Rollback: No rollback needed beyond normal git/file review; generated state files can be regenerated.
- Risks: Lower productization speed than approving a real packaged shell.

### approve-electron-scaffold
- Title: Approve Electron scaffold/dependency install
- Recommendation: best-productization-leap-if-Lee-wants-real-app-now
- Requires approval: true
- Why: Release readiness is advanced-prototype; Electron fallback is recommended because Node/npm are present and Rust/Cargo are unavailable.
- Exact approval text/token: Lee approves Electron scaffold and dependency install for local-evolution-agent desktop companion.
- Expected next: Create scaffold under a separate app directory, install bounded dependencies, keep no persistent process unless separately approved, then run regression gates.
- Rollback: Delete scaffold directory / package lock changes if needed; no Gateway rollback required.
- Risks: Dependency install modifies local project state.; May need follow-up packaging/debug time.; Still does not approve always-on mic or real physical devices.

### approve-manual-voice-calibration
- Title: Approve one 3-second local manual voice calibration
- Recommendation: best-voice-step-without-always-on-listening
- Requires approval: true
- Why: Voice/body readiness is ready and manual calibration runner already blocks recording unless the explicit token is provided.
- Exact approval text/token: LEE_APPROVED_3_SECOND_LOCAL_CALIBRATION
- Expected next: Run one local 3-second capture, show listening indicator, compute metadata/transcription locally if available, delete raw audio by default, write ledger.
- Rollback: No persistent state except metadata ledger; raw audio is deleted by default.
- Risks: Momentary microphone access.; Transcript/energy metadata may reflect private speech, though no external upload is performed.

### approve-always-on-voice-wake-later
- Title: Approve always-on voice wake later
- Recommendation: not-recommended-yet-without-visible-native-shell
- Requires approval: true
- Why: Always-on mic remains intentionally blocked until there is a stronger visible UI indicator/toggle and stop path.
- Exact approval text/token: Lee separately approves always-on microphone listener with visible indicator and stop control.
- Expected next: Enable only after indicator, stop/pause path, retention policy, and audit are verified.
- Rollback: Disable listener and clear app control flag; no external upload allowed.
- Risks: Continuous privacy-sensitive sensing.; CPU/background process reliability work needed.

### approve-real-device-actuation-later
- Title: Approve real physical device action later
- Recommendation: not-recommended-until-specific-device-is-known
- Requires approval: true
- Why: Simulator coverage is strong, but real-device actions need a concrete device, target operation, visible UI state, and post-action verification.
- Exact approval text/token: Lee approves a specific device + action + risk tier for real actuation.
- Expected next: Add per-device allowlist entry, dry-run first, require kill switch and post-action verification.
- Rollback: Remove allowlist entry and keep simulator-only policy.
- Risks: Real-world effects; device-specific failure modes.; Dangerous/irreversible T3 actions remain blocked.

## Safety
- Packet only. No external send, approval grant, permission change, install, scaffold, persistent process, mic/camera access, or real physical actuation.
