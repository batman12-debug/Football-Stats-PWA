# Pin Live Score — Design Spec

**Date:** 2026-07-15  
**Product:** CheckBoard (World Cup 2026)  
**Status:** Approved for planning  

## Summary

Add Google-style **pin live score**: a persistent, quietly updating system notification for a chosen match, backed by an unlimited on-device pin queue. No PWA install required. True iPhone Dynamic Island support is Phase 2 via a native Live Activity companion that reuses the same queue and live-stats API.

## Goals

- Let users pin any fixture before kickoff; it becomes the live score surface when the match starts.
- Unlimited ordered personal queue; on full time, auto-advance to the next queued match or clear if empty.
- Quiet score updates only (no push banners / sounds for goals).
- Reuse existing backend live data; minimal server work in Phase 1.
- Design the queue contract so Phase 2 Dynamic Island can attach without rewriting pin UX.

## Non-goals (Phase 1)

- PWA “Add to Home Screen” / installable app requirement.
- Floating Document PiP mini-window.
- Server-synced pins across devices (no accounts).
- Goal / red-card push alerts.
- Native Dynamic Island / Lock Screen Live Activity (Phase 2 only).
- Android home-screen widgets as a primary surface.

## Approved decisions

| Topic | Choice |
| --- | --- |
| Delivery | Phase 1 web notification pin; Phase 2 native Live Activity |
| What to pin | Specific match, including before kickoff |
| After FT | Auto-switch to next queued match; else clear |
| Queue size | Unlimited ordered list |
| Alerts | Quiet score updates only |
| Install | Not required (notification-style pin like Google) |
| Backend | Reuse `GET /api/matches/{id}/live-stats`; no new score APIs |

## Phase 1 — Product surface

### Pin controls

- Pin / unpin on **match cards** and **match detail**.
- Visual: muted when off, brand win-green when on.
- Interaction: press feedback `scale(0.97)` ~160ms ease-out; animate only transform/opacity (no `transition: all`).
- First pin triggers the browser **notification permission** prompt (not on page load).

### Queue

- Ordered list of fixture IDs stored on-device (default: `localStorage`; migrate to IndexedDB only if size/perf requires it).
- Unlimited length; UI provides a sheet/drawer to reorder and unpin.
- Pinning an already-queued match is a no-op.
- **Active match** = first item in queue order while its status is upcoming (NS) or live.
- **FT advance:** when the active match reports full time, update the notification to the final score on that poll, remove that fixture from the queue, then set active to the new head (or close the notification if the queue is empty).

### Notification

- At most **one** system notification representing the **active** match (not one per queued item).
- Content patterns:
  - Upcoming: team codes / names + kickoff time + “Upcoming”
  - Live: e.g. `FRA 1–0 ESP · 67'`
  - FT: show final briefly, then advance or dismiss
- Tap opens `/match/{id}`.
- Updates are quiet (replace notification body; no noisy banner policy beyond platform defaults for updates).

### Platform honesty

- **Android Chrome:** primary Phase 1 target for Google-like persistent notification updates.
- **iOS Safari:** ongoing web notification updates are limited; Phase 1 still maintains in-app pinned/queue state and best-effort notifications; copy sets expectation that Lock Screen / Dynamic Island arrive in Phase 2.

## Architecture

```text
Match card / detail ──pin/unpin──► PinQueue (on-device)
                                      │
                                      ▼
                              Active fixture resolver
                                      │
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
         poll live-stats API                 Notification controller
         /api/matches/{id}/live-stats        (permission + show/update/close)
                    │
                    ▼
              FT → advance queue → update or clear notification
```

### Client modules (conceptual)

1. **`pin-queue`** — CRUD + order for fixture IDs; persistence.
2. **`pin-active`** — resolve active ID from queue + fixture status.
3. **`live-score-notification`** — permission, show/update/close; formats body from live-stats.
4. **`pin-ui`** — pin button, queue sheet; Emil motion rules.

Polling reuses the existing frontend live-stats fetch path (same source as `LiveMatchStatsPanel`).

### Backend

- **No new score endpoints** for Phase 1.
- Gain: reuse `live-stats` / match detail; no Redis writes for pins; no auth for pinning.
- Optional later: account-backed queue sync; server push (out of scope).

## Error & edge cases

| Case | Behavior |
| --- | --- |
| Permission denied | Keep queue; show in-app pinned state + enable-notifications hint |
| Permission revoked later | Keep queue; stop notification updates |
| Poll / network failure | Keep last known score in notification; do not unpin |
| Upcoming (NS) | Show kickoff / Upcoming; no fabricated score |
| Duplicate pin | No-op |
| Empty queue after FT | Close notification; empty state in queue UI |
| Unsupported / weak browser | Queue + in-app pin still work; notification best-effort |

## Phase 2 — Dynamic Island (sketch only)

- Thin native iOS companion (ActivityKit Live Activity).
- Same fixture IDs / queue semantics; score from same `live-stats` API.
- Dynamic Island + Lock Screen for the active match.
- Web Phase 1 must not claim Island support in UI copy.

## UI craft checklist (Emil)

- Pressable pin: `scale(0.97)` on `:active`, ~100–160ms ease-out.
- Prefer CSS transitions on transform/opacity over keyframes for pin toggles.
- Gate hover effects with `@media (hover: hover) and (pointer: fine)`.
- Respect `prefers-reduced-motion`.
- Queue sheet: one job — manage pins; avoid decorative card clutter.

## Testing (Phase 1)

1. Pin / unpin from card and detail; visual state correct.
2. Permission allow and deny paths.
3. NS → LIVE → FT transition; notification body updates quietly.
4. FT advances to next queued match; empty queue clears notification.
5. Reorder queue changes which match becomes active when appropriate.
6. Poll failure retains last score.
7. Manual smoke on Android Chrome; note iOS limitations in QA notes.

## Success criteria

- User can pin matches without installing a PWA.
- On a supporting browser (Android Chrome), one persistent notification tracks the active queued score quietly.
- Queue auto-advances on FT.
- No new backend score product required.
- Spec leaves a clear, shared contract for Phase 2 Live Activities.

## Implementation note

Do not start coding until an implementation plan is written from this spec (`writing-plans` skill).
