#!/usr/bin/env python3
"""
Simulate N concurrent users against GoalMind (local or deployed).

Usage:
  python scripts/load_test.py
  python scripts/load_test.py --base http://192.168.1.36:3000 --users 100 --rounds 3
  python scripts/load_test.py --api-only --base http://localhost:8000
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import time
from dataclasses import dataclass, field
from typing import Callable

import httpx

# Typical mobile session: home → matches bracket → teams list
FRONTEND_SESSION: list[tuple[str, str]] = [
    ("GET", "/"),
    ("GET", "/api/matches/bracket"),
    ("GET", "/api/teams"),
    ("GET", "/matches"),
]

API_SESSION: list[tuple[str, str]] = [
    ("GET", "/api/matches/bracket"),
    ("GET", "/api/teams"),
    ("GET", "/api/matches/upcoming"),
    ("GET", "/health"),
]


@dataclass
class RequestResult:
    path: str
    status: int
    duration_ms: float
    error: str | None = None


@dataclass
class LoadTestReport:
    label: str
    users: int
    rounds: int
    results: list[RequestResult] = field(default_factory=list)

    @property
    def total_requests(self) -> int:
        return len(self.results)

    @property
    def failed(self) -> list[RequestResult]:
        return [r for r in self.results if r.error or r.status >= 400]

    def latency_ms(self) -> list[float]:
        return [r.duration_ms for r in self.results if not r.error and r.status < 400]

    def summary(self) -> str:
        lat = self.latency_ms()
        err = self.failed
        duration_s = max((r.duration_ms for r in self.results), default=1) / 1000
        lines = [
            f"\n{'=' * 60}",
            f"  {self.label}",
            f"  {self.users} concurrent users × {self.rounds} rounds = {self.total_requests} requests",
            f"{'=' * 60}",
        ]
        if not lat:
            lines.append("  No successful requests.")
            return "\n".join(lines)

        sorted_lat = sorted(lat)
        p = lambda q: sorted_lat[int(len(sorted_lat) * q)] if sorted_lat else 0
        total_time = sum(r.duration_ms for r in self.results) / 1000
        rps = len(lat) / total_time if total_time > 0 else 0

        lines.extend(
            [
                f"  Success rate:   {100 * len(lat) / self.total_requests:.1f}% ({len(lat)}/{self.total_requests})",
                f"  Errors:         {len(err)}",
                f"  Throughput:     {rps:.1f} req/s",
                f"  Latency (ms):",
                f"    min:  {min(lat):.0f}",
                f"    avg:  {statistics.mean(lat):.0f}",
                f"    p50:  {p(0.50):.0f}",
                f"    p95:  {p(0.95):.0f}",
                f"    p99:  {p(0.99):.0f}",
                f"    max:  {max(lat):.0f}",
            ]
        )

        if err:
            by_status: dict[str, int] = {}
            for e in err[:10]:
                key = e.error or f"HTTP {e.status}"
                by_status[key] = by_status.get(key, 0) + 1
            lines.append("  Sample errors:")
            for key, count in by_status.items():
                lines.append(f"    {count}× {key}")

        # Per-path breakdown
        by_path: dict[str, list[float]] = {}
        for r in self.results:
            if r.error or r.status >= 400:
                continue
            by_path.setdefault(r.path, []).append(r.duration_ms)
        lines.append("  Per endpoint (avg ms):")
        for path, times in sorted(by_path.items(), key=lambda x: statistics.mean(x[1]), reverse=True):
            lines.append(f"    {path}: {statistics.mean(times):.0f}ms")

        return "\n".join(lines)


async def run_user(
    client: httpx.AsyncClient,
    user_id: int,
    session: list[tuple[str, str]],
    rounds: int,
    think_ms: int,
    out: list[RequestResult],
    lock: asyncio.Lock,
    virtual_ips: bool,
) -> None:
    headers = {"X-Forwarded-For": f"10.99.{user_id // 254}.{user_id % 254}"} if virtual_ips else None
    for _ in range(rounds):
        for method, path in session:
            start = time.perf_counter()
            try:
                response = await client.request(method, path, timeout=30.0, headers=headers)
                elapsed = (time.perf_counter() - start) * 1000
                result = RequestResult(path=path, status=response.status_code, duration_ms=elapsed)
            except Exception as exc:  # noqa: BLE001
                elapsed = (time.perf_counter() - start) * 1000
                result = RequestResult(path=path, status=0, duration_ms=elapsed, error=str(exc))
            async with lock:
                out.append(result)
            if think_ms > 0:
                await asyncio.sleep(think_ms / 1000)


async def run_load_test(
    base_url: str,
    users: int,
    rounds: int,
    session: list[tuple[str, str]],
    label: str,
    think_ms: int,
    virtual_ips: bool,
) -> LoadTestReport:
    base_url = base_url.rstrip("/")
    results: list[RequestResult] = []
    lock = asyncio.Lock()
    limits = httpx.Limits(max_connections=users + 10, max_keepalive_connections=users)

    async with httpx.AsyncClient(base_url=base_url, limits=limits, follow_redirects=True) as client:
        tasks = [
            run_user(client, i, session, rounds, think_ms, results, lock, virtual_ips)
            for i in range(users)
        ]
        await asyncio.gather(*tasks)

    return LoadTestReport(label=label, users=users, rounds=rounds, results=results)


def main() -> None:
    parser = argparse.ArgumentParser(description="GoalMind concurrent user load test")
    parser.add_argument("--base", default="http://localhost:3000", help="Frontend base URL")
    parser.add_argument("--api-base", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--users", type=int, default=100, help="Concurrent users")
    parser.add_argument("--rounds", type=int, default=2, help="Session rounds per user")
    parser.add_argument("--think-ms", type=int, default=100, help="Pause between requests (simulates reading)")
    parser.add_argument("--api-only", action="store_true", help="Test backend API only")
    parser.add_argument("--frontend-only", action="store_true", help="Test frontend + proxy only")
    parser.add_argument("--virtual-ips", action="store_true", help="Unique X-Forwarded-For per user (needs TRUST_PROXY_HEADERS=true on backend)")
    args = parser.parse_args()

    if args.virtual_ips:
        print("Virtual IPs enabled — set TRUST_PROXY_HEADERS=true on backend for accurate 100-user simulation.\n")
    print(f"\nGoalMind load test — {args.users} concurrent users")
    print(f"Think time: {args.think_ms}ms between requests\n")

    async def run_all() -> list[LoadTestReport]:
        reports: list[LoadTestReport] = []
        if not args.frontend_only:
            reports.append(
                await run_load_test(
                    args.api_base,
                    args.users,
                    args.rounds,
                    API_SESSION,
                    f"Backend API ({args.api_base})",
                    args.think_ms,
                    args.virtual_ips,
                )
            )
        if not args.api_only:
            reports.append(
                await run_load_test(
                    args.base,
                    args.users,
                    args.rounds,
                    FRONTEND_SESSION,
                    f"Frontend + proxy ({args.base})",
                    args.think_ms,
                    args.virtual_ips,
                )
            )
        return reports

    reports = asyncio.run(run_all())
    for report in reports:
        print(report.summary())

    total_errors = sum(len(r.failed) for r in reports)
    all_lat = [ms for r in reports for ms in r.latency_ms()]
    if all_lat:
        p95 = sorted(all_lat)[int(len(all_lat) * 0.95)]
        print(f"\n{'=' * 60}")
        print("  VERDICT (rule of thumb for mobile UX)")
        print(f"{'=' * 60}")
        if total_errors == 0 and p95 < 2000:
            print("  PASS — 100 users handled with p95 under 2s and no errors.")
        elif total_errors == 0 and p95 < 5000:
            print("  OK   — No errors, but p95 > 2s. Fine for dev; optimize before big launch.")
        else:
            print("  WARN — Errors and/or high latency. Review backend cache and hosting.")
        print()


if __name__ == "__main__":
    main()
