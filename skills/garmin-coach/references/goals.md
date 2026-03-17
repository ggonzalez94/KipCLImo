# Goals

The user's primary goal determines what you emphasize when synthesizing advice.
Always reference the goal when making recommendations. The goal is stored in
`profile.primary_goal` from `garmin config show`.

---

## Running Goals

### Correr más rápido en una distancia específica (PR)
Emphasis: interval quality, pace progression across weeks, race predictions trend, VO2max trajectory. Flag sessions where target pace was missed. Track whether easy runs are staying easy enough to support hard sessions.

### Prepararse para una carrera (5K / 10K / medio maratón / maratón / ultra)
Emphasis: long run progression (distance and time on feet), endurance score trend, race predictions vs target time, taper readiness in final weeks, weekly volume ramp rate (flag >10% week-over-week increases). If a race date is configured, count down weeks remaining and adjust urgency.

### Construir base aeróbica / aumentar volumen semanal
Emphasis: volume trends (weekly km and hours), intensity distribution (protect 80/20 — flag if hard sessions exceed 20%), aerobic HR drift improvement over weeks, consistency (days per week trained). Discourage intensity spikes during base building.

### Volver de una lesión sin recaídas
Emphasis: conservative load monitoring — keep ACWR below 1.2, flag any single-week volume jump >15%. Watch recovery signals closely: HRV, body battery, sleep. Monitor GCT balance and asymmetry for compensation patterns. Celebrate consistency over performance.

### Mantener consistencia y salud (sin objetivo específico)
Emphasis: consistency streaks (how many weeks in a row with 3+ sessions), recovery balance (not over- or under-training), avoid overreaching status. Flag detraining if it appears. General health signals: sleep trends, resting HR, stress.

---

## Cycling Goals

### Mejorar FTP / potencia sostenida
Emphasis: FTP trend over 4-week blocks, threshold and VO2max interval quality, power consistency in sustained efforts, TSS progression. Flag if too much time in endurance zone without enough threshold work.

### Prepararse para un evento (gran fondo, carrera, tour)
Emphasis: weekly TSS ramp, long ride progression, climbing readiness (VAM, power-to-weight if relevant), endurance score trend, taper timing. If event date is configured, count down and adjust urgency.

### Construir resistencia para rutas largas
Emphasis: duration of longest ride trending up, HR decoupling improving (better aerobic efficiency), fueling signals (power fade in last third of long rides), volume consistency.

### Mantener consistencia y salud
Emphasis: ride frequency, recovery balance, avoid overreaching. Flag detraining. General health signals.

---

## Gym Goals

### Complementar rendimiento en running o ciclismo
Emphasis: are gym sessions supporting the primary sport? Watch that gym volume doesn't spike during hard training blocks. Focus on functional strength markers (single-leg work, hip stability, core). Flag if recovery impact is too high (HRV drops, readiness down after gym days).

### Fitness general y composición corporal
Emphasis: progressive overload trends (is load/volume increasing?), training frequency and consistency, body composition trends (weight, body fat % if available), balanced muscle group coverage. Flag stagnation on compound lifts.

### Prevención de lesiones / movilidad
Emphasis: session consistency (regularity matters more than intensity), recovery signals, any asymmetry flags from running/cycling data. Encourage low-impact, high-frequency approach. Flag if gym sessions are too intense and impacting recovery for other activities.
