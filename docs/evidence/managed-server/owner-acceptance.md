# Owner-run managed-server acceptance

Provenance: owner-run native Termux acceptance, supported by the supplied
transcript and the owner's explicit confirmation of starting-shell survival
and same-conversation resume, as recorded in the release-preparation handoff.
This file is a summary of that supplied evidence, not a raw transcript or an
automated execution log. No real-account tests were rerun to prepare this record.
No credentials, tokens, private prompts, or conversation identifiers are copied.

- Completed: September 26, 2026, America/Los_Angeles (September 27 UTC).
- Runtime: Codex CLI **0.157.1**, using the existing ChatGPT login.
- Candidate: corrected managed-app-server feature, wrapper VERSION **0.3.1**.
- Branch: `feat/managed-app-server`.
- Base HEAD: `60da03eb3078b19cab2c438f25f21ecd08878f4d`, plus uncommitted changes.
- Reviewed wrapper artifact SHA-256:
  `4ffb5a7cc1d0ee51678bb00951c7598dddc6832df1f867def9a674e2e3d0efde`.
- Candidate source identities: [verification.json](verification.json).

| Owner-confirmed action | Result |
| --- | --- |
| Managed server start and authenticated status | Succeeded |
| Connect with existing ChatGPT login | Produced real model responses |
| Actual `pwd` execution | Returned `/data/data/com.termux/files/home/repos/codex-termux` |
| Deliberate client exit | Managed server remained available |
| Close starting shell and open another | Authenticated connectivity survived; explicitly confirmed by owner |
| Explicit resume | Restored the original conversation and answered another request; explicitly confirmed by owner |
| Ctrl+C during a response | Interrupted the response; a subsequent request succeeded |
| Fork | Preserved conversation history and answered another request |
| `manage server stop` | Reported that the server and proxy stopped |
| Subsequent status | Reported `Server stopped` |

Both review fixes were present: malformed control authentication proofs are
rejected safely, and connect arguments after Codex's delimiter are preserved.
The acceptance above applies to the recorded 0.3.1 feature candidate, not the
later regenerated 0.4.0 artifact. The version bump and offline 0.4.0 checks are
recorded separately in [VALIDATION.md](../../../VALIDATION.md).

This establishes the reported interactive workflow on the owner's native device.
It does not establish force-stop/reboot survival, Android battery-pressure
longevity, automatic stale-state recovery, live custom-provider switching, or
multi-client same-conversation coordination. The upstream Unix-socket daemon
remains unrepaired; the feature is an opt-in managed WebSocket workaround.
