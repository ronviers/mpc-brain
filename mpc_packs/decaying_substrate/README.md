# decaying_substrate — transitional shim

**Transitional shim. Replace in S6 with a first-class pack when the kernel carve-out lands.**

Re-exports `DecayingSubstrate` from `mpc_session3` unchanged. No new
behaviour. No new mutations. This pack exists to give the `mpc_packs/`
namespace a stable import path for the session-3 substrate ahead of the
Session 6 kernel carve-out.

## Declared dependencies

- `mpc_session3.DecayingSubstrate`

## Declared mutations

None (pure re-export).
