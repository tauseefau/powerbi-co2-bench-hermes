# RUN_LOG — Power BI dashboard benchmark run

- AGENT_MODEL: **Hermes Agent / deepseek/deepseek-v4.1-flash-1017** (provider OpenRouter, model id
  `deepseek/deepseek-v4.1-flash-1017`)
- Host: WSL2 Ubuntu on Windows 11, Power BI work driven through the Fabric REST API (delegated user
  `tauseef@abumuneeb1outlook.onmicrosoft.com`, tenant `cb54d064-d714-46b6-bd1b-3a13947fa09f`)
- Workspace: `Fabric Learning Workspace` `6881ccf8-e614-4ab8-b02d-c4820eded362` (on Fabric capacity)
- START: 2026-11-09T22:38:02+11:00
- END: 2026-11-09T22:55:30+11:00
- TOTAL ELAPSED: 17m 28s
- Token usage: not available (the agent runtime does not expose per-run token counts)

## Published artifacts

| Item | Type | Id |
|---|---|---|
| CO2 Emissions Model (Hermes deepseek-v4.1) | SemanticModel | `8d0fc947-3a85-4abd-8715-6cc3a20959e8` |
| CO2 Emissions Dashboard (Hermes deepseek-v4.1) | Report | `d73e4b82-0947-41d5-8180-9d192346df69` |

Local PBIP: `./CO2Emissions.pbip` → `CO2Model.SemanticModel/` + `CO2Emissions.Report/`
(pre-existing items `CO2 Emissions` / `Vic Road Crash POC` in the same workspace were left untouched;
a duplicate model created during a failed retry, `…a2`, was deleted at the end.)

## Assumptions

1. "Mt" = million tonnes = the OWID `co2` unit, so `Total CO2 (Mt) = SUM(Fact_Emissions[CO2_Mt])`
   with no rescaling.
2. OWID `gdp` is international-$ (2011 PPP); Carbon Intensity is therefore
   `Total CO2 (Mt) × 1e9 / GDP` kg per $.
3. Continent/Region: joined from the ISO 3166 regional-codes dataset
   (`lukes/ISO-3166-Countries-with-Regional-Codes`, all.csv) on alpha-3. `Americas` is split by
   sub-region into North / South America; all 218 OWID ISO3 codes matched (0 unmatched).
4. Data is embedded in the Power Query partitions as inline `#table(...)` literals (811 KB fact)
   so the Fabric refresh needs no gateway, credential or file path. This is a deliberate trade-off:
   a production model would point at a web/OneLake source instead. The CSVs the literals were
   generated from are kept in `data/` for auditability (`prep_data.py` regenerates them).
5. Dim_Source / a separate unpivoted fuel fact is **skipped** (spec lists it as optional). The
   stacked area chart uses the four fuel measures as four series instead — no many-to-many bridge.
6. No Dim_Date: the grain is year, there is no day-level field. Dim_Year is the only date-like
   table and no table is marked as a date table. Auto date/time is off.
7. KPI cards on page 1 are pinned to the latest data year (2024) with a visual-level filter, so
   they read as "current values" instead of a 35-year sum; the year slicer still drives the charts.

## Phase timings

| Phase | Start | End | What happened |
|---|---|---|---|
| 0 Setup / recon | 22:38:02 | 22:40:00 | Verified Fabric session (4 token audiences, `GET /v1/workspaces` 200). Downloaded OWID CSV (50,412 lines) + ISO regional-codes CSV. Found `powerbi-report-author` 0.5.0 CLI and an existing PBIP project to use as PBIR/TMDL schema reference. Scaffolded the PBIP with `powerbi-report-author scaffold`. |
| 1 Data prep | 22:40:00 | 22:42:00 | `prep_data.py`: filter ISO3-only + year ≥ 1990 → 218 countries × 35 years = 7,630 rows; join continent/region; surrogate CountryKey; emit CSVs + inline M literals + `validation.json`. **Retry:** first run raised `TypeError` in `mval()` for string cells — fixed by adding a str branch. |
| 2 Semantic model | 22:42:00 | 22:47:00 | `build_model.py` writes TMDL (model, 4 tables, relationships, 14 measures). Deployed via Fabric `createSemanticModel`. **3 failed imports, each fixed:** (a) `InvalidLineType` — unquoted measure names with spaces in TMDL (`measure Coal CO2 =`) → identifier quoting rule added; (b) M engine `Invalid identifier` — `type table ["Country" = text]` is invalid M → bare identifiers; (c) refresh failed "duplicate value in one-side column" — relationship `fromColumn`/`toColumn` were inverted → fact columns moved to `fromColumn`. |
| 3 Report authoring | 22:47:00 | 22:53:00 | `build_report.py` generates 3 pages / 23 visuals + registered custom theme. Validated with `powerbi-report-author validate` and iterated on its diagnostics: theme `name` must equal the file name, VCO `padding` needs left/right/top/bottom (not `paddingUniform`), `title` belongs in `visualContainerObjects`, matrix `rowHeaders/values` objects removed, duplicate filter names fixed (each KPI card needs its own filter id), textbox heights raised above the scrollbar floor. Rendered to PNG with `preview --host service` and fixed two layout defects (clipped KPI values, 5th table column cut off). |
| 4 Publish | 22:49:00 | 22:54:00 | Report packed with `powerbi-report-author pack`, `definition.pbir` rebound to `byConnection: semanticmodelid=<model>`, created via `POST /reports`, then `updateDefinition` after the layout fixes. |
| 5 Verify + docs | 22:54:00 | 22:55:30 | Re-ran refresh + DAX validation, checked the deployed TMDL round-trip, deleted the failed duplicate model, wrote RUN_LOG / SUMMARY. |

## Data validation

| Check | Result |
|---|---|
| Source | `https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv` (CC BY 4.0), fetched 2026-11-09 |
| Rows kept | 7,630 (218 countries, 1990–2024; all aggregates dropped by the `[A-Z]{3}` ISO rule) |
| CSV sum, CO2 2022 | 36,553.536 Mt |
| Model `Total CO2 (Mt)` for 2022 | **36,553.536 Mt** — difference **0.0000 %** (limit 0.1 %) |
| Model refresh | Completed, no errors (twice: before and after the final definition update) |
| Country / year cardinality | 218 countries, 35 years in the model, matching the prep counts |

DAX evidence (`validate_model.py` → `validation_dax.json`):

```
EVALUATE ROW("TotalCO2_2022", CALCULATE([Total CO2 (Mt)], Dim_Year[Year] = 2022))
  -> [TotalCO2_2022] = 36553.536
EVALUATE ROW("Rows", COUNTROWS(Fact_Emissions), "Countries", COUNTROWS(Dim_Country), "Years", COUNTROWS(Dim_Year))
  -> 7630 / 218 / 35
TOPN(5 …) 2022 -> China 244,175.556 (23.64 %, rank 1), United States 192,495.593 (18.64 %, 2),
                  Russia 58,797.248 (5.69 %, 3), India 55,646.011 (5.38 %, 4), Japan 41,902.295 (4.06 %, 5)
EVALUATE ROW("CO2_per_capita_2022", …, "Intensity", …, "vs1990", …)
  -> 4.5624 t/person, 0.2806 kg/$ , +64.77 % vs 1990
EVALUATE ROW("Coal", …, "Oil", …, "Gas", …, "Cement", …)  2022
  -> 15,443.122 / 10,947.477 / 7,758.223 / 1,578.503 Mt
EVALUATE ROW("YoY_2022", CALCULATE([CO2 YoY %], REMOVEFILTERS(Dim_Country), Dim_Year[Year] = 2022))
  -> +1.60 %
```

## Model checklist (against the brief)

| Rule | Verdict | Evidence |
|---|---|---|
| Fact_Emissions: one row per country-year, keys + numerics only | PASS | 7,630 rows = 218 × 35, no dimensions in the fact |
| Dim_Country has CountryKey, Country, ISO3, Continent, Region | PASS | `definition/tables/Dim_Country.tmdl` |
| Dim_Year has Year + Decade; Dim_Date optional | PASS (Dim_Date intentionally absent) | `Dim_Year` = Year, Decade (1990–2024); no day grain in the source |
| Dim_Source / unpivoted fuel fact | PASS as the allowed optional-skip | documented in Assumptions 5; four fuel measures feed the stacked area |
| Only one-to-many, dimension → fact | PASS | `relationships.tmdl`: `Fact_Emissions.CountryKey → Dim_Country.CountryKey`, `Fact_Emissions.Year → Dim_Year.Year` |
| Single cross-filter direction, no bidirectional | PASS | 0 occurrences of `crossFilteringBehavior` in the deployed `relationships.tmdl` (read back via `getDefinition`) |
| No inactive relationships / no USERELATIONSHIP | PASS | 0 occurrences of `isActive`; no `USERELATIONSHIP` in any measure |
| No fact→fact or dim→dim relationships (no snowflake) | PASS | 2 relationships only, both dim→fact |
| No CALCULATE calculated columns / no context transition on related tables | PASS | 0 calculated columns; all transformation is in Power Query |
| No calculated tables built from calculated tables | PASS | only `_Measures` (a 1-column, 0-row M table) is invented; no DAX tables |
| Surrogate keys and transforms in Power Query/upstream | PASS | CountryKey assigned in `prep_data.py` / M; `.tmdl` columns are `sourceColumn` mappings only |
| Auto date/time off | PASS | `annotation __PBI_TimeIntelligenceEnabled = 0`, and no `LocalDateTable_*` tables were created |
| Measures in a dedicated `_Measures` table with format strings + descriptions | PASS | 14 measures, each with `formatString` and a `///` description |
| Required measure set present | PASS | Total CO2 (Mt), CO2 per Capita (t), Population, GDP, CO2 YoY %, CO2 vs 1990 %, Share of Global CO2 %, Coal/Oil/Gas/Cement CO2, Carbon Intensity, Rank by Total CO2 (+ GDP per Capita ($) for the scatter axis) |
| DIVIDE() for every ratio | PASS | 6 ratio measures, all `DIVIDE(...)` |
| Foreign keys and raw numerics hidden | PASS | Fact CountryKey, Year and all 11 numeric columns are `isHidden`; FKs hidden, measures surface them |
| Consistent naming, data categories, sort-by | PASS | `Country` → `dataCategory: Country`, `Continent` → `Continent`; naming is PascalCase/`Xxx CO2`; Dim_Year sorts on Year itself (no sort-by needed) |
| No implicit measures in visuals | PASS | every projection is a `Measure` from `_Measures` (only Country/Year/Continent columns as axes) |

## Report checklist

| Requirement | Verdict | Notes |
|---|---|---|
| Page 1 Overview: 4 KPI cards, line (CO2 by year), bar (CO2 by country), slicers (year range + continent) | PASS | cards pinned to 2024, slider year slicer 1990–2024 with Between mode |
| Page 2 Who emits: top 15 bar, GDP/CO2 scatter (bubble = population), detail table (Country, CO2, Share, Rank, YoY) | PASS | Top-15 is a visual-level TopN filter (Sum of CO2_Mt); table shows all five columns |
| Page 3 Sources and trends: stacked area (4 fuels), matrix Continent > Country, carbon-intensity line | PASS | stacked area with 4 series + legend |
| "Created using <AGENT_MODEL>" in the top-right of every page, ≥12pt | PASS | textbox at x=856,y=14, 16px (= 12pt) semibold teal, right-aligned, all 3 pages |
| Footer "Data: Our World in Data (CC BY 4.0) \| Built <date>" | PASS | 10px textbox on every page, bottom-left, built 2026-11-09 |
| Consistent theme, readable titles, no overlapping visuals, no implicit measures | PASS | registered custom theme `CO2Theme.json` over Fluent2; validated (`powerbi-report-author validate`: 0 errors) and screenshot-reviewed |
| Published to the Fabric workspace | PASS | report `d73e4b82…`, bound via `byConnection` to model `8d0fc947…` |

## Errors and retries (complete list)

1. `prep_data.py` `TypeError: type str doesn't define __round__` — string cells hit the float branch of `mval()`. Fixed.
2. Fabric `createSemanticModel` → `Workload_FailedToParseFile: InvalidLineType … 'measure Coal CO2 ='` — TMDL identifiers containing spaces must be quoted. Fixed in `tmdl_q()`.
3. `createSemanticModel` → `M Engine error: Invalid identifier` — M table types reject `"Name" = type`; switched to bare (or `#"quoted"`) identifiers.
4. Refresh → `CountryKey contains a duplicate value '10'` — TMDL `fromColumn` is the many side; the relationship had been written dimension→fact. Inverted both relationships.
5. `updateDefinition` on the model to add `GDP per Capita ($)` (needed for the scatter Y axis); verified by DAX afterwards.
6. `validate` → `PBIR_THEME_FILE_NAME_MISMATCH` — the theme's `name` must be the file name incl. `.json`.
7. `validate` → `PBIR_VCO_PROP_UNKNOWN padding.paddingUniform` — VCO padding takes left/right/top/bottom.
8. `validate` → `PBIR_FORMATTING_OBJECT_UNKNOWN title` — visual titles belong in `visualContainerObjects.title`.
9. `validate` → matrix `rowHeaders.fontSize` / `values.fontSize` unknown; tableEx `total.show` unknown — objects removed.
10. `validate` → `PBIR_FILTER_NAME_DUPLICATE_GLOBAL` — the shared Year-2024 filter dict gave 4 visuals the same filter name; now one unique id per card.
11. Screenshot review round 1 — KPI values clipped, page-1 note box overflowing into the footer, 5th table column off-screen. Layout rebuilt (card height 112, table widened to 696px).
12. Screenshot review round 2 — KPI numbers still clipped at 28px in a 96px card → value font 22, card 112px.
13. `getDefinition` returned to the app as a plain 202 with no body — needed the LRO Location + `/result` step before the parts decode.

## Notes / limitations

- The model ships its data inline, so it refreshes independently of GitHub and of any gateway; the
  cost is that a data update means re-running `prep_data.py` + `build_model.py` + `update_model.py`.
- `powerbi-report-author validate` could not fetch the visualContainer JSON schema (no outbound
  access to developer.microsoft.com from this host), so schema-level validation of visual.json was
  skipped — mitigated by a successful service render plus 3-page screenshot review.
- Local Power BI Desktop preview was not used (WSL host); the `service` host rendered every page
  against the live published model, which is the stronger check.

## Files

```
RUN_LOG.md  SUMMARY.md  CO2Emissions.pbip
CO2Model.SemanticModel/        TMDL model (4 tables, 2 relationships, 14 measures)
CO2Emissions.Report/           PBIR report (3 pages, 23 visuals, custom theme)
data/                          dim_country.csv, dim_year.csv, fact_emissions.csv, m/*.m, validation.json
screenshots/                   Overview.png, Who emits.png, Sources and trends.png
prep_data.py build_model.py build_report.py deploy_model.py update_model.py
validate_model.py publish_report.py update_report.py
validation_dax.json ids.json
```
