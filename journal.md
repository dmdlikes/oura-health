# Oura Health Journal

Running log of analyses, insights, and discussions.

---

## 2026-03-06: Withings Scale Integration + Weight Analysis

### Setup
Withings WiFi scale data integrated via OAuth2 API. 463 weigh-ins from 2015-09-29 to 2026-03-05 stored in `weight` table.

### Weight History
| Year | Avg (kg) | Range | Fat % |
|------|----------|-------|-------|
| 2019 | 84.6 | 80.7-86.0 | 16.8 |
| 2020 | 82.1 | 80.6-82.9 | 14.9 |
| 2022 | 79.6 | 77.9-81.2 | 14.1 |
| 2023 | 79.2 | 78.2-80.5 | 13.8 |
| 2025 | 85.5 | 84.4-87.0 | 18.3 |
| 2026 | 84.6 | 83.8-86.5 | 18.0 |

Weight was lowest in 2022-2023 (~79 kg, 14% fat). Has risen ~5 kg since then. This coincides with the period of lower exercise consistency (winter pattern, less running).

### No-Alcohol Effect on Weight
- Drinking period (2025): 85.5 kg avg, 18.3% fat
- No alcohol (2026): 84.6 kg avg, 18.0% fat
- Down ~0.9 kg and 0.3% fat after stopping alcohol

### Weight vs Overnight HR (Ring 3 period)
Weak but directional signal — lower weight associates with lower overnight HR:
- 83-84.5 kg: 60.7 bpm lowest HR, 34.1 HRV
- 84.5-86 kg: 61.1 bpm, 35.4 HRV
- 86+ kg: 61.4 bpm, 32.0 HRV

The HR relationship is modest (~0.7 bpm across the range). Weight loss alone won't get HR to target, but it's a contributing factor alongside cardio fitness.

### Recent Trend (Encouraging)
Monthly averages show a downward trend since stopping alcohol:
- Oct 2025: 85.8 kg, 18.5% fat
- Feb 2026: 84.3 kg, 17.9% fat
- Mar 2026: 84.3 kg, 17.3% fat (early data)

Fat percentage dropping faster than weight — suggests body recomposition (possibly more activity).

---

## 2026-03-06: Initial Deep Analysis

### Goal
Get overnight lowest heart rate down to 55-57 bpm consistently.

### Current Baseline (last 70 days, as of March 2026)
- Avg lowest HR: **61.9 bpm** (goal: 55-57)
- Avg HRV: **34.7 ms**
- Avg sleep: **7.1 hrs**
- Avg deep sleep: **1.15 hrs (16.5%)**
- Hit <=57 bpm: **1 night out of 72**
- Hit <=60 bpm: **26 of 72 nights (36%)**

### Ring History (IMPORTANT for data interpretation)
- **Ring 1** (pre Feb 2021): HRV avg 50.9, max 78
- **Ring 2** (Apr 2021 - Jan 2025): HRV avg 39.4, max 81
- **Ring 3 / Gen 4** (Jan 12, 2025+): HRV avg 32.0, max 51

**Each ring measures HRV differently.** Controlling for identical HR and sleep duration:
- Ring 1: 43.7 HRV
- Ring 2: 40.6 HRV
- Ring 3: 34.0 HRV

~10 points of the apparent 20-point HRV decline is measurement artifact from ring changes. Real decline is likely 5-8 points (age + lifestyle). Gen 4 is validated as MORE accurate (CCC=0.99 vs ECG) - earlier rings likely read high.

**Deep sleep also affected:** Ring 3 reclassified ~6% from deep to light. Don't compare deep sleep across rings.

### Key Findings

#### 1. Sleep Duration is the #1 HR Lever
- <6 hrs sleep: 68.1 avg lowest HR
- 6+ hrs: 61.2-61.4 (floor effect after 6 hrs)
- Consecutive 7+ hr nights compound: 60.8 vs 63.3

#### 2. Alcohol Cessation is Working
Stopped drinking Jan 1, 2026. Comparing 65-day windows:
- HR: down 2.2 bpm
- HRV: up 3.6 points
- Efficiency: up 3 points
- Weekend penalty eliminated (Fri/Sat were +3 bpm, +6 HRV worse when drinking)
- Alcohol effect lasted 2-3 days per episode, so 2 weekend sessions wiped out ~4 of 7 nights

#### 3. Moderate Activity > Intense Activity (for overnight HR)
Same-night effect:
- <200 active cal: 59.8 avg lowest HR (best!)
- 200-400: 61.1
- 600+: 65.0 (worst)

BUT weekly lagged effect is opposite:
- Low activity weeks: 30.3 HRV next week
- Active weeks: 33.2 HRV next week

**Interpretation:** Hard workouts hurt that night but build fitness over weeks. The key is frequency and consistency, not intensity.

#### 4. Basketball Night Profile
Basketball finishes ~9pm, then late eating and late bedtime:
- Lowest HR: 66.1 (vs 63.1 regular nights)
- HRV: 26.1 (vs 32.4)
- Sleep: 6.8 hrs (vs 7.2)
Acute cost but contributes to long-term fitness.

#### 5. Seasonality = Exercise Pattern
- Summer (Jun-Sep): HRV 42-44, runs outdoors 3-4x/week
- Winter (Nov-Dec): HRV 37-38, only basketball 1x/week + low-intensity Pilates
- The annual HRV cycle is driven by exercise pattern, not weather

#### 6. HRV and Deep Sleep are the Same System
They track almost perfectly together. Both are measures of parasympathetic/vagal tone. Can't optimize one without the other. The upstream driver is cardiovascular fitness.

#### 7. Causal Chain (from data)
**Activity (weeks of consistency) -> HRV -> Deep Sleep -> Lowest HR**
- Activity is the leading indicator
- HRV responds within 1-2 weeks
- HR is the laggard (responds last, stays changed longest)
- Alcohol suppresses the entire chain

#### 8. Breathing Disturbance Index
BDI 10+ nights: HR +3 bpm, HRV -3 vs low BDI nights. Only 5% of nights.
Correlates with lower SpO2 (<96% -> avg BDI 6.7 vs >98% -> BDI 5.0).
Sleep apnea tested: mild signs, not clinical. BDI worse with late bedtimes. Snoring historically associated with alcohol (now eliminated).

#### 9. "Restless Periods" is a Junk Metric
Scales linearly with time in bed (~27-30/hr regardless). Predicts nothing useful. Awake time also doesn't correlate with HR/HRV - brief awakenings don't hurt cardiovascular recovery.

### Recommendations (Priority Order)

1. **Add winter cardio** - 20-30 min moderate cardio 4-5x/week year-round. The winter gap is where fitness erodes annually. Treadmill, indoor cycling, brisk walking all count.
2. **Stay alcohol-free** - Already yielding benefits. Full HRV recovery takes 3-6 months.
3. **Protect 6+ hr sleep floor** - Non-negotiable. Aim for 7+.
4. **Stack consecutive good nights** - Consistency > single great nights.
5. **Bedtime by 11pm** - Modest but real benefit for deep sleep.
6. **Continue magnesium** - Take at night if not already. Glycinate form preferred.

### Realistic Targets
- Short-term (3 months): Avg lowest HR 59-60, HRV 38-40 (on current ring)
- Medium-term (6+ months with consistent cardio): HR 57-59, HRV 42-45
- The 55-57 goal may require sustained cardiovascular conditioning and time

### Charts
- `outputs/health_trends.png` - All 4 metrics normalized on one graph
- `outputs/correlations.png` - Paired correlations in quadrants

### Ideas to Explore
- **Snore Wars + Oura integration** - Combine Oura biometric data (HR, HRV, SpO2, BDI, breathing rate) with Snore Wars audio to improve snoring attribution. Oura can provide a "likely snoring" signal based on BDI/SpO2/HR patterns that could timestamp when snoring episodes occur, helping attribute audio events to the right person.
- **4-week rolling activity average** as the primary activity metric for dashboards
- **Recovery index trend** from readiness data (declining, worth monitoring)

---

## 2026-03-07: Lab Results Integration + Lipid Analysis

### Lab Data
5 lipid panels loaded into `labs` table (45 records). Collection dates: 2019-03-25, 2021-05-25, 2023-03-30, 2024-02-22, 2025-09-02.

### Diet Phases (confirmed with user)
| Phase | Period | Diet | Notes |
|-------|--------|------|-------|
| 1 | Oct 2021 → Feb 2023 | Strict Keto | Weight loss period (86→79 kg) |
| 2 | Mar 2023 → Feb 2024 | Low Carb | Reintroduced some carbs |
| 3 | Mar 2024 → Dec 2024 | Low Carb (reduced activity) | Hip surgery March 2024 |
| 4 | Jan 2025 → Nov 2025 | Low Carb | Recovery, moderate activity |
| 5 | Dec 2025+ | Strict Keto | Current phase |

### Lipid Panel Timeline
| Date | TC | LDL | HDL | TG | ApoB | Diet Phase | Fasting |
|------|-----|-----|-----|-----|------|------------|---------|
| 2019-03-25 | 178 | 106 | 46 | 131 | - | Pre-keto | No |
| 2021-05-25 | 203 | 129 | 55 | 108 | - | Pre-keto | No |
| 2023-03-30 | 238 | 150 | 56 | 180 | - | Low carb (just transitioned) | No |
| 2024-02-22 | 161 | 89 | 55 | 94 | 66 | Low carb | Inadvertently fasted |
| 2025-09-02 | 224 | 152 | 62 | 57 | 114 | Low carb | No |

### Key Insights

#### ApoB Jump (66→114) occurred within low-carb phases
Both Feb 2024 and Sep 2025 panels were during LOW CARB — not keto. This weakens the "keto drives ApoB up" explanation. The key differences:
- **Feb 2024**: Inadvertently fasted, pre-hip surgery, more active
- **Sep 2025**: Non-fasted, 18 months post-hip surgery, significantly less active
- Reduced activity + fasting status differences may explain more than diet

#### Fasting vs Non-Fasting
- Feb 2024 (fasted): TG 94, LDL 89 — best panel
- Sep 2025 (non-fasted): TG 57, LDL 152
- The very low TG in Sep 2025 (57, non-fasting) argues AGAINST fasting as sole explanation

#### HDL Trend is Positive
46 → 55 → 56 → 55 → 62. Steadily improving, consistent with low-carb benefits.

#### Hip Surgery (March 2024) as Confounding Factor
18 months of dramatically reduced activity between the two ApoB measurements. Activity is a known modulator of lipid metabolism.

### Metabolic Markers (Sep 2025)
- HbA1c: 5.4% (excellent), Glucose: 91 (normal), CRP: <1 (low inflammation)
- Kidney function all normal

### Activity Intensity Analysis (the data doesn't support an activity explanation)

90-day H+M activity before each ApoB draw:
- **Feb 2024 (ApoB 66):** 27.5 min/day H+M, 10.2% intensity ratio, 316 cal/day
- **Sep 2025 (ApoB 114):** 40.1 min/day H+M, 13.4% intensity ratio, 401 cal/day

Activity was objectively *better* before the worse ApoB draw — on every metric (volume, intensity ratio, active calories). 12-month trailing averages were also nearly identical. Activity quality/quantity does NOT explain the ApoB difference.

**Missing data:** Oura's HR data only goes back ~2 days, so we can't see actual HR zones historically. Oura's "high/medium" classifications are MET-based estimates, not true HR zones. Nike Run Club data (GDPR request pending) would provide actual running volume and pace, which would be a much better fitness signal.

### Dietary Context (critical for interpretation)

Keto vs low carb for this user is **NOT about saturated fat intake** — it's about carb restriction:
- **Strict keto (<50g carbs):** No rice, no processed sugar. Carbs from vegetables, fiber, some chocolate.
- **Low carb:** Same protein/fat base, plus some white rice with meals, some processed sugar.
- **Saturated fat is largely constant** across both phases: chicken, beef, bacon on weekends, butter coffee (weekends only for past 6 months).

This means the traditional "more saturated fat → more LDL" mechanism doesn't apply. The variable is **carb availability**, which affects hepatic VLDL production and LDL particle dynamics directly (the lean mass hyper-responder pathway).

### Fasting vs Non-Fasting Panels

Fasting is the gold standard for lipid panels:
- **Triglycerides:** Most affected. Eating fat before draw can spike TG 20-50%+. March 2023 TG 180 (non-fasted) could be 100-120 fasted.
- **LDL:** Calculated via Friedewald (TC - HDL - TG/5). Inflated TG *lowers* calculated LDL — so non-fasted LDL may be *understated*.
- **ApoB:** Directly measured, <5% variation with meals. The 66→114 jump is the most reliable number.
- **HDL:** Minimally affected by fasting.

The Feb 2024 panel is the cleanest data point. But ApoB is trustworthy regardless.

### Weight Loss Lipid Paradox

Counter-intuitive but well-documented: during active weight loss, the body mobilizes stored fat into the bloodstream, transiently raising TC, LDL, and free fatty acids. After weight stabilization, lipids settle lower.
- **March 2023 (worst panel):** Near end of major weight loss, 79 kg — possibly still in fat-mobilization state.
- **Feb 2024 (best panel):** Weight-stable at 82 kg — no longer mobilizing stored fat.

Being lighter ≠ better lipids if you're actively losing.

### Revised Conclusions

The strongest correlates with lipid variation are:
1. **Fasting status** — the single biggest explainer for the Feb 2024 vs Sep 2025 difference
2. **Weight/body composition** — 82.2 kg/16% vs 86.4 kg/18.5% (4.2 kg, 2.5% fat difference)
3. **Active weight loss state** — mobilizing stored fat worsens panels transiently
4. **Carb restriction level** — may drive LDL/ApoB via hepatic VLDL pathway, independent of sat fat
5. ~~Activity level~~ — **ruled out by data** (better activity = worse panel)

### Recommendations
1. Get a **fasting lipid panel + ApoB** during current strict keto phase (3+ months in) — this isolates the keto effect with a clean draw
2. Consider **CAC scan** — direct plaque measurement bypasses all lipid panel interpretation issues
3. **Nike Run Club GDPR data request** — submit at nike.com/privacy to get historical running data; will provide actual pace/distance/HR zone data that Oura can't capture
4. Wait for weight to stabilize on current keto before drawing labs (don't test during active loss)

### Dashboard Updates
- Added Labs Timeline chart with diet phase background shading
- Added diet phase annotations to weight chart
- Reference lines for LDL optimal (<100) and ApoB target (<90)

---

