# Cycling

Coaching heuristics for cycling-specific metrics. Loaded when the user's profile includes `cycling`.

## Power Metrics

- **FTP (Functional Threshold Power):** the highest average power sustainable for ~60 minutes. The anchor for all intensity zones.
- **Normalized Power (NP):** power-weighted average that accounts for variability. Always compare NP to avg power, not just avg power alone.
- **Intensity Factor (IF = NP / FTP):**
  - <0.75 = recovery ride
  - 0.75–0.85 = endurance
  - 0.85–0.95 = tempo
  - 0.95–1.05 = threshold
  - >1.05 = VO2max or above
- **TSS (Training Stress Score) = IF² × duration_hours × 100:** quantifies cumulative load per ride.
  - Weekly TSS guidelines: recovery week <300, base/endurance week 300–500, build week 500–700, high-load week 700–900. >900/week without context = flag for overreaching.
  - A single ride TSS >150 warrants 24–48h of easy riding before the next key session.

## Cycling Cadence

- Optimal range: 85–95 rpm on flat terrain.
- Climbing: 70–85 rpm is normal and acceptable; below 60 rpm sustained = grinding — flag it.
- Cadence consistency across a ride matters more than the absolute number. Erratic cadence (large swings) often signals poor gear selection or fatigue.
- Low cadence at high power (mashing) increases muscular fatigue and joint stress. If sustained power is high and cadence is below 75 rpm, note the trade-off.

## Heart Rate Decoupling

- Compare the HR/power ratio in the first half of a steady-state ride vs the second half: (avg HR second half / avg power second half) / (avg HR first half / avg power first half) - 1.
- <5%: good aerobic fitness — heart rate is tracking power cleanly.
- 5–10%: moderate drift — acceptable on hot days or long rides, but worth noting.
- >10%: endurance ceiling, inadequate fueling, heat stress, or cumulative fatigue. Flag it and investigate context.
- Only meaningful on rides with steady-state segments. Interval sessions and highly variable power profiles will inflate this metric artificially.

## Climbing Analysis

- **VAM (Vertical Ascent Meters/hour):** measures climbing rate regardless of gradient.
  - Recreational cyclist: 600–800 VAm/h
  - Strong amateur: 800–1200 VAm/h
  - VAM varies with gradient — steeper climbs produce higher VAM at the same W/kg. Always note gradient when comparing.
- **Power-to-weight ratio at threshold (W/kg):**
  - Recreational: 2.5–3.5 W/kg
  - Strong amateur: 3.5–4.5 W/kg
  - Improvements here are the clearest indicator of climbing progress. Track it across training blocks.
- For climb segments, report: avg power, avg W/kg, VAM, IF, and how it compares to FTP-derived expectations.

## Endurance Ride Analysis

- **Pacing consistency:** compare Normalized Power to Average Power. NP/Avg Power ratio >1.10 = variable pacing — spikes and surges that may not show up in avg power but still cost matches.
- **Late-ride power fade:** compare avg power in the last hour to the first hour. >15% fade = fueling issue, insufficient base fitness, or both. Ask about nutrition strategy before attributing it to fitness alone.
- For long rides (>3h), report power by hour. A gradual fade is normal; a cliff after hour 2–3 is a signal.
- Top sessions by training effect: duration, avg power, NP, IF, TSS, cadence, HR decoupling, and any climb segments.
