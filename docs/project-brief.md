# Projekti ulevaade

Viimati uuendatud: 06.04.2026

## Mis see on

Portfelli analuusi platvorm juuniorkaevanduse aktsiatele (kuld, hobe, vask, liitium jm) Austraalias ja Kanadas. Streamlit veebirakendus, mis aitab kliendil teha investeerimisotsuseid: mida osta, muua, vahetada ja kui palju igasse positsiooni paigutada.

## Klient

- **Nimi:** Kees (KC) Van Middendorp
- **Ettevote:** Tiresias / Directiecoach.nl, Holland
- **Taust:** endine IT-firma direktor (Microsoft 365), praegu executive coach. Pole programmeerija.
- **Eesmark:** ehitada usaldusvaarne investeerimissusteem, mis asendab tema praegust ChatGPT-pohist tookeskkonda. Pikemas perspektiivis soovib ta investeerimisest sissetulekut teenida ja toolt loobuda.

## Miks ta seda vajab

Ta on ehitanud oma investeerimissusteemi ChatGPT-s (versioon 6.1), aga see ei hoia seisu — ChatGPT muudab pidevalt ja pole jarjepidev. Ta vajab fikseeritud, usaldusvaarnest tarkvara, mis toetab tema igapaevast otsustusprotsessi.

## Kokkulepitud tingimused

- **Hind:** $1,950 ($350 + $350 + $650 + $600)
- **Makse:** tukitoo (project-based, milestoned)
- **Ajapress:** puudub, nadalane hilinemine OK
- **Skoop:** klient ise utles "when I go out of scope just give me a warning and then we discuss it"
- **Suhtlus:** Upwork kaudu, parast lepingut voimalik Slack/email
- **Tulevikupotentsiaal:** klient mainis lisaprojekte (REIT-id, teised turud)
- **Trade execution:** VALJA JAETUD esimesest versioonist (kliendi manual + meie ettepanek, klient noustus)

## Milestoned

**Milestone 1 — $350 — VALMIS, MAKSTUD**
Review developer pack V6.1, technical design, working PoC (IB API ingestion).

**Milestone 2 — $350 — AKTIIVNE, RAHASTATUD**
Scoring, risk, EV, decision, rebalance engines + Daily/Weekly/Monthly dashboards + PDF export.
Exit: tais susteem — skoori sisestamine, soovitused, PDF eksport.

**Milestone 3 — $650**
Unit/integration testid, config cleanup, dokumentatsioon, bug fixes tagasisidest, handover.
Exit: production-ready susteem dokumentatsiooniga.

**Milestone 4 — $600 (UUS, ootab kliendi kinnistust)**
Import module + dual report system.
- Teksti/CSV parser segastele junior miner nimekirjadele
- Ticker normaliseerimine, V7 scoring, portfelli vordlus, swap detection
- 5 Streamlit tabi
- Private PDF (taielik execution detail)
- Shareable Tiresias-branded PDF (saniteeritud, ilma finantsidetailideta)

**Ei sisaldu (eraldi lisatoo):**
- Automaatne scoring pipeline (hybrid auto-score + override)
- News and Intelligence Engine (uudised, filings, catalyst, insider activity)
- Automation ja valisalerting
- Automaatne trade execution IB API kaudu

## Tehniline alus

- **Frontend:** Streamlit (klient juba kasutab, jookseb tema laptopis)
- **Andmed:** IB API (ib_async) portfelli andmeteks
- **Andmebaas:** SQLite (skooride ja EV andmete persisteerimine)
- **Hosting:** lokaalne (kliendi laptop), hiljem voimalik datacenter
- **Autentimine:** pole vaja (ainult tema kasutab)
- **Config:** YAML failid kaalude, lavede, rubriikide ja seadistuste jaoks
- **PDF:** reportlab (institutional-quality PDF raportid)

## Susteemi arhitektuur (M2 seis)

### Andmevoog

```
IB API / CSV upload
    |
ingestion.py -> normalize_holdings()
    |
persistence.py -> load_all_scores() + load_ev_data()
    |
scoring.py -> enrich_with_scores()
    |
ev_engine.py -> enrich_with_ev()
    |
risk_engine.py -> enrich_with_risk()
    |
decision_engine.py -> enrich_with_decisions()
    |
rebalance_engine.py -> calculate_target_weights()
    |
enriched DataFrame -> dashboard render() + pdf_generator.generate()
```

### Moodulid

**modules/ingestion.py** — IB API uhendus (ib_async), CSV import, normaliseerimine, valideerimine.
WSL2 -> Windows TWS uhendus kasutab networkingMode=mirrored .wslconfig-is.

**modules/persistence.py** — SQLite andmebaas (data/processed/scoring_data.db).
Tabelid: scores (10 kriteeriumit + final_score), ev_data (upside, probability, downside, catalyst, ev_raw, ev_adjusted, tier), portfolio_snapshots (ajalugu).

**modules/scoring.py** — kaalutud skoor 10 kriteeriumiga. Kaalud config/settings.yaml-st, rubriigid config/scoring_rubrics.yaml-st. Iga kriteerium 0-10, tulemus kaalutud keskmine.

**modules/ev_engine.py** — Expected Value arvutus.
Valem: `EV_raw = (upside * probability) - downside`, `EV_adjusted = EV_raw * catalyst_multiplier`.
Catalyst multipliers: near_term=1.2, mid_term=1.0, long_term=0.8.
Tier-id EV pohjal: core (>=5.0), core_min (>=4.0), secondary (>=3.0), speculative (<3.0).

**modules/risk_engine.py** — risk skoor 5-10 (5=madal, 10=kõrge).
Pohineb score ja EV lavenditel (konfigureeritav settings.yaml-s).
Skooriata positsioonid saavad riski 7 (unknown = moderate).
Risk >= 9 triggerib SELL soovituse ja swap-otsingu.

**modules/decision_engine.py** — otsustusmootor.
Prioriteet: SELL > BUY > ADD > HOLD > NO_DATA.
Puuduvad skoorid (None/NaN) -> NO_DATA (v.a. risk >= sell_threshold -> SELL).

| Otsus | Tingimus |
|-------|----------|
| BUY | score >= 8.4 JA ev >= 4.5 |
| ADD | score >= 7.0 JA ev >= 5.0 |
| HOLD | score >= 7.0 |
| SELL | risk >= 9 VOI score < 7.0 |
| NO_DATA | score voi EV puudub |

Swap-loogika: otsib portfellist paremaid alternatiive risk >= 9 positsioonidele.
Swap trigger: buy_ev >= sell_ev * 1.25 JA improvement >= 1.0.

**modules/rebalance_engine.py** — target kaalud EV tier-i pohjal, iteratiivne normaliseerimine max 25% cap-iga.
Constraint kontroll: max positsioon 25%, max regioon 45%, max commodity 30%.

### Dashboardid

**dashboards/daily.py** — taktikaline igapaevaulevaade.
- Andmete laadimine (IB API voi CSV upload)
- Portfolio kokkuvote (koguväärtus, positsioonide arv)
- Decision Dashboard tabel (score, EV, risk, action, kaalud) — värvikoodidega
- Risk Flags (risk >= 9 positsioonid)
- Swap Candidates (paremate alternatiivide soovitused)
- Score Input (10 slaiderit + EV sisendid, reaalajas preview, salvestamine SQLite-i)
- PDF eksport

**dashboards/weekly.py** — nadalane portfellihaldus.
- Koondmetriks (keskmine score, EV, kõrge riski arv)
- Taielik scoring tabel (koik 10 kriteeriumit iga positsiooni kohta)
- Allocation Gap tabel (current vs target vs delta)
- Rebalance plaan (trim/sell + add, neto rahavoog)
- Constraint violations (regioon, commodity, kontsentratsioon)
- Top 5 ideed EV jargi
- PDF eksport

**dashboards/monthly.py** — strateegiline kuu ulevaade.
- Performance kokkuvote (parim/halvim positsioon unrealized P/L jargi)
- Commodity ekspositsioon (kaal, positsioonide arv, max limit, staatus)
- Region ekspositsioon (jurisdictioni jargi)
- Strateegiline positsioneerimine (core/secondary/speculative jaotus)
- Taielik portfelli tabel
- PDF eksport

**dashboards/shared.py** — jagatud loogika: get_db_path(), load_and_enrich() (kogu enrichment pipeline).

**dashboards/components.py** — custom HTML alert komponendid (alert_info, alert_success, alert_warning, alert_error) projekti varvipaletiga.

### PDF raportid

**reports/pdf_generator.py** — reportlab-pohised raportid.
- PortfolioPDFReport baasklass (header, footer, tabelid, styling)
- DailyPDFReport — executive summary, otsuste tabel, risk lipud
- WeeklyPDFReport — scoring tabel, rebalance plaan, top 5 ideed
- MonthlyPDFReport — taielik portfelli tabel, tier jaotus

PDF kasutab sama enriched DataFrame'i mis dashboard — loogika ei lahkne.

## Varvipalett

Labi kogu rakenduse ja PDF-ide kasutatakse uhte varvipaletti:

| Varv | Hex | Kasutus |
|------|-----|---------|
| Dusk Blue | #355070 | Sidebar taust, peamine accent, ADD action, PDF header |
| Dusty Lavender | #6d597a | Metric labelid, info alertide aarise |
| Sage Green | #6b8f71 | BUY action, success alertid |
| Rosewood | #b56576 | Warning alertide aarise |
| Light Coral | #e56b6f | SELL action, error alertid, risk lipud |
| Light Bronze | #eaac8b | HOLD action, aktiivne nav link, sidebar accent |

Streamlit teema (.streamlit/config.toml): primaryColor=#355070, secondaryBg=#f5f0eb.
Sidebar navigatsioon: custom HTML lingid (mitte Streamlit radio/nupud).

## Scoring mudel

### 10 kriteeriumit (settings.yaml)

| # | Kriteerium | Kaal |
|---|-----------|------|
| 1 | Geology / Deposit Quality | 20% |
| 2 | Discovery Probability | 15% |
| 3 | Scale Potential | 15% |
| 4 | Management Quality | 10% |
| 5 | Jurisdiction | 10% |
| 6 | Catalysts (12-24m) | 10% |
| 7 | Capital Structure | 5% |
| 8 | Market Positioning | 5% |
| 9 | Strategic Value | 5% |
| 10 | ESG / Permitting | 5% |

Iga kriteeriumil on anchored scoring rubric (config/scoring_rubrics.yaml) viie vahemikuga (9-10, 7-8, 5-6, 3-4, 0-2).

### Valemid

- **Weighted Score** = sum(score_i * weight_i), kaalud summeeruvad 1.0
- **EV_raw** = (upside * probability) - downside
- **EV_adjusted** = EV_raw * catalyst_multiplier
- **Risk** = 5-10 skaala, pohineb score ja EV lavenditel
- **Decision** = BUY/ADD/HOLD/SELL/NO_DATA prioriteediga

### Position sizing

| Tier | EV lavend | Kaal |
|------|----------|------|
| Core | EV >= 5.0 | 6-10% |
| Secondary | EV 3.0-5.0 | 3-6% |
| Speculative | EV < 3.0 | 1-3% |

### Portfolio constraints

- Max uks positsioon: 25%
- Max regioon: 45%
- Max commodity: 30%
- Core target: 60%, Rising target: 40%

## Tuleviku visioon (kliendi V1.1-V2.0)

- V1.0: manual 10 criteria + anchored rubrics + weights (= praegune MVP)
- V1.1: + confidence score + penalty rules
- V1.2: + stage-specific weights
- V1.3: + peer-relative undervaluation
- V1.4: backtest + recalibrate
- V2.0: hybrid automation

**Kliendi soovitatud penalty rules:**
- funding < 4 -> max total score capped at 7.0
- jurisdiction < 3 -> watchlist risk minimum 8
- capital structure < 3 -> undervaluation cannot exceed 7
- liquidity < 2 -> position size cap at 1/2 normal
- permitting < 4 for developer -> automatic red flag

**Kliendi soovitatud 4-kihiline mudel:**
- Layer A: Asset Quality (geology, scale, grade, strategic relevance)
- Layer B: Execution Quality (management, funding, capital structure, catalyst path)
- Layer C: External Risk (jurisdiction, permitting, market/liquidity risk)
- Layer D: Market Opportunity (undervaluation, upside, EV)

## Testid

69 testi, koik labitud (06.04.2026):
- test_ingestion.py — CSV parse, normaliseerimine, valideerimine
- test_scoring.py — kaalutud skoor, valideerimine, rubriigid
- test_ev_engine.py — EV valem, catalyst multipliers, tier mapping
- test_risk_engine.py — score/EV -> risk mapping, flags, override
- test_decision_engine.py — BUY/ADD/HOLD/SELL/NO_DATA reeglid, NaN handling
- test_rebalance_engine.py — target kaalud, trim/add, constraints
- test_persistence.py — SQLite save/load round-trip, upsert

## Allikdokumendid

- `docs/Developer_Pack_V6_1.md` — kliendi manual (10-lk spetsifikatsioon)
- `docs/build-streamlit-...md` — algne toopostitus, AI analuus, proposal
- `communication/upwork_chat.txt` — kogu Upwork suhtlus
- `communication/meeting-1.txt` — esimese kone transkript
- `communication/hybrid-scope-message.txt` — hybrid vs MVP sonum
