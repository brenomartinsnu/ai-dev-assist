#!/usr/bin/env python3
"""
Apple Pay orange-path triage helper.

Given a customer-id, shard, card-id, tokenization-id and the approximate
event timestamp, this:
  1. Calls piata's public-transport fraudster check for the customer.
  2. Queries Alexandria (nu.logs.k8s) for:
     - lost-boy's device-score request (mdes-request)
     - lost-boy's auth-response (generic deny label)
     - piata's tar-decision (the actual reason codes + device-score --
       this is what really confirms orange path)

All Alexandria queries are scoped to a single `date` partition (required
for Trino partition pruning -- unscoped scans get S3-throttled) plus a
narrow time window around --timestamp, since the request/response/tar-decision
log lines all land within minutes of each other.

Requires `nu` (nucli) on PATH and valid credentials (`nu dev bd`), plus the
`alexandria-query` scope.
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text):
    return ANSI_ESCAPE.sub("", text)


REQUEST_QUERY = """
SELECT *
FROM nu.logs.k8s
WHERE date = DATE '{date}'
  AND time BETWEEN TIMESTAMP '{start}' AND TIMESTAMP '{end}'
  AND prototype = '{shard}'
  AND service = 'lost-boy'
  AND log LIKE '%{tokenization_id}%'
  AND log LIKE '%mdes-request%'
ORDER BY time DESC
LIMIT 100
"""

RESPONSE_QUERY = """
SELECT *
FROM nu.logs.k8s
WHERE date = DATE '{date}'
  AND time BETWEEN TIMESTAMP '{start}' AND TIMESTAMP '{end}'
  AND prototype = '{shard}'
  AND service = 'lost-boy'
  AND json_value(log, 'lax $.data.message.card."card/id"') = '{card_id}'
  AND log LIKE '%auth-response%'
ORDER BY time DESC
LIMIT 100
"""

PIATA_TAR_QUERY = """
SELECT *
FROM nu.logs.k8s
WHERE date = DATE '{date}'
  AND time BETWEEN TIMESTAMP '{start}' AND TIMESTAMP '{end}'
  AND prototype = '{shard}'
  AND service = 'piata'
  AND log LIKE '%tar-decision%'
  AND log LIKE '%{customer_id}%'
ORDER BY time DESC
LIMIT 50
"""


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"$ {' '.join(cmd)}", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(f"command failed: {' '.join(cmd)}")
    return strip_ansi(result.stdout)


def check_piata_fraud(country, shard, customer_id, env):
    account = f"nu-{country}"
    authorization_id = str(uuid.uuid4())
    payload = json.dumps({"customer-id": customer_id, "authorization-id": authorization_id})
    cmd = [
        account, "ser", "curl", "post", shard, "piata",
        "/api/tokenization-requests/validate",
        "--data", payload,
        "--env", env, "-f",
    ]
    out = run(cmd)
    return json.loads(out)


def query_alexandria(sql, country, env):
    with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False) as f:
        f.write(sql)
        path = f.name
    try:
        cmd = ["nu", "alexandria", "search", path, "--country", country, "--env", env]
        return run(cmd)
    finally:
        Path(path).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--customer-id", required=True)
    parser.add_argument("--shard", required=True)
    parser.add_argument("--card-id", required=True)
    parser.add_argument("--tokenization-id", required=True)
    parser.add_argument("--timestamp", required=True,
                         help="Approximate event time, e.g. '2026-08-16 01:26:12' "
                              "(used for the date partition + a time window)")
    parser.add_argument("--window-hours", type=float, default=1.0,
                         help="Hours before/after --timestamp to search (default 1 => 2h total window)")
    parser.add_argument("--country", default="br", help="br (default) · mx · co; also derives the nucli account (nu-<country>)")
    parser.add_argument("--env", default="prod")
    args = parser.parse_args()

    event_time = datetime.fromisoformat(args.timestamp)
    window = timedelta(hours=args.window_hours)
    start = (event_time - window).strftime("%Y-%m-%d %H:%M:%S")
    end = (event_time + window).strftime("%Y-%m-%d %H:%M:%S")
    date = event_time.strftime("%Y-%m-%d")

    print("== piata public-transport fraudster check ==")
    fraud_result = check_piata_fraud(args.country, args.shard, args.customer_id, args.env)
    print(json.dumps(fraud_result, indent=2))
    if fraud_result.get("result") == "approved":
        print("-> NOT a fraudster per Conrado's public-transport rule.")
    else:
        print("-> Flagged by the public-transport fraudster rule (real fraud case, not orange path).")

    print("\n== lost-boy device-score request ==")
    request_sql = REQUEST_QUERY.format(
        date=date, start=start, end=end, shard=args.shard, tokenization_id=args.tokenization_id,
    )
    print(query_alexandria(request_sql, args.country, args.env))

    print("\n== lost-boy auth-response (deny reason) ==")
    response_sql = RESPONSE_QUERY.format(
        date=date, start=start, end=end, shard=args.shard, card_id=args.card_id,
    )
    print(query_alexandria(response_sql, args.country, args.env))

    print("\n== piata tar-decision (actual reason codes + device-score) ==")
    tar_sql = PIATA_TAR_QUERY.format(
        date=date, start=start, end=end, shard=args.shard, customer_id=args.customer_id,
    )
    tar_out = query_alexandria(tar_sql, args.country, args.env)
    print(tar_out)

    is_orange_path = '"16"' in tar_out and '"denied"' in tar_out and '"device-score":"1"' not in tar_out
    if is_orange_path:
        print("-> Orange Path detected (reason code \"16\" + denied, device-score != 1). Suggested fix:")
        print(f"nu card orange-path-allow {args.customer_id}")
    else:
        print("-> No reason-code \"16\" + denied match found (or device-score is \"1\", a device "
              "restriction, not orange path); inspect manually before assuming orange path.")


if __name__ == "__main__":
    main()
