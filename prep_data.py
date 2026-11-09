#!/usr/bin/env python3
"""Prep OWID CO2 data into star-schema CSVs + inline M table literals.

Inputs (already downloaded): owid-co2-data.csv, ISO 3166 regional codes CSV.
Outputs: dim_country.csv, dim_year.csv, fact_emissions.csv, m/*.m, validation.json
"""
import csv, json, re, sys, os

SRC = "/home/tauseef/.hermes/cache/scratch"
OUT = "/mnt/c/Users/tause/bench-hermes-deepseek-v4.1-20261109-2237/data"
os.makedirs(OUT + "/m", exist_ok=True)
MIN_YEAR = 1990

CONTINENT_BY_REGION = {
    "Africa": "Africa", "Asia": "Asia", "Europe": "Europe", "Oceania": "Oceania",
    "Antarctic": "Antarctica",
}
ISO3_OVERRIDES = {  # OWID ISO codes absent from the ISO 3166 list
    "XKX": ("Europe", "Southern Europe"),
}

iso = {}
with open(f"{SRC}/iso.csv", newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        region, sub = r.get("region", ""), r.get("sub-region", "")
        if region == "Americas":
            continent = "South America" if sub == "South America" else "North America"
        else:
            continent = CONTINENT_BY_REGION.get(region, "Not assigned")
        iso[r["alpha-3"]] = (continent, sub)

rows, unmatched, max_year = [], set(), MIN_YEAR
with open(f"{SRC}/owid.csv", newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        code = r["iso_code"] or ""
        if not re.fullmatch(r"[A-Z]{3}", code):
            continue  # drops aggregates ("World", "Europe", "High-income countries", ...)
        year = int(r["year"])
        if year < MIN_YEAR:
            continue
        if code not in iso and code not in ISO3_OVERRIDES:
            unmatched.add(code)
        rows.append(r)
        max_year = max(max_year, year)

def num(v):
    v = (v or "").strip()
    if v == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None

countries = sorted({r["iso_code"] for r in rows})
keyof = {c: i + 1 for i, c in enumerate(countries)}

dim_country = []
for c in countries:
    name = next(r["country"] for r in rows if r["iso_code"] == c)
    continent, region = iso.get(c) or ISO3_OVERRIDES.get(c, ("Not assigned", "Not assigned"))
    dim_country.append([keyof[c], name, c, continent, region])

FACT_COLS = ["CountryKey", "Year", "Population", "GDP", "CO2_Mt", "CO2_per_capita_t",
             "Coal_CO2", "Oil_CO2", "Gas_CO2", "Cement_CO2", "Methane", "Nitrous_Oxide",
             "Share_Global_CO2"]
SRC_COLS = ["population", "gdp", "co2", "co2_per_capita", "coal_co2", "oil_co2", "gas_co2",
            "cement_co2", "methane", "nitrous_oxide", "share_global_co2"]

fact = []
for r in rows:
    fact.append([keyof[r["iso_code"]], int(r["year"])] + [num(r[c]) for c in SRC_COLS])
fact.sort(key=lambda x: (x[1], x[0]))

with open(f"{OUT}/dim_country.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["CountryKey", "Country", "ISO3", "Continent", "Region"]); w.writerows(dim_country)

with open(f"{OUT}/fact_emissions.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(FACT_COLS); w.writerows(fact)

dim_year = [[y, (y // 10) * 10] for y in range(MIN_YEAR, max_year + 1)]
with open(f"{OUT}/dim_year.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["Year", "Decade"]); w.writerows(dim_year)

def mval(v):
    if v is None:
        return "null"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        return mtext(v)
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return repr(round(v, 10))

def mtext(s):
    return '"' + s.replace('"', '""') + '"'

def ident(s):
    """M identifier: bare when legal, else #"quoted"."""
    return s if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", s) else '#"' + s.replace('"', '""') + '"'

# Inline M tables: no external file / gateway / credentials needed for Fabric refresh.
def write_m(name, cols, types, data, typeof):
    tl = ", ".join(f"{ident(c)} = {t}" for c, t in zip(cols, types))
    body = (",\n            ".join("{" + ", ".join(mval(x) for x in row) + "}" for row in data))
    src = (f'let\n    Source = #table(type table [{tl}],\n        {{\n            {body}\n        }})\nin\n    Source\n')
    with open(f"{OUT}/m/{name}.m", "w", encoding="utf-8") as f:
        f.write(src)
    return len(src)

sz = {}
sz["Dim_Country"] = write_m("Dim_Country",
    ["CountryKey", "Country", "ISO3", "Continent", "Region"],
    ["Int64.Type", "text", "text", "text", "text"], dim_country, None)
sz["Fact_Emissions"] = write_m("Fact_Emissions", FACT_COLS,
    ["Int64.Type", "Int64.Type"] + ["number"] * 11, fact, None)
sz["Dim_Year"] = write_m("Dim_Year", ["Year", "Decade"],
    ["Int64.Type", "Int64.Type"], dim_year, None)

# Validation: independent recomputation of the 2022 CO2 total from the raw CSV.
p2022 = [r for r in fact if r[1] == 2022]
total_2022 = sum(r[4] for r in p2022 if r[4] is not None)
raw2022 = sum(num(r["co2"]) or 0 for r in rows if int(r["year"]) == 2022)
res = {
    "countries": len(dim_country), "fact_rows": len(fact),
    "year_min": MIN_YEAR, "year_max": max_year,
    "co2_2022_mt_fact": round(total_2022, 4), "co2_2022_mt_raw": round(raw2022, 4),
    "diff_pct": round(abs(total_2022 - raw2022) / raw2022 * 100, 6),
    "unmatched_iso": sorted(unmatched), "m_sizes_bytes": sz,
}
json.dump(res, open(f"{OUT}/validation.json", "w"), indent=2)
print(json.dumps(res, indent=2))
