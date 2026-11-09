#!/usr/bin/env python3
"""Push the final PBIR to the report item created by this run, then read it back."""
import base64, json, subprocess, time, urllib.request, urllib.error

ROOT = "/mnt/c/Users/tause/bench-hermes-deepseek-v4.1-20261109-2237"
ids = json.load(open(f"{ROOT}/ids.json"))
WS, MID, RID = ids["workspace"], ids["model_id"], ids["report_id"]
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

raw = subprocess.run(["powerbi-report-author", "pack", f"{ROOT}/CO2Emissions.Report", "--raw"],
                     capture_output=True, text=True, check=True).stdout
body = json.loads(raw)
for part in body["definition"]["parts"]:
    if part["path"] == "definition.pbir":
        pbir = json.loads(base64.b64decode(part["payload"]))
        pbir["datasetReference"] = {"byConnection": {"connectionString": f"semanticmodelid={MID}"}}
        part["payload"] = base64.b64encode(json.dumps(pbir, indent=2).encode()).decode()

st, res, hdr = call("POST", f"{FAB}/workspaces/{WS}/reports/{RID}/updateDefinition", body)
print("updateDefinition ->", st, json.dumps(res)[:300])
if st == 202:
    loc = hdr.get("Location") or hdr.get("location")
    for _ in range(60):
        time.sleep(3)
        s2, b2, _ = call("GET", loc)
        if s2 == 200 and b2.get("status") in ("Succeeded", "Failed"):
            print("lro ->", b2.get("status"), json.dumps(b2.get("error"))[:400])
            break

st, r, _ = call("GET", f"{FAB}/workspaces/{WS}/reports/{RID}")
print("report ->", st, r.get("displayName"), r.get("datasetId"))
st, d, _ = call("POST", f"{FAB}/workspaces/{WS}/reports/{RID}/getDefinition?format=PBIR", {})
if st == 202:  # LRO
    time.sleep(5)
    d = call("GET", f"{FAB}/workspaces/{WS}/reports/{RID}/getDefinition?format=PBIR")[1]
parts = [p["path"] for p in d.get("definition", {}).get("parts", [])]
print("parts:", len(parts), parts[:8])
pbir = json.loads(base64.b64decode(next(p["payload"] for p in d["definition"]["parts"]
                                        if p["path"] == "definition.pbir")))
print("binding:", pbir.get("datasetReference"))
