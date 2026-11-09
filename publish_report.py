#!/usr/bin/env python3
"""Pack the local PBIR report, rebind it to this run's model, create it in Fabric."""
import base64, json, subprocess, time, urllib.request, urllib.error

ROOT = "/mnt/c/Users/tause/bench-hermes-deepseek-v4.1-20261109-2237"
ids = json.load(open(f"{ROOT}/ids.json"))
WS, MID = ids["workspace"], ids["model_id"]
NAME = "CO2 Emissions Dashboard (Hermes deepseek-v4.1)"
FAB, FAB_R = "https://api.fabric.microsoft.com/v1", "https://api.fabric.microsoft.com"

def token(r):
    return subprocess.check_output(["az", "account", "get-access-token", "--resource", r,
                                    "--query", "accessToken", "-o", "tsv"], text=True).strip()

def call(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token(FAB_R))
    req.add_header("Content-Type", "application/json")
    req.add_header("x-ms-fabric-skill", "powerbi-report-cli")
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            raw = r.read().decode() or "{}"
            return r.status, (json.loads(raw) if raw.strip() else {}), dict(r.headers)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw), dict(e.headers)
        except json.JSONDecodeError:
            return e.code, {"raw": raw}, dict(e.headers)

raw = subprocess.run(["powerbi-report-author", "pack", f"{ROOT}/CO2Emissions.Report",
                      "--mode", "create", "--display-name", NAME, "--raw"],
                     capture_output=True, text=True, check=True).stdout
body = json.loads(raw)

for part in body["definition"]["parts"]:
    if part["path"] == "definition.pbir":
        pbir = json.loads(base64.b64decode(part["payload"]))
        pbir["datasetReference"] = {"byConnection": {"connectionString": f"semanticmodelid={MID}"}}
        part["payload"] = base64.b64encode(json.dumps(pbir, indent=2).encode()).decode()

st, res, hdr = call("POST", f"{FAB}/workspaces/{WS}/reports", body)
print("create report ->", st, json.dumps(res)[:400])
if st == 202:
    loc = hdr.get("Location") or hdr.get("location")
    for _ in range(60):
        time.sleep(3)
        s2, b2, _ = call("GET", loc)
        if s2 == 200 and b2.get("status") in ("Succeeded", "Failed", "Deduplicated"):
            print("lro ->", b2.get("status"), json.dumps(b2.get("error"))[:500])
            break
        if s2 not in (200, 202):
            print("poll ->", s2, json.dumps(b2)[:300]); break
elif st in (200, 201):
    print("report id", res.get("id"))

st, r, _ = call("GET", f"{FAB}/workspaces/{WS}/reports")
rep = [x for x in r.get("value", []) if x["displayName"] == NAME]
print("reports in ws:", st, [(x["displayName"], x["id"]) for x in rep])
if rep:
    ids["report_id"] = rep[0]["id"]
    json.dump(ids, open(f"{ROOT}/ids.json", "w"), indent=2)
