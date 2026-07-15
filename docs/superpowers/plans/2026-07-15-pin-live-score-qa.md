# Pin Live Score — Phase 1 Manual QA Checklist

**Primary target:** Android Chrome (Chromium with Notification API support)  
**Out of scope for this pass:** Service worker / push, account sync, ActivityKit / Dynamic Island, backend changes

Automated unit/type checks (`npm test`, `tsc --noEmit`) run in CI/local; this checklist covers browser/device behavior that requires a human with real notifications.

---

## Pre-flight

- [ ] Dev or production build served over HTTPS or `localhost`
- [ ] At least two fixtures available (one upcoming/NS, one live or simulatable)
- [ ] Browser notification permission reset or fresh profile for permission tests

---

## Checklist

### 1. Pin / unpin from card and detail

- [ ] Pin from a **match card** on home/matches — icon shows active (win-green) state
- [ ] Unpin from the same card — icon returns to inactive
- [ ] Pin from **match detail** (`/match/{id}`) — same active styling
- [ ] Unpin from detail — queue updates; header pin count reflects change

### 2. First pin → permission prompt

- [ ] First pin on a clean profile triggers the browser **notification permission** prompt (not on page load)
- [ ] **Allow:** notification appears for active (head) match; in-app pin state persists
- [ ] **Deny:** queue and in-app pin state still work; enable-notifications hint shown; no crash

### 3. Live notification updates (granted permission)

- [ ] With permission granted, notification **title/body** update on live poll (~10s interval)
- [ ] Updates are quiet — same notification tag replaced; no noisy re-notify banner storm on each poll
- [ ] Score/minute changes reflect live-stats payload

### 4. Full time → dequeue and advance

- [ ] When active match reaches **FT** (simulate or wait): notification shows final score once
- [ ] Active match is removed from queue; **next queued match** becomes the notification
- [ ] If queue is empty after FT: notification **closes**; no stale notification left

### 5. Reorder changes next active

- [ ] With multiple pinned matches, open queue sheet and **reorder**
- [ ] After current match FT/dequeue, the **new head** (per reorder) becomes active notification
- [ ] Reorder while live: head remains active until FT unless explicitly testing mid-queue promotion rules

### 6. Network failure mid-live

- [ ] Kill network (offline / devtools) while a live match is pinned and notification showing
- [ ] **Last known score** retained in notification and in-app state
- [ ] Pin remains in queue; no auto-unpin on poll failure
- [ ] Restore network — polling resumes and notification catches up

### 7. Tap notification → match detail

- [ ] Tap system notification opens **`/match/{id}`** for the active (head) fixture
- [ ] Correct match loads; pin state consistent with queue

### 8. iOS Safari — honest limits (no Island claims)

- [ ] On iOS Safari, pin queue and in-app pin UI still work
- [ ] Document **observed** notification behavior (often limited background/update cadence vs Android Chrome)
- [ ] UI copy does **not** claim Dynamic Island, Lock Screen Live Activity, or PWA install requirement
- [ ] Phase 2 native companion noted only in docs/spec — not promised in product UI

---

## Platform notes

| Platform | Expectation |
| --- | --- |
| **Android Chrome** | Primary Phase 1 QA; persistent quiet notification updates |
| **Desktop Chrome / Edge** | Acceptable secondary smoke for permission + update loop |
| **iOS Safari** | Best-effort notifications; queue/in-app pin are source of truth |

---

## Sign-off

| Check | Tester | Date | Pass/Fail | Notes |
| --- | --- | --- | --- | --- |
| 1–7 Android Chrome | | | | |
| 8 iOS Safari | | | | |

**Agent smoke (automated, no real Notification):** `npm test`, `npx tsc --noEmit` — see task-10 report. Full notification walk remains **manual on device**.
