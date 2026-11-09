#!/usr/bin/env python3
"""Push the local TMDL definition onto the model created by this run (updateDefinition)."""
import base64, json, os, subprocess, time, urllib.request, urllib.error

ROOT = "/mnt/c/Users/tause/bench-hermes-deepseek-v4.1-20261109-2237"
SM = f"{ROOT}/CO2Model.SemanticModel"
ids = json.load(open(f"{ROOT}/ids.json"))
WS, MID = ids["workspace"], ids["model_id"]
FAB, FAB_R = "https://api.fabric.microsoft.com/v1", "https://api.fabric.microsoft.com"
PBI = "https://api.powerbi.com/v1.0/myorg"
PBI_R = "https://analysis.windows.net/powerbi/api"

def token(r):
    return subprocess.check_output(["az", "account", "get-access-token", "--resource", r,
                                    "--query", "accessToken", "-o", "tsv"], text=True).strip()

def call(method, url, resource, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token(resource))
    req.add_header("Content-Type", "application/json")
    req.add_header("x-ms-fabric-skill", "semantic-model-authoring")
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

def parts():
    out = []
    for rel in ["definition.pbism", "definition/database.tmdl", "definition/model.tmdl",
                "definition/relationships.tmdl"]:
        out.append({"path": rel, "payload": base64.b64encode(open(f"{SM}/{rel}", "rb").read()).decode(),
                    "payloadType": "InlineBase64"})
    for sub in ("tables", "cultures"):
        d = f"{SM}/definition/{sub}"
        for f in sorted(os.listdir(d)):
            out.append({"path": f"definition/{sub}/{f}",
                        "payload": base64.b64encode(open(f"{d}/{f}", "rb").read()).decode(),
                        "payloadType": "InlineBase64"})
    return out

st, body, hdr = call("POST", f"{FAB}/workspaces/{WS}/semanticModels/{MID}/updateDefinition", FAB_R,
                     {"definition": {"format": "TMDL", "parts": parts()}})
print("updateDefinition ->", st, json.dumps(body)[:400])
if st == 202:
    loc = hdr.get("Location") or hdr.get("location")
    for _ in range(60):
        time.sleep(3)
        s2, b2, _ = call("GET", loc, FAB_R)
        if s2 == 200 and b2.get("status") in ("Succeeded", "Failed"):
            print("lro ->", b2.get("status"), json.dumps(b2.get("error"))[:400])
            break
        if s2 not in (200, 202):
            print("lro poll ->", s2, json.dumps(b2)[:300])
            break

st, r, _ = call("POST", f"{PBI}/groups/{WS}/datasets/{MID}/executeQueries", PBI_R,
                {"queries": [{"query": 'EVALUATE ROW("GDPpc_2022", CALCULATE([GDP per Capita ($)], Dim_Year[Year] = 2022), "Measures", COUNTROWS(INFO.MEASURES()))'}],
                 "serializerSettings": {"includeNulls": True}})
print("verify ->", st, json.dumps(r)[:400])
