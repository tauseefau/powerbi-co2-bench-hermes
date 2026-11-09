#!/usr/bin/env python3
"""Refresh the published model and run DAX validation queries."""
import json, subprocess, sys, time, urllib.request, urllib.error

ROOT = "/mnt/c/Users/tause/bench-hermes-deepseek-v4.1-20261109-2237"
ids = json.load(open(f"{ROOT}/ids.json"))
WS, MID = ids["workspace"], ids["model_id"]
PBI_R = "https://analysis.windows.net/powerbi/api"
PBI = "https://api.powerbi.com/v1.0/myorg"

def token(r):
    return subprocess.check_output(["az", "account", "get-access-token", "--resource", r,
                                    "--query", "accessToken", "-o", "tsv"], text=True).strip()

def call(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token(PBI_R))
    req.add_header("Content-Type", "application/json")
    req.add_header("x-ms-fabric-skill", "semantic-model-authoring")
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            raw = r.read().decode() or "{}"
            return r.status, (json.loads(raw) if raw.strip() else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"raw": raw}

print(json.dumps(call("POST", f"{PBI}/groups/{WS}/datasets/{MID}/refreshes",
                      {"notifyOption": "NoNotification"}), indent=2))
for i in range(80):
    time.sleep(5)
    st, h = call("GET", f"{PBI}/groups/{WS}/datasets/{MID}/refreshes?$top=1")
    row = (h.get("value") or [{}])[0]
    print(f"[{i}] refresh status:", row.get("status"), row.get("extendedStatus") or "")
    if row.get("status") in ("Completed", "Failed"):
        if row.get("status") == "Failed":
            print(json.dumps(row, indent=2)[:2000])
        break

QUERIES = {
    "total_co2_2022": 'EVALUATE ROW("TotalCO2_2022", CALCULATE([Total CO2 (Mt)], Dim_Year[Year] = 2022))',
    "fact_rows_countries": 'EVALUATE ROW("Rows", COUNTROWS(Fact_Emissions), "Countries", COUNTROWS(Dim_Country), "Years", COUNTROWS(Dim_Year))',
    "top5_2022": 'EVALUATE TOPN(5, ADDCOLUMNS(VALUES(Dim_Country[Country]), "CO2", [Total CO2 (Mt)], "Share", [Share of Global CO2 %], "Rank", [Rank by Total CO2], "YoY", [CO2 YoY %]), [CO2], DESC)',
    "per_capita_2022": 'EVALUATE ROW("CO2_per_capita_2022", CALCULATE([CO2 per Capita (t)], Dim_Year[Year] = 2022), "Intensity", CALCULATE([Carbon Intensity (kg per $ GDP)], Dim_Year[Year] = 2022), "vs1990", CALCULATE([CO2 vs 1990 %], Dim_Year[Year] = 2022))',
    "fuels_2022": 'EVALUATE ROW("Coal", CALCULATE([Coal CO2], Dim_Year[Year] = 2022), "Oil", CALCULATE([Oil CO2], Dim_Year[Year] = 2022), "Gas", CALCULATE([Gas CO2], Dim_Year[Year] = 2022), "Cement", CALCULATE([Cement CO2], Dim_Year[Year] = 2022))',
    "yoy_2022": 'EVALUATE ROW("YoY_2022", CALCULATE([CO2 YoY %], REMOVEFILTERS(Dim_Country), Dim_Year[Year] = 2022))',
}
out = {}
for k, q in QUERIES.items():
    st, r = call("POST", f"{PBI}/groups/{WS}/datasets/{MID}/executeQueries",
                 {"queries": [{"query": q}], "serializerSettings": {"includeNulls": True}})
    rows = r.get("results", [{}])[0].get("tables", [{}])[0].get("rows") if st == 200 else r
    out[k] = rows
    print(k, "->", st, json.dumps(rows)[:900])
json.dump(out, open(f"{ROOT}/validation_dax.json", "w"), indent=2)
