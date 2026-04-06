# Portfolio Intelligence V7 — ulevaade

## Mis see on?

Streamlit veebirakendus, mis aitab hallata juuniorkaevanduse aktsiate portfelli. Sa laadid oma Interactive Brokers portfelli andmed rakendusse, skooritad iga aktsiat 10 kriteeriumi jargi, ja susteem utleb sulle: mida osta, muua, hoida voi vahetada, ning kui palju igasse positsiooni paigutada.

Rakendus jookseb lokaalselt sinu arvutis — keegi teine sellele ligi ei paase.

## Kuidas kaivitada

```
streamlit run app.py
```

Avaneb brauser aadressil `localhost:8501`. Vasakul kulgribal on kolm lehte: **Daily**, **Weekly**, **Monthly**.

## Daily — igapaevane toolaud

See on peamine leht, kus sa igapaevaselt tootad.

### 1. Andmete laadimine

Kaks valikut:
- **IB API** — vajuta "Load from IB", rakendus uhendub sinu TWS-iga ja tombab portfelli automaatselt
- **CSV Upload** — laadi ules IB ekspordi CSV-fail (kui TWS pole avatud)

### 2. Decision Dashboard

Tabel koigi positsioonidega. Iga aktsia kohta naed:
- **Score** — sinu antud kaalutud skoor (0-10). Arvutatakse 10 kriteeriumi kaalutud keskmisena. Korge skoor tahendab kvaliteetset ettevotet.
- **Expected Value** — oodatav vaartus. Kui suur on potentsiaalne tootlus arvestades tousustsenaariumi toenaosust ja voimalikku kahjumit. Valem: (upside x toenaosus) - downside, korrigeeritud katalusaatori ajastusega.
- **Risk** — riskiskoor 5-10. 5-6 = madal risk (hea), 7-8 = nork positsioon, 9-10 = muu-kandidaat. Arvutatakse automaatselt Score ja EV pohjal.
- **Action** — susteemi soovitus, mida selle aktsiaga teha:
  - **BUY** (roheline) — tugev ost: score >= 8.4 ja EV >= 4.5
  - **ADD** (sinine) — suurenda positsiooni: score >= 7.0 ja EV >= 5.0
  - **HOLD** (pronks) — hoia: score >= 7.0, aga EV pole piisavalt korge ostmiseks
  - **SELL** (punane) — muu: risk >= 9 voi score liiga madal
  - **No Score** (hele) — skoori pole veel sisestatud, otsust ei saa teha
- **Weight %** — praegune kaal portfellis protsentides. Naitab, kui suur osa koguportfellist on selles aktsias.
- **Target %** — susteemi arvutatud siht-kaal. Pohineb EV-l: korgema EV-ga aktsiad saavad suurema kaalu (core 6-10%, secondary 3-6%, speculative 1-3%).

### 3. Risk Flags

Punased hoiatused positsioonidele, mille risk on >= 9. Need on muu-kandidaadid ja vajavad kohest tahelepanu — kas muua maha voi vahetada parema vastu.

### 4. Swap Candidates

Vahetussoovitused. Kui sul on risk >= 9 positsioon ja portfellis on parem alternatiiv (vahemalt 1.25x korgema EV-ga), pakub susteem konkreetse vahetuse: muu X, osta Y.

### 5. Score a position (kokkuvolditav)

Siin sisestad iga aktsia skoorid. Ava see ja:
1. Vali ticker dropdown-ist
2. Lukka 10 slaiderit (0-10) — iga kriteerium eraldi:
   - Geology (20%) — maavara kvaliteet
   - Discovery Probability (15%) — avastamise toenaosus
   - Scale Potential (15%) — suuruse potentsiaal
   - Management (10%) — juhtkonna kvaliteet
   - Jurisdiction (10%) — jurisdiktsioon/riigirisk
   - Catalysts (10%) — lahiaja katalusaatorid
   - Capital Structure (5%) — kapitali struktuur
   - Market Positioning (5%) — turupositsioon
   - Strategic Value (5%) — strateegiline vaartus
   - ESG/Permitting (5%) — keskkonnaload
3. Iga slaideri all naed rubriigi kirjeldust (mis see hinne tahendab)
4. **Estimated Score** uueneb reaalajas iga slaideri liigutusega — nii naed kohe, kuidas iga kriteerium moju avaldab
5. Sisesta EV andmed (need on eraldi Score'ist — Score hindab ettevotte kvaliteeti, EV hindab investeeringu potentsiaali):
   - **Upside multiple** — mitu korda voib aktsia tousta (5-50x). Nt 10x tahendab, et eduka avastuse korral voib hind 10-kordistuda.
   - **Success probability** — kui toenaoline on, et see tousustsenaaarium teostub (0.25-0.80). Nt 0.40 = 40% toenaosus.
   - **Downside** — kui palju void kaotada kui asjad lahevad halvasti (0-10). Nt 1.0 tahendab vaikest kahju, 5.0 tahendab poole raha kaotust.
   - **Catalyst timing** — millal on oodata jargmist olulist sundmust (puurimistulemused, rahastamine jne). Near term saab 1.2x boonuse (lahema aja katalusaatorid on vaartuslikumad), mid term 1.0x, long term 0.8x.
6. **Expected Value** ja **Tier** uuenevad samuti reaalajas EV sisendite muutmisel
7. Vajuta **Save Scores** — salvestab molemad (Score + EV) andmebaasi. Alles siis muutuvad Decision Dashboard tabelis olevad vaartused ja soovitused. Andmed pusivad ka parast rakenduse taaskaivitust.

### 6. Export Daily PDF

Genereerib PDF-raporti koos tabelite ja risk-lippudega.

## Weekly — nadala portfellihaldus

Eeldab, et andmed on Daily lehel laaditud.

- **Koondmetriks** — portfelli tervise ulevaade: keskmine score, keskmine EV ja mitu positsiooni on korge riskiga
- **Complete Scoring Table** — koik 10 kriteeriumit iga positsiooni kohta uhes tabelis. Naitab, kus on aktsiate tugevused ja norkused.
- **Allocation Gap** — praegune kaal vs siht-kaal ja nende vahe (delta). Positiivne delta = alakaalus (osta juurde), negatiivne = ulekaalus (vahenda).
- **Rebalance Plan** — konkreetsed dollarisummad, mida teha:
  - **Trim/Sell** — mida ja kui palju muua ($)
  - **Add** — mida ja kui palju juurde osta ($)
  - **Net cash flow** — kokkuvote: kas raha vabaneb (positiivne) voi on vaja juurde panna (negatiivne)
- **Constraint Violations** — hoiatused, kui portfell on tasakaalust valjas: uks positsioon > 25%, uks regioon > 45%, voi uks commodity > 30% koguportfellist
- **Best Ideas** — 5 koige korgema EV-ga positsiooni. Need on sinu parimad voimalused praegu.
- **Export Weekly PDF**

## Monthly — strateegiline ulevaade

- **Portfolio Summary** — koguvaartus, parim ja halvim positsioon realiseerimata kasumi/kahjumi jargi
- **Commodity Exposure** — kui palju portfellist on kullas, hobedas, vaskes jne. Naitab ka piirmaara (max 30%) ja kas oled ule. Aitab valtida liigset kontsentratsiooni uhte toorainesse.
- **Region Exposure** — sama riikide/jurisdiktsioonide jargi (max 45%). Aitab hajutada geograafilist riski.
- **Strategic Positioning** — kuidas portfell jaguneb kvaliteedi jargi: core (parimad, EV >= 5), secondary (korralikud, EV 3-5) ja speculative (riskantsed, EV < 3). Naitab iga grupi positsiooniode arvu, kaalu ja keskmist kvaliteeti.
- **Full Portfolio** — taistabel koigi andmetega uhes kohas
- **Export Monthly PDF**

## Kust andmed tulevad ja kuhu lahevad

```
config/settings.yaml          — koik lavendid, kaalud, piirangud (muudetav)
config/scoring_rubrics.yaml   — iga kriteeriumi kirjeldused
data/processed/scoring_data.db — SQLite, sinu sisestatud skoorid (pusiv)
reports/                      — genereeritud PDF-id
```

**settings.yaml** on koige olulisem fail — seal saad muuta:
- Scoring kaalusid — milline kriteerium kui palju loeb (nt geology 20%, management 10%)
- Decision lavendeid — millal susteem soovitab osta/muua (nt BUY kui score >= 8.4)
- Risk lavendeid — mis score/EV kombinatsioon annab millise riski
- Position sizing reegleid — kui suure kaalu iga tier saab (core 6-10%, secondary 3-6%)
- Portfolio piiranguid — max uhe positsiooni kaal (25%), max regioon (45%), max commodity (30%)

## Tuupiline toovoog

1. Ava TWS (Interactive Brokers)
2. Kaivita `streamlit run app.py`
3. Daily lehel vajuta **Load from IB**
4. Vaata Decision Dashboard — mis on SELL, mis "No Score"
5. Ava **Score a position**, skoori labi skoorimata positsioonid
6. Parast skoorimist vaata, kuidas soovitused muutuvad
7. Nadala lopus mine **Weekly** lehele — vaata rebalance plaani
8. Kuu lopus mine **Monthly** lehele — strateegiline ulevaade
9. Ekspordi PDF kui vaja raportit
