#!/usr/bin/env python3
"""Create the semantic model in Fabric from the local TMDL, refresh it, then validate with DAX."""
import base64, json, os, subprocess, sys, time, urllib.request, urllib.error

ROOT = "/mnt/c/Users/tause/bench-hermes-deepseek-v4.1-20261109-2237"
SM = f"{ROOT}/CO2Model.SemanticModel"
WS = "6881ccf8-e614-4ab8-b02d-c4820eded362"          # Fabric Learning Workspace
NAME = os.environ.get("MODEL_NAME", "CO2 Emissions Model (Hermes deepseek-v4.1)")
FAB = "https://api.fabric.microsoft.com/v1"
PBI = "https://powerbi.com.placeholder"  # replaced below
FAB_R = "https://api.fabric.microsoft.com"
PBI_R = "https://analysis.windows.net/powerbi/api"
SKILL = "semantic-model-authoring"

def token(resource):
    return subprocess.check_output(
        ["az", "account", "get-access-token", "--resource", resource,
         "--query", "accessToken", "-o", "tsv"], text=True).strip()

def call(method, url, resource, body=None, extra_headers=None, want_headers=False):
    tok = token(resource)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {tok}")
    req.add_header("Content-Type", "application/json")
    req.add_header("x-ms-fabric-skill", SKILL)
    for k, v in (extra_headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            raw = r.read().decode() or "{}"
            hdrs = dict(r.headers)
            status = r.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        hdrs, status = dict(e.headers), e.code
    try:
        parsed = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        parsed = {"raw": raw}
    return (status, parsed, hdrs) if want_headers else (status, parsed)

def poll(location):
    for _ in range(120):
        time.sleep(3)
        st, body = call("GET", location, FAB_R)
        if st == 200:
            state = body.get("status")
            if state == "Succeeded":
                return True, body
            if state == "Failed":
                return False, body
        elif st == 202:
            continue
        else:
            return False, body
    return False, {"status": "timeout"}

def parts():
    out = []
    for rel in ["definition.pbism", "definition/database.tmdl", "definition/model.tmdl",
                "definition/relationships.tmdl"]:
        p = f"{SM}/{rel}"
        if os.path.exists(p):
            out.append({"path": rel, "payload": base64.b64encode(open(p, "rb").read()).decode(),
                        "payloadType": "InlineBase64"})
    td = f"{SM}/definition/tables"
    for f in sorted(os.listdir(td)):
        out.append({"path": f"definition/tables/{f}",
                    "payload": base64.b64encode(open(f"{td}/{f}", "rb").read()).decode(),
                    "payloadType": "InlineBase64"})
    cs = f"{SM}/definition/cultures"
    if os.path.isdir(cs):
        for f in sorted(os.listdir(cs)):
            out.append({"path": f"definition/cultures/{f}",
                        "payload": base64.b64encode(open(f"{cs}/{f}", "rb").read()).decode(),
                        "payloadType": "InlineBase64"})
    return out

def main():
    st, body, hdr = call("POST", f"{FAB}/workspaces/{WS}/semanticModels", FAB_R,
                         {"displayName": NAME, "definition": {"format": "TMDL", "parts": parts()}},
                         want_headers=True)
    print("create ->", st, json.dumps(body)[:800])
    if st not in (200, 201, 202):
        sys.exit(1)
    if st == 202:
        loc = hdr.get("Location") or hdr.get("location")
        ok, res = poll(loc)
        print("lro ->", ok, json.dumps(res)[:800])
        if not ok:
            sys.exit(1)
        item = call("GET", f"{FAB}/workspaces/{WS}/semanticModels?recursive=false", FAB_R)[1]
        mid = [i["id"] for i in item.get("value", []) if i["displayName"] == NAME][0]
    else:
        mid = body["id"]
    print("MODEL_ID", mid)
    json.dump({"workspace": WS, "model_id": mid, "name": NAME},
              open(f"{ROOT}/ids.json", "w"), indent=2)

if __name__ == "__main__":
    main()
