# A16-P0/P1 — 독립 loaded-domain 설계 원장 (2026-11-26)
## P0 기준
A parent ea68e96710b62e982308fe740afeeba6081fd551, B d397bea7cd1ccc0f8ca5dcb3503c313e83405f47, platform b8ef3998973a5e33b67ddd5c5b63c3c89b837840. Main/E unchanged, stacked Draft targets A parent. B diagnostic dea58025451055e709f5bd1a8892ef352d4197756543b9d32598e39bc8026e98 verified outer + exact 3/3 inner, exit0, raw recomputed true, worksheet 4 rows blank human decisions; Git HEAD not in diagnostic, user confirmation and PR46 comment 7181242168 support review-only product acceptance. B Q01 PASS Q02–07 HOLD. A15 old data/GUI PASS, cleanup -11, production contact HOLD, no GT. B referenced requirements, handoff, acceptance, FOV issue, card and audit API inspected. Do not use A15 hard-coded audit pins for A16. 
## P1 prespecified matrix
New physical cylinder stacks; same materials (0.22kg each, mu=.65), tray, overhead camera, gravity, 1ms, 2s t0, 2.2–2.699s world-Y .12Nm command on uppermost dish, end12.3s. Both families new dimensions, second has three dishes. Changing target to uppermost on 3 stack is explicit same top-dish intervention semantics. Canonical family/layout v2 hashes from actual ordered geometry/material/nominal world poses, no seed/name/outcome. Physical fingerprint additionally unversioned geometry/poses; B must compare content not prefixes. Seed=0 all, no jitter. Support margin below means lower radius minus top center distance, a nominal geometric proxy, not true contact area/COM certification. Tray center/eccentric classification refers to top center; relative support offset separately tracked. Positive/negative torque alignment crossed with tray-center placement; not guaranteed outcome. 
|scene|family dimensions radius/thickness m|lower x|upper x|relative upper offset|nominal support margin m|hypothesis (not label)|
|---|---|---:|---:|---:|---:|---|
|L16-01|F1 .115/.045 + .082/.050|-.012|0|+.012|.103|small response plausible|
|L16-02|F1 same|-.097|0|+.097|.018|large response plausible|
|L16-03|F1 same|.09|.102|+.012|.103|small response plausible|
|L16-04|F1 same|-.005|-.102|-.097|.018|opposite torque alignment may differ|
|L16-05|F2 .140/.025 + .105/.025 + .075/.035|-.012|0|+.012|.093|small response plausible|
|L16-06|F2 same|.087|0|-.087|.018|opposite alignment may differ|
|L16-07|F2 same|-.09|-.102|-.012|.093|small response plausible|
|L16-08|F2 same|.015|.102|+.087|.018|large response plausible|
F2 lower and middle concentric. All nominal fully loaded tray; actual settled/support/FOV must pass before external command. Each family contains center and eccentric tray placement at both support margins. Center-to-support relation still physically meaningful; evaluate signed offset, tray center, stack count, geometry/outcome confounding after capture; no automatic class labels, no cherry-picking or rerun to balance. Natural occlusion, usage rights, human review remain HOLD. No A15 repetitions. No dynamic robot claim. 
## Scope
P0/P1 design hypotheses frozen before actual execution. All eight attempted once unless acquisition failure stops; retain failures/not-run. B QA before expansion. Source code and docs only on Git. 
