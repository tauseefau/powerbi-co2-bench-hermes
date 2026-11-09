#!/usr/bin/env python3
"""Build the 3-page PBIR report (pages, visuals, theme) for the CO2 model."""
import json, os, shutil, uuid

ROOT = "/mnt/c/Users/tause/bench-hermes-deepseek-v4.1-20261109-2237"
RD = f"{ROOT}/CO2Emissions.Report"
DEF = f"{RD}/definition"
BUILT = "2026-11-09"
AGENT = "Created using Hermes Agent / deepseek-v4.1-flash-1017"
FOOTER = f"Data: Our World in Data (CC BY 4.0) | Built {BUILT}"
MEAS = "_Measures"
FC, FY = "Fact_Emissions", "Dim_Year"
DC = "Dim_Country"

# ------------------------------------------------------------------ helpers
def lit(v):
    return {"expr": {"Literal": {"Value": v}}}

def p_str(s):
    return lit("'" + s.replace("'", "''") + "'")

def p_num(n):
    return lit(f"{n}D")

def p_bool(b):
    return lit("true" if b else "false")

def p_color(hexcode):
    return {"solid": {"color": {"expr": {"Literal": {"Value": "'" + hexcode + "'"}}}}}

def col(e, prop):
    return {"field": {"Column": {"Expression": {"SourceRef": {"Entity": e}}, "Property": prop}},
            "queryRef": f"{e}.{prop}", "nativeQueryRef": prop}

def meas(prop, entity=MEAS):
    return {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
            "queryRef": f"{entity}.{prop}", "nativeQueryRef": prop}

def title_obj(text):
    return {"title": [{"properties": {
        "show": p_bool(True),
        "text": p_str(text),
        "fontSize": p_num(12),
        "bold": p_bool(True),
        "fontColor": p_color("#1B1F24")}}]}

def container():
    return {"padding": [{"properties": {"left": p_num(8), "right": p_num(8),
                                         "top": p_num(8), "bottom": p_num(8)}}],
            "background": [{"properties": {"show": p_bool(True), "color": p_color("#FFFFFF")}}],
            "border": [{"properties": {"show": p_bool(True), "color": p_color("#E3E8EF"), "radius": p_num(6)}}],
            "visualHeader": [{"properties": {"show": p_bool(False)}}]}

_ids = iter(range(1, 400))
def vid(page):
    return f"{page}{next(_ids):04x}"

def visual(page, x, y, w, h, vtype, query=None, objects=None, filters=None,
           sort=None, title=None, z=None):
    name = vid(page)
    v = {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.14.0/schema.json",
         "name": name,
         "position": {"x": x, "y": y, "z": z if z is not None else next(_ids),
                      "height": h, "width": w, "tabOrder": next(_ids)},
         "visual": {"visualType": vtype}}
    if query:
        v["visual"]["query"] = query
        if sort:
            v["visual"]["query"]["sortDefinition"] = sort
    objs = dict(objects or {})
    if objs:
        v["visual"]["objects"] = objs
    vco = container()
    if title:
        vco.update(title_obj(title))
    v["visual"]["visualContainerObjects"] = vco
    if filters:
        v["filterConfig"] = {"filters": filters}
    return name, v

def textbox(text_lines, size=12, color="#4A5560", semibold=False, align="left", bg=None):
    runs = []
    for i, t in enumerate(text_lines):
        runs.append({"textRuns": [{"value": t, "textStyle": {
            "fontFamily": "Segoe UI Semibold" if semibold and i == 0 else "Segoe UI",
            "fontSize": f"{size}px", "color": color}}],
            "horizontalTextAlignment": align})
    objs = {"general": [{"properties": {"paragraphs": runs}}]}
    vco = {"padding": [{"properties": {"left": p_num(0), "right": p_num(0),
                                      "top": p_num(0), "bottom": p_num(0)}}],
           "background": [{"properties": {"show": p_bool(bool(bg)),
                                          "color": p_color(bg or "#FFFFFF")}}],
           "border": [{"properties": {"show": p_bool(False)}}]}
    return objs, vco

# ------------------------------------------------------------------ theme
os.makedirs(f"{RD}/StaticResources/RegisteredResources", exist_ok=True)
theme = {
    "name": "CO2Theme.json",
    "dataColors": ["#0F6E6E", "#F2A65A", "#4C6EF5", "#E4572E", "#8AB17D",
                   "#B08BBB", "#2F4858", "#F3C969"],
    "foreground": "#1B1F24", "foregroundNeutralSecondary": "#5A6672",
    "background": "#FFFFFF", "backgroundLight": "#F5F7FA", "backgroundNeutral": "#E3E8EF",
    "tableAccent": "#0F6E6E",
    "textClasses": {
        "callout": {"fontSize": 34, "fontFace": "Segoe UI Semibold", "color": "#0F6E6E"},
        "title": {"fontSize": 14, "fontFace": "Segoe UI Semibold", "color": "#1B1F24"},
        "header": {"fontSize": 12, "fontFace": "Segoe UI Semibold", "color": "#1B1F24"},
        "label": {"fontSize": 11, "fontFace": "Segoe UI", "color": "#5A6672"}},
    "visualStyles": {"*": {"*": {
        "background": [{"show": True, "color": {"solid": {"color": "#FFFFFF"}}, "transparency": 0}],
        "border": [{"show": True, "color": {"solid": {"color": "#E3E8EF"}}, "radius": 6}],
        "visualHeader": [{"show": False}],
        "title": [{"show": True, "fontSize": 12, "bold": True, "fontColor": {"solid": {"color": "#1B1F24"}},
                   "alignment": "left"}]}}},
}
theme_name = "CO2Theme.json"
json.dump(theme, open(f"{RD}/StaticResources/RegisteredResources/{theme_name}", "w"), indent=2)

report = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.3.0/schema.json",
    "themeCollection": {
        "baseTheme": {"name": "Fluent2-CY26SU10", "type": "SharedResources",
                      "reportVersionAtImport": {"visual": "2.11.0", "report": "3.4.0", "page": "2.3.1"}},
        "customTheme": {"name": theme_name, "type": "RegisteredResources",
                        "reportVersionAtImport": {"visual": "2.14.0", "report": "3.4.0", "page": "2.3.1"}}},
    "resourcePackages": [
        {"name": "SharedResources", "type": "SharedResources",
         "items": [{"name": "Fluent2-CY26SU10", "path": "BaseThemes/Fluent2-CY26SU10.json", "type": "BaseTheme"}]},
        {"name": "RegisteredResources", "type": "RegisteredResources",
         "items": [{"name": theme_name, "path": theme_name, "type": "CustomTheme"}]}],
    "settings": {"useStylableVisualContainerHeader": True, "exportDataMode": "AllowSummarized",
                 "defaultDrillFilterOtherVisuals": True, "allowChangeFilterTypes": True,
                 "useEnhancedTooltips": True, "useDefaultAggregateDisplayName": True},
}
json.dump(report, open(f"{DEF}/report.json", "w"), indent=2)

# ------------------------------------------------------------------ pages
PAGES = [("a1b2c3d4e5f60101aa01", "Overview"),
         ("a1b2c3d4e5f60102aa02", "Who emits"),
         ("a1b2c3d4e5f60103aa03", "Sources and trends")]
shutil.rmtree(f"{DEF}/pages", ignore_errors=True)
os.makedirs(f"{DEF}/pages")

def page_bg():
    return {"background": [{"properties": {"color": p_color("#F5F7FA")}}]}

def write_page(pid, name, visuals):
    d = f"{DEF}/pages/{pid}"
    os.makedirs(f"{d}/visuals")
    json.dump({"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
               "name": pid, "displayName": name, "displayOption": "FitToPage",
               "height": 720, "width": 1280, "objects": page_bg()},
              open(f"{d}/page.json", "w"), indent=2)
    for vname, v in visuals:
        os.makedirs(f"{d}/visuals/{vname}")
        json.dump(v, open(f"{d}/visuals/{vname}/visual.json", "w"), indent=2)

def chrome(pid, title, subtitle):
    out = []
    objs, vco = textbox([title, subtitle], size=20, color="#1B1F24", semibold=True)
    n, v = visual(pid, 24, 14, 720, 56, "textbox", objects=objs)
    v["visual"]["visualContainerObjects"] = vco
    out.append((n, v))
    objs, vco = textbox([AGENT], size=16, color="#0F6E6E", align="right")
    n, v = visual(pid, 856, 14, 400, 40, "textbox", objects=objs)
    v["visual"]["visualContainerObjects"] = vco
    out.append((n, v))
    objs, vco = textbox([FOOTER], size=10, color="#5A6672")
    n, v = visual(pid, 24, 684, 1232, 30, "textbox", objects=objs)
    v["visual"]["visualContainerObjects"] = vco
    out.append((n, v))
    return out

# ================================================================== page 1
pid = PAGES[0][0]
vs = chrome(pid, "Global CO2 emissions since 1990",
            "Our World in Data country dataset - fossil fuels, cement and land-use-free CO2")
KPI = [(24, "Total CO2 (Mt)", "Total CO2 2024 (Mt)"),
       (330, "CO2 per Capita (t)", "CO2 per Capita 2024 (t)"),
       (636, "CO2 YoY %", "CO2 YoY % (2024)"),
       (942, "CO2 vs 1990 %", "CO2 vs 1990 % (2024)")]
year2024 = {"name": "Filter" + uuid.uuid4().hex[:24],
            "field": {"Column": {"Expression": {"SourceRef": {"Entity": FY}}, "Property": "Year"}},
            "type": "Categorical",
            "filter": {"Version": 2, "From": [{"Name": "d", "Entity": FY, "Type": 0}],
                       "Where": [{"Condition": {"In": {
                           "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "d"}},
                                                       "Property": "Year"}}],
                           "Values": [[{"Literal": {"Value": "2024L"}}]]}}}]},
            "howCreated": "User"}
for x, m, ttl in KPI:
    objs = {"value": [{"properties": {"fontSize": p_num(22), "bold": p_bool(True),
                                      "fontColor": p_color("#0F6E6E")}, "selector": {"id": "default"}}],
            "label": [{"properties": {"fontSize": p_num(11), "fontColor": p_color("#5A6672")},
                       "selector": {"id": "default"}}],
            "fillCustom": [{"properties": {"show": p_bool(False)}, "selector": {"id": "default"}}],
            "outline": [{"properties": {"show": p_bool(False)}, "selector": {"id": "default"}}]}
    n, v = visual(pid, x, 76, 296, 112, "cardVisual",
                  {"queryState": {"Data": {"projections": [meas(m)]}}}, objs,
                  filters=[{**year2024, "name": "Filter" + uuid.uuid4().hex[:24]}], title=ttl)
    vs.append((n, v))

n, v = visual(pid, 24, 196, 780, 292, "lineChart",
              {"queryState": {"Category": {"projections": [col(FY, "Year")]},
                              "Y": {"projections": [meas("Total CO2 (Mt)")]}}},
              {"dataPoint": [{"properties": {"defaultColor": p_color("#0F6E6E")}}]},
              sort={"sort": [{"field": {"Column": {"Expression": {"SourceRef": {"Entity": FY}},
                                                    "Property": "Year"}}, "direction": "Ascending"}]},
              title="Total CO2 by year (Mt)")
vs.append((n, v))

n, v = visual(pid, 816, 196, 440, 478, "barChart",
              {"queryState": {"Category": {"projections": [col(DC, "Country")]},
                              "Y": {"projections": [meas("Total CO2 (Mt)")]}}},
              {"legend": [{"properties": {"show": p_bool(False)}}]},
              sort={"sort": [{"field": {"Measure": {"Expression": {"SourceRef": {"Entity": MEAS}},
                                                     "Property": "Total CO2 (Mt)"}}, "direction": "Descending"}]},
              title="CO2 by country (Mt)")
vs.append((n, v))

n, v = visual(pid, 24, 496, 380, 100, "slicer",
              {"queryState": {"Values": {"projections": [col(FY, "Year")]}}},
              {"data": [{"properties": {"mode": p_str("Between")}}],
               "header": [{"properties": {"show": p_bool(True), "text": p_str("Year range")}}]},
              title=None)
vs.append((n, v))

n, v = visual(pid, 416, 496, 380, 100, "slicer",
              {"queryState": {"Values": {"projections": [col(DC, "Continent")]}}},
              {"data": [{"properties": {"mode": p_str("Dropdown")}}],
               "header": [{"properties": {"show": p_bool(True), "text": p_str("Continent")}}]})
vs.append((n, v))

write_page(pid, PAGES[0][1], vs)

# ================================================================== page 2
pid = PAGES[1][0]
vs = chrome(pid, "Who emits", "Largest emitters, their weight in world emissions, and income vs emissions")

# Top 15 via a visual TopN filter (by Sum of CO2_Mt, top 15 countries)
topn = {
    "name": "Filter" + uuid.uuid4().hex[:24],
    "field": {"Column": {"Expression": {"SourceRef": {"Entity": DC}}, "Property": "Country"}},
    "type": "TopN",
    "filter": {"Version": 2, "From": [
        {"Name": "subquery", "Type": 2, "Expression": {"Subquery": {"Query": {
            "Version": 2,
            "From": [{"Name": "d", "Entity": DC, "Type": 0},
                     {"Name": "f", "Entity": FC, "Type": 0}],
            "Select": [{"Column": {"Expression": {"SourceRef": {"Source": "d"}}, "Property": "Country"},
                        "Name": "c"}],
            "OrderBy": [{"Direction": 2, "Expression": {"Aggregation": {
                "Expression": {"Column": {"Expression": {"SourceRef": {"Source": "f"}},
                                         "Property": "CO2_Mt"}},
                "Function": 0}}}],
            "Top": 15}}}},
        {"Name": "d", "Entity": DC, "Type": 0}],
        "Where": [{"Condition": {"In": {
            "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "d"}},
                                        "Property": "Country"}}],
            "Table": {"SourceRef": {"Source": "subquery"}}}}}]},
    "howCreated": "User"}

n, v = visual(pid, 24, 78, 520, 596, "barChart",
              {"queryState": {"Category": {"projections": [col(DC, "Country")]},
                              "Y": {"projections": [meas("Total CO2 (Mt)")]}}},
              {"legend": [{"properties": {"show": p_bool(False)}}],
               "labels": [{"properties": {"show": p_bool(True)}}]},
              filters=[topn],
              sort={"sort": [{"field": {"Measure": {"Expression": {"SourceRef": {"Entity": MEAS}},
                                                     "Property": "Total CO2 (Mt)"}}, "direction": "Descending"}]},
              title="Top 15 countries by Total CO2 (Mt)")
vs.append((n, v))

n, v = visual(pid, 560, 78, 696, 280, "scatterChart",
              {"queryState": {"Category": {"projections": [col(DC, "Country")]},
                              "X": {"projections": [meas("CO2 per Capita (t)")]},
                              "Y": {"projections": [meas("GDP per Capita ($)")]},
                              "Size": {"projections": [meas("Population")]}}},
              {"legend": [{"properties": {"show": p_bool(False)}}],
               "categoryLabels": [{"properties": {"show": p_bool(False)}}]},
              title="GDP per capita vs CO2 per capita (bubble = population)")
vs.append((n, v))

n, v = visual(pid, 560, 370, 696, 304, "tableEx",
              {"queryState": {"Values": {"projections": [
                  col(DC, "Country"), meas("Total CO2 (Mt)"), meas("Share of Global CO2 %"),
                  meas("Rank by Total CO2"), meas("CO2 YoY %")]}}},
              {},
              sort={"sort": [{"field": {"Measure": {"Expression": {"SourceRef": {"Entity": MEAS}},
                                                     "Property": "Rank by Total CO2"}}, "direction": "Ascending"}]},
              title="Country detail")
vs.append((n, v))
write_page(pid, PAGES[1][1], vs)

# ================================================================== page 3
pid = PAGES[2][0]
vs = chrome(pid, "Sources and trends", "Where the CO2 comes from, by continent, and how carbon intensity is moving")
n, v = visual(pid, 24, 78, 760, 300, "stackedAreaChart",
              {"queryState": {"Category": {"projections": [col(FY, "Year")]},
                              "Y": {"projections": [meas("Coal CO2"), meas("Oil CO2"),
                                                    meas("Gas CO2"), meas("Cement CO2")]}}},
              {"legend": [{"properties": {"show": p_bool(True), "position": p_str("Top")}}]},
              sort={"sort": [{"field": {"Column": {"Expression": {"SourceRef": {"Entity": FY}},
                                                    "Property": "Year"}}, "direction": "Ascending"}]},
              title="Coal / Oil / Gas / Cement CO2 over time (Mt)")
vs.append((n, v))

n, v = visual(pid, 800, 78, 456, 300, "matrix",
              {"queryState": {"Rows": {"projections": [col(DC, "Continent"), col(DC, "Country")]},
                              "Values": {"projections": [meas("Total CO2 (Mt)"),
                                                         meas("Share of Global CO2 %")]}}},
              None, title="Continent > Country")
vs.append((n, v))

n, v = visual(pid, 24, 394, 1232, 280, "lineChart",
              {"queryState": {"Category": {"projections": [col(FY, "Year")]},
                              "Y": {"projections": [meas("Carbon Intensity (kg per $ GDP)")]}}},
              {"dataPoint": [{"properties": {"defaultColor": p_color("#E4572E")}}],
               "legend": [{"properties": {"show": p_bool(False)}}]},
              sort={"sort": [{"field": {"Column": {"Expression": {"SourceRef": {"Entity": FY}},
                                                    "Property": "Year"}}, "direction": "Ascending"}]},
              title="Carbon intensity trend (kg CO2 per $ of GDP)")
vs.append((n, v))
write_page(pid, PAGES[2][1], vs)

json.dump({"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
           "pageOrder": [p[0] for p in PAGES], "activePageName": PAGES[0][0]},
          open(f"{DEF}/pages/pages.json", "w"), indent=2)
print("report written:", sum(len(os.listdir(f"{DEF}/pages/{p[0]}/visuals")) for p in PAGES), "visuals")
