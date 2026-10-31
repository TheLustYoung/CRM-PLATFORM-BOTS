"""Load test: many users asking the API at the same time.

It drives the same internal API the bots use, with the bot's service key, in steps of growing concurrency, and prints
throughput, latency percentiles and status codes for each step. By default every request registers a user (what each
/start and message does); --url makes them metadata requests for a link instead (real jobs: the workers fetch the
link, so use your own test link and few requests). Downloads themselves are not measured: they depend on the source
sites, and the queue absorbs them.

    python -m infrastructure.scripts.load_test --api http://127.0.0.1:8000 --steps 10,50,100 --requests 300

Run it against a test copy or outside peak hours: it creates synthetic users (ids 9_000_000_000+).
"""
import argparse
import asyncio
import statistics
import time
import httpx
from backend.config import settings


async def one(client: httpx.AsyncClient, api: str, user_id: int, url: str | None) -> tuple[float, int]:
    """One bot request: a user registration (database read and write, what every /start and message does), or with
    --url a metadata request for that link (creates a real job: the workers will fetch the link)."""
    started = time.perf_counter()
    headers = {"X-Bot-Kind": "media", "X-Service-Key": settings().service_key("media")}
    try:
        if url:
            response = await client.post(f"{api}/internal/metadata", headers=headers, json={
                "user_id": user_id, "username": None, "url": url, "request_key": f"load-{user_id}-{time.time_ns()}"})
        else:
            response = await client.post(f"{api}/internal/register", headers=headers,
                                         json={"user_id": user_id, "username": f"load{user_id}", "language_code": "en"})
        code = response.status_code
    except httpx.HTTPError:
        code = 0
    return time.perf_counter() - started, code


async def step(api: str, concurrency: int, total: int, url: str) -> dict:
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(timeout=30, limits=limits) as client:
        semaphore = asyncio.Semaphore(concurrency)

        async def run(i):
            async with semaphore:
                return await one(client, api, 9_000_000_000 + i, url)
        started = time.perf_counter()
        results = await asyncio.gather(*(run(i) for i in range(total)))
        elapsed = time.perf_counter() - started
    times = sorted(r[0] for r in results)
    codes: dict[int, int] = {}
    for _, code in results:
        codes[code] = codes.get(code, 0) + 1
    pick = lambda q: times[min(len(times) - 1, int(q * len(times)))] * 1000
    return {"concurrency": concurrency, "requests": total, "rps": round(total / elapsed, 1), "p50_ms": round(pick(0.5)),
            "p95_ms": round(pick(0.95)), "max_ms": round(times[-1] * 1000), "mean_ms": round(statistics.mean(times) * 1000), "codes": codes}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--steps", default="10,50,100")
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--url", default=None, help="test metadata requests for this link instead of registrations")
    args = parser.parse_args()
    print(f"{'concurrency':>11} {'req/s':>7} {'p50 ms':>7} {'p95 ms':>7} {'max ms':>7}  status codes")
    for concurrency in (int(s) for s in args.steps.split(",")):
        r = asyncio.run(step(args.api.rstrip("/"), concurrency, args.requests, args.url))
        print(f"{r['concurrency']:>11} {r['rps']:>7} {r['p50_ms']:>7} {r['p95_ms']:>7} {r['max_ms']:>7}  {r['codes']}")


if __name__ == "__main__":
    main()
