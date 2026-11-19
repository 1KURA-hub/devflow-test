import csv, sys, statistics

path = sys.argv[1]
rows = list(csv.DictReader(open(path)))
if not rows:
    print("no samples"); sys.exit(1)

times = sorted(int(r["timeStamp"]) for r in rows)
elapsed = [int(r["elapsed"]) for r in rows]
ok = [r for r in rows if r["success"] == "true"]
err = len(rows) - len(ok)

dur = (max(times) - min(times)) / 1000.0
qps = len(rows) / dur if dur > 0 else 0

def pct(vals, p):
    if not vals: return 0
    k = (len(vals) - 1) * p / 100.0
    f = int(k)
    c = min(f + 1, len(vals) - 1)
    return vals[f] + (vals[c] - vals[f]) * (k - f)

e = sorted(elapsed)
print(f"samples={len(rows)} duration={dur:.1f}s qps={qps:.1f} "
      f"avg={statistics.mean(e):.1f}ms p50={pct(e,50):.1f} p95={pct(e,95):.1f} "
      f"p99={pct(e,99):.1f} max={max(e)}ms errors={err} err_rate={err/len(rows)*100:.2f}%")
codes = {}
for r in rows:
    codes[r["responseCode"]] = codes.get(r["responseCode"], 0) + 1
print("codes:", codes)
