# Benchmark prompt (verbatim)

This is the exact brief this repository answers, recorded word for word.

---

# TASK: Build a Power BI dashboard end-to-end (benchmark run)

You are one of several AI agents getting this exact same prompt. The results will be
compared for token usage, wall-clock time and output quality. Work on your own. Do not
ask clarifying questions. Make reasonable assumptions and write them down in RUN_LOG.md.

## 0. Identity and logging (do this first)
- Find out your agent name and exact model ID (for example "Claude Code / claude-opus-5-5").
  Call this <AGENT_MODEL>.
- Create a folder ./bench-<agent>-<yyyyMMdd-HHmm>/ and do all work inside it.
- Create RUN_LOG.md and record the START timestamp (ISO 8601, with seconds) right away.
- For each phase below, log: the phase start and end time, what you did, any errors, and
  every retry or fix.
- At the very end, record the END timestamp and the total elapsed time.

## 1. Data: use this exact public dataset (no substitutes)
Our World in Data, CO2 and greenhouse gas emissions (CC BY 4.0):
https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv

- Keep only real countries (rows where iso_code is a 3-letter code, so drop aggregates
  like "World", "Europe" and "High-income countries").
- Keep years 1990 and later.
- Columns needed: country, iso_code, year, population, gdp, co2, co2_per_capita,
  coal_co2, oil_co2, gas_co2, cement_co2, methane, nitrous_oxide, share_global_co2.
- Add continent (and region if you can) for each country, either from a public mapping or
  from a small mapping table you build. Record the source in RUN_LOG.md.

## 2. Semantic model: star schema, best practice, no circular dependencies
Build the model with the Fabric / Power BI semantic model tooling you have (the Fabric
skill, TMDL or PBIP). It must meet ALL of these rules:

Structure
- Fact_Emissions: one row per country per year. Keys and numeric columns only.
- Dim_Country: CountryKey, Country, ISO3, Continent, Region.
- Dim_Year: Year, Decade, plus a full Dim_Date if you want one. Mark it as the date table
  if you build Dim_Date.
- Optional: Dim_Source (Coal/Oil/Gas/Cement) for the source breakdown. Do this by
  unpivoting into a separate fact table or a field parameter. Do NOT build a
  many-to-many bridge.

Relationships
- Only one-to-many, from dimension to fact.
- Single cross-filter direction only. No bidirectional relationships anywhere.
- No inactive relationships unless a measure uses USERELATIONSHIP and you write down why.
- No relationships between two fact tables or between two dimension tables
  (no snowflaking).

Avoiding circular dependencies (state in RUN_LOG.md how you checked each one)
- No calculated columns that use CALCULATE or a context transition on a table that
  takes part in a relationship.
- No calculated tables built from other calculated tables that loop back.
- Do surrogate keys and transformations in Power Query or upstream, not in DAX
  calculated columns.
- Turn off Auto date/time.

Measures (put them in a dedicated "_Measures" table, with format strings and descriptions)
- Total CO2 (Mt), CO2 per Capita (t), Population, GDP
- CO2 YoY %, CO2 vs 1990 % (Kyoto baseline)
- Share of Global CO2 %, Coal / Oil / Gas / Cement CO2
- Carbon Intensity (kg CO2 per $ GDP)
- Rank by Total CO2 (RANKX across countries, respecting filters)
- Use DIVIDE() for every ratio. No implicit measures in visuals.

Hygiene
- Hide foreign keys and raw numeric columns that measures already cover.
- Use consistent naming, set data categories (Country gets Country/Region), and set
  sort-by columns where needed.

Validation: run DAX queries that prove these:
- The total of Total CO2 for 2022 matches the CSV sum to within 0.1%.
- The model refreshes with no errors.
- No relationship is bidirectional.
- Record the query results in RUN_LOG.md.

## 3. Report: 3 pages, Power BI (PBIR/PBIP), publish if you have access
Page 1 "Overview"
- KPI cards: Total CO2, CO2 per Capita, YoY %, vs 1990 %
- Line chart: Total CO2 by Year
- Filled map or bar chart: CO2 by Country
- Slicers: Year range, Continent

Page 2 "Who emits"
- Top 15 countries by Total CO2 (bar)
- Scatter: GDP per capita vs CO2 per capita, bubble size = Population
- Table: Country, Total CO2, Share %, Rank, YoY %

Page 3 "Sources and trends"
- Stacked area: Coal / Oil / Gas / Cement over time
- Decomposition or matrix: Continent > Country
- Carbon Intensity trend line

Every page MUST include:
- A text box in the top-right corner reading "Created using <AGENT_MODEL>" in at least
  12pt, so anyone viewing can see which model built it.
- A footer: "Data: Our World in Data (CC BY 4.0) | Built <date>".
- A consistent theme, readable titles, no overlapping visuals, and every visual bound to
  explicit measures.

## 4. Deliverables (in the run folder)
- The PBIP project (semantic model + report), published to the Fabric workspace if you
  have access.
- RUN_LOG.md with: START/END timestamps, phase timings, assumptions, errors and retries,
  validation results, and the model checklist (each rule above marked PASS or FAIL with
  evidence).
- SUMMARY.md, under 15 lines: what you built, what is left incomplete, any known issues,
  and your own token usage if your tool exposes it (write "not available" otherwise).

**Stop when the deliverables are done. Do not polish beyond the spec.**
**make sure create new dataset if it exist dont overwrite**

---

## How this run answered it

- Agent: **Hermes Agent / deepseek/deepseek-v4.1-flash-1017**
- Run folder: `bench-hermes-deepseek-v4.1-20261109-2237/` (this repository root)
- Published model: `CO2 Emissions Model (Hermes deepseek-v4.1)` — Fabric Learning Workspace
- Published report: `CO2 Emissions Dashboard (Hermes deepseek-v4.1)`
- Result summary and deviations: `SUMMARY.md`; full phase log and checklist: `RUN_LOG.md`
