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

