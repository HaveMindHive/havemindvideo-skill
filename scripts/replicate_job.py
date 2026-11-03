"""Run one Replicate prediction safely: time limits, cancel-and-retry on hangs, 429 backoff.

Why (Turaq, 11-02-2026): Stop Swiping lost hours to Kling jobs that sat 20-66 minutes on
Replicate and then failed, while our scripts polled forever. Normal times measured that day:
Kling 3 pro 2-4.5 min, lipsync-2-pro 1.5-2 min.

    from replicate_job import run
    url = run("kwaivgi/kling-v3-video", inp, limit_s=600)

The API key comes from REPLICATE_API_TOKEN (never printed).
"""
import json, os, sys, time, urllib.error, urllib.request

API = "https://api.replicate.com/v1"


def _req(url, data=None, method=None, timeout=60):
    h = {"Authorization": "Bearer " + os.environ["REPLICATE_API_TOKEN"], "Content-Type": "application/json",
         "User-Agent": "the-boss/1.0", "Prefer": "respond-async"}
    body = json.dumps(data).encode() if data is not None else None
    for attempt in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=h, method=method), timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                time.sleep(4 * (attempt + 1)); continue
            if e.code == 402:
                sys.exit("FAILED: Replicate says the account is out of credit (402). Tell Turaq; do not retry.")
            raise SystemExit(f"FAILED: HTTP {e.code}: {e.read()[:300].decode(errors='replace')}")
        except (urllib.error.URLError, TimeoutError):
            time.sleep(4 * (attempt + 1))
    raise SystemExit("FAILED: Replicate unreachable after retries")


def run(model, inp, limit_s=600, queue_limit_s=300, tries=2, poll_s=6, log=print):
    """Return the output URL. Cancels and retries a job that waits in queue longer than
    queue_limit_s or runs longer than limit_s; gives up after `tries` attempts."""
    last = "unknown"
    for n in range(1, tries + 1):
        p = _req(f"{API}/models/{model}/predictions", {"input": inp}, timeout=180)
        log(f"started {p['id']} ({model}, try {n}/{tries})", flush=True)
        t0 = time.time(); started = None
        while p["status"] not in ("succeeded", "failed", "canceled"):
            time.sleep(poll_s)
            try:
                p = _req(p["urls"]["get"], timeout=30)
            except SystemExit:
                continue
            now = time.time()
            if p["status"] == "processing" and started is None:
                started = now
            if (started is None and now - t0 > queue_limit_s) or (started and now - started > limit_s):
                why = "stuck in queue" if started is None else f"running over {limit_s // 60} min"
                try:
                    _req(p["urls"]["cancel"], {}, method="POST", timeout=30)
                except SystemExit:
                    pass
                log(f"canceled {p['id']}: {why} (Replicate is slow right now)", flush=True)
                last = why; p = {"status": "canceled"}
                break
        if p["status"] == "succeeded":
            out = p["output"] if isinstance(p["output"], str) else p["output"][0]
            log(f"done {p['id']} | predict_time {p.get('metrics', {}).get('predict_time')}", flush=True)
            return out
        if p["status"] == "failed":
            last = str(p.get("error"))[:300]
            log(f"failed {p.get('id')}: {last}", flush=True)
            if "invalid" in last.lower() or "E006" in last:
                break  # bad input: retrying the same input won't help
    sys.exit(f"FAILED after {n} tries: {last}")


def data_uri(path):
    import base64, mimetypes
    return f"data:{mimetypes.guess_type(path)[0]};base64," + base64.b64encode(open(path, "rb").read()).decode()


def download(url, out):
    urllib.request.urlretrieve(url, out)
    print("saved", out, flush=True)
