#!/usr/bin/env python3
"""Generate the CO2 star-schema semantic model TMDL (PBIP) with inline M data."""
import json, os, re, uuid, hashlib

ROOT = "/mnt/c/Users/tause/bench-hermes-deepseek-v4.1-20261109-2237"
SM = f"{ROOT}/CO2Model.SemanticModel"
DEF = f"{SM}/definition"
os.makedirs(f"{DEF}/tables", exist_ok=True)
os.makedirs(f"{SM}/.pbi", exist_ok=True)
os.makedirs(f"{DEF}/cultures", exist_ok=True)

def lt(seed):
    return str(uuid.UUID(hashlib.md5(seed.encode()).hexdigest()))

def m_source(name):
    """Indent the inline M table to sit under `source =` inside TMDL."""
    lines = open(f"{ROOT}/data/m/{name}.m", encoding="utf-8").read().rstrip("\n").split("\n")
    return "\n".join("\t\t\t\t" + l if l.strip() else l for l in lines)

# ---------------------------------------------------------------- dimensions
dim_country_cols = [
    ("CountryKey", "int64", "0", True, None, None),
    ("Country", "string", None, False, "Country", None),
    ("ISO3", "string", None, False, None, None),
    ("Continent", "string", None, False, "Continent", None),
    ("Region", "string", None, False, None, None),
]

def col(name, dtype, key, hidden, fmt=None, data_cat=None, sort_by=None, desc=None):
    s = ""
    if desc:
        s += f"\t\t/// {desc}\n"
    s += f"\tcolumn {tmdl_q(name)}\n\t\tdataType: {dtype}\n"
    if key:
        s += "\t\tisKey\n"
    if hidden:
        s += "\t\tisHidden\n"
    if fmt:
        s += f"\t\tformatString: {fmt}\n"
    if data_cat:
        s += f"\t\tdataCategory: {data_cat}\n"
    if sort_by:
        s += f"\t\tsortByColumn: {tmdl_q(sort_by)}\n"
    s += "\t\tsummarizeBy: none\n"
    s += f"\t\tlineageTag: {lt('col:' + name)}\n"
    s += f"\t\tsourceColumn: {tmdl_q(name)}\n"
    return s

def tmdl_q(name):
    return name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) else "'" + name.replace("'", "''") + "'"

# ---------------------------------------------------------------- model.tmdl
model = """model Model
\tculture: en-US
\tdefaultPowerBIDataSourceVersion: powerBI_V3
\tdiscourageImplicitMeasures
\tdataAccessOptions
\t\tlegacyRedirects
\t\treturnErrorValuesAsNull

annotation __PBI_TimeIntelligenceEnabled = 0

annotation PBI_QueryOrder = ["Dim_Country","Dim_Year","Fact_Emissions","_Measures"]

annotation PBI_ProTooling = ["DevMode"]

ref table Dim_Country
ref table Dim_Year
ref table Fact_Emissions
ref table _Measures
"""
open(f"{DEF}/model.tmdl", "w", encoding="utf-8").write(model)
open(f"{DEF}/database.tmdl", "w", encoding="utf-8").write("database\n\tcompatibilityLevel: 1606\n")
open(f"{DEF}/cultures/en-US.tmdl", "w", encoding="utf-8").write("cultureInfo en-US\n")

# ---------------------------------------------------------------- Dim_Country
dc = ["table Dim_Country", "\tlineageTag: " + lt("tbl:Dim_Country"), ""]
for name, dtype, fmt, hidden, cat, sb in dim_country_cols:
    dc.append(col(name, dtype, name == "CountryKey", hidden, fmt, cat))
    dc.append("")
dc.append("""\tpartition Dim_Country = m
\t\tmode: import
\t\tsource =
""" + m_source("Dim_Country") + """

\tannotation PBI_ResultType = Table
""")
open(f"{DEF}/tables/Dim_Country.tmdl", "w", encoding="utf-8").write("\n".join(dc))

# ---------------------------------------------------------------- Dim_Year
dy = ["table Dim_Year", "\tlineageTag: " + lt("tbl:Dim_Year"), ""]
dy.append(col("Year", "int64", True, False, "0"))
dy.append("")
dy.append(col("Decade", "int64", False, False, "0"))
dy.append("")
dy.append("""\tpartition Dim_Year = m
\t\tmode: import
\t\tsource =
""" + m_source("Dim_Year") + """

\tannotation PBI_ResultType = Table
""")
open(f"{DEF}/tables/Dim_Year.tmdl", "w", encoding="utf-8").write("\n".join(dy))

# ---------------------------------------------------------------- Fact
fact_cols = [
    ("CountryKey", "int64", True, None),
    ("Year", "int64", True, None),
    ("Population", "double", True, "#,0"),
    ("GDP", "double", True, "#,0"),
    ("CO2_Mt", "double", True, "#,0.0"),
    ("CO2_per_capita_t", "double", True, "#,0.00"),
    ("Coal_CO2", "double", True, "#,0.0"),
    ("Oil_CO2", "double", True, "#,0.0"),
    ("Gas_CO2", "double", True, "#,0.0"),
    ("Cement_CO2", "double", True, "#,0.0"),
    ("Methane", "double", True, "#,0.0"),
    ("Nitrous_Oxide", "double", True, "#,0.0"),
    ("Share_Global_CO2", "double", True, "0.000%"),
]
fa = ["table Fact_Emissions", "\tlineageTag: " + lt("tbl:Fact_Emissions"), ""]
for name, dtype, hidden, fmt in fact_cols:
    fa.append(col(name, dtype, False, hidden, fmt))
    fa.append("")
fa.append("""\tpartition Fact_Emissions = m
\t\tmode: import
\t\tsource =
""" + m_source("Fact_Emissions") + """

\tannotation PBI_ResultType = Table
""")
open(f"{DEF}/tables/Fact_Emissions.tmdl", "w", encoding="utf-8").write("\n".join(fa))

# ---------------------------------------------------------------- measures
MEASURES = [
    ("Total CO2 (Mt)", "SUM(Fact_Emissions[CO2_Mt])", "#,0.0",
     "Total CO2 emissions of the selected countries and years, in million tonnes (OWID)."),
    ("Population", "SUM(Fact_Emissions[Population])", "#,0",
     "Sum of population of the selected rows."),
    ("GDP per Capita ($)", "DIVIDE([GDP], [Population])", "#,0",
     "GDP per person in international-$, 2011 PPP (used by the GDP vs CO2 scatter page)."),
    ("GDP", "SUM(Fact_Emissions[GDP])", "#,0",
     "Sum of GDP (international-$, 2011 PPP) of the selected rows."),
    ("CO2 per Capita (t)", "DIVIDE([Total CO2 (Mt)] * 1000000, [Population])", "#,0.00",
     "Tonnes of CO2 per person: (CO2 Mt x 1e6) / population."),
    ("CO2 YoY %",
     "VAR y = MAX ( Dim_Year[Year] )\n"
     "VAR cur = CALCULATE ( [Total CO2 (Mt)], Dim_Year[Year] = y )\n"
     "VAR prior =\n"
     "    CALCULATE ( [Total CO2 (Mt)], REMOVEFILTERS ( Dim_Year ), Dim_Year[Year] = y - 1 )\n"
     "RETURN\n"
     "    DIVIDE ( cur - prior, prior )",
     "0.0%", "Year-on-year change of Total CO2 against the previous year in the visible year context."),
    ("CO2 vs 1990 %",
     "VAR y = MAX ( Dim_Year[Year] )\n"
     "VAR cur = CALCULATE ( [Total CO2 (Mt)], Dim_Year[Year] = y )\n"
     "VAR base =\n"
     "    CALCULATE ( [Total CO2 (Mt)], REMOVEFILTERS ( Dim_Year ), Dim_Year[Year] = 1990 )\n"
     "RETURN\n"
     "    DIVIDE ( cur - base, base )",
     "0.0%", "Change against the 1990 Kyoto baseline for the countries currently in filter context."),
    ("Share of Global CO2 %",
     "VAR cur = [Total CO2 (Mt)]\n"
     "VAR total_all =\n"
     "    CALCULATE ( [Total CO2 (Mt)], REMOVEFILTERS ( Dim_Country ) )\n"
     "RETURN\n"
     "    DIVIDE ( cur, total_all )",
     "0.00%", "Country share of world CO2 for the years in filter context (country filter removed on purpose)."),
    ("Coal CO2", "SUM(Fact_Emissions[Coal_CO2])", "#,0.0", "Coal-sourced CO2, million tonnes."),
    ("Oil CO2", "SUM(Fact_Emissions[Oil_CO2])", "#,0.0", "Oil-sourced CO2, million tonnes."),
    ("Gas CO2", "SUM(Fact_Emissions[Gas_CO2])", "#,0.0", "Gas-sourced CO2, million tonnes."),
    ("Cement CO2", "SUM(Fact_Emissions[Cement_CO2])", "#,0.0", "Cement-sourced CO2, million tonnes."),
    ("Carbon Intensity (kg per $ GDP)",
     "DIVIDE([Total CO2 (Mt)] * 1000000000, [GDP])", "#,0.000",
     "Kilograms of CO2 per dollar of GDP: (CO2 Mt x 1e9) / GDP."),
    ("Rank by Total CO2",
     "IF (\n"
     "    ISBLANK ( [Total CO2 (Mt)] ),\n"
     "    BLANK (),\n"
     "    RANKX ( ALLSELECTED ( Dim_Country[Country] ), [Total CO2 (Mt)],, DESC, Dense )\n"
     ")",
     "#,0", "Dense rank of the country by Total CO2 within the countries visible in the report."),
]

me = [
    "table _Measures",
    "\tlineageTag: " + lt("tbl:_Measures"),
    "",
    "\tcolumn Placeholder",
    "\t\tdataType: int64",
    "\t\tisHidden",
    "\t\tformatString: 0",
    "\t\tsummarizeBy: none",
    f"\t\tlineageTag: {lt('col:Placeholder')}",
    "\t\tsourceColumn: Placeholder",
    "",
]
for name, expr, fmt, desc in MEASURES:
    lines = expr.split("\n")
    body = "\t\t\t" + lines[0] + ("\n" + "\n".join("\t\t\t" + l if l.strip() else l for l in lines[1:]) if len(lines) > 1 else "")
    me.append(f"\t/// {desc}")
    me.append(f"\tmeasure {tmdl_q(name)} =\n{body}")
    me.append(f"\t\tformatString: {fmt}")
    me.append(f"\t\tlineageTag: {lt('meas:' + name)}")
    me.append("")
me.append("""\tpartition _Measures = m
\t\tmode: import
\t\tsource =
\t\t\t\tlet
\t\t\t\t    Source = #table(type table [Placeholder = Int64.Type], {})
\t\t\t\tin
\t\t\t\t    Source

\tannotation PBI_ResultType = Table
""")
open(f"{DEF}/tables/_Measures.tmdl", "w", encoding="utf-8").write("\n".join(me))

# ---------------------------------------------------------------- relationships
rel = f"""relationship {lt('rel:country')}
\tfromColumn: Fact_Emissions.CountryKey
\ttoColumn: Dim_Country.CountryKey

relationship {lt('rel:year')}
\tfromColumn: Fact_Emissions.Year
\ttoColumn: Dim_Year.Year
"""
open(f"{DEF}/relationships.tmdl", "w", encoding="utf-8").write(rel)

# ---------------------------------------------------------------- pbip plumbing
open(f"{DEF}.pbism", "w", encoding="utf-8").write('{\n  "version": "4.2",\n  "settings": {}\n}\n')
open(f"{SM}/.pbi/editorSettings.json", "w", encoding="utf-8").write(
    json.dumps({"version": "1.0", "enableAutoRecovery": True,
                "useTMDL": True, "showHiddenObjects": False}, indent=2))
open(f"{SM}/.platform", "w", encoding="utf-8").write(json.dumps({
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.1.0/schema.json",
    "metadata": {"type": "SemanticModel", "displayName": "CO2Model"},
    "config": {"version": "2.0", "logicalId": lt("sm:CO2Model")}}, indent=2))
print("model written")
