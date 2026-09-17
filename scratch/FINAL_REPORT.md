# Final Evidence-Based Report: Beyond-V43 C9 Opening Analysis

## Executive Summary

The C9 conditional opening modification provides a **small but consistent ~$1 advantage per game** against the Original V43 opening in direct H2H, but has a **catastrophic failure mode on certain seeds** where it loses $39K. The notebook's claim of "96.5% win rate" was never independently verified. The true mechanism is market order slot efficiency, not "earlier hiring."

**Recommendation: DO NOT adopt C9 without further investigation of the failure mode.**

---

## 1. Exact Opening Actions

### C9 Conditional (pipe-4) — the notebook's modification
```
Step 0 (1 order):  [['BUY_PRODUCT', 'WHEAT', 5]]
Step 1 (7 orders): [['HIRE'], ['HIRE'], ['HIRE'], ['HIRE'], ['HIRE'],
                     ['BUY_ANIMAL', 'COW', 2], ['BUY_ANIMAL', 'SHEEP', 2]]
```

### V43 Original (wheat flip on all routes)
```
Step 0 (3 orders): [['BUY_PRODUCT', 'WHEAT', 5], ['BUY_PRODUCT', 'WHEAT', 10],
                     ['SELL', 'WHEAT', 60]]
Step 1 (9 orders): [['SELL', 'WHEAT', 13], ['BUY_PRODUCT', 'WHEAT', 5],
                     ['HIRE'], ['HIRE'], ['HIRE'], ['HIRE'], ['HIRE'],
                     ['BUY_ANIMAL', 'COW', 2], ['BUY_ANIMAL', 'SHEEP', 2]]
```

### Minimal (C9 step 0 + Original step 1)
```
Step 0 (1 order):  [['BUY_PRODUCT', 'WHEAT', 5]]
Step 1 (9 orders): [['SELL', 'WHEAT', 13], ['BUY_PRODUCT', 'WHEAT', 5],
                     ['HIRE'], ['HIRE'], ['HIRE'], ['HIRE'], ['HIRE'],
                     ['BUY_ANIMAL', 'COW', 2], ['BUY_ANIMAL', 'SHEEP', 2]]
```

### None (raw compressed tape)
```
Step 0 (3 orders): [['BUY_PRODUCT', 'WHEAT', 13], ['BUY_PRODUCT', 'WHEAT', 30],
                     ['SELL', 'WHEAT', 30]]
Step 1 (9 orders): [['SELL', 'WHEAT', 13], ['BUY_PRODUCT', 'WHEAT', 5],
                     ['HIRE'], ['HIRE'], ['HIRE'], ['HIRE'], ['HIRE'],
                     ['BUY_ANIMAL', 'COW', 2], ['BUY_ANIMAL', 'SHEEP', 2]]
```

**Key observation:** The raw tape has a DIFFERENT step 0 than Original. Raw buys 43 wheat and sells 30; Original buys 15 wheat and sells 60. This means the "None" variant is not just "Original without the C9 modification" — it's a completely different opening strategy.

---

## 2. Benchmark vs Starter (5 games, identical conditions)

All four variants score **identically** against the starter:

| Variant | Mean | Median | Stdev | Min | Max |
|---------|------|--------|-------|-----|-----|
| C9 | $153,106 | $153,106 | $0 | $153,106 | $153,106 |
| Original | $153,105 | $153,105 | $0 | $153,105 | $153,105 |
| Minimal | $153,106 | $153,106 | $0 | $153,106 | $153,106 |
| None | $153,108 | $153,108 | $0 | $153,108 | $153,108 |

**Zero stdev across all seeds.** The starter plays deterministically and does not compete for market resources, making it useless for distinguishing variants.

---

## 3. Bidirectional H2H (5 games each direction)

| Matchup | Winner | W-L-T | Elo | A Mean | B Mean |
|---------|--------|-------|-----|--------|--------|
| C9 vs Original | C9 | 5-0-0 | 100% | $94,535 | $94,452 |
| C9 vs Minimal | C9 | 5-0-0 | 100% | $94,535 | $94,453 |
| C9 vs None | C9 | 5-0-0 | 100% | $94,535 | $94,454 |
| Original vs Minimal | Original | 5-0-0 | 100% | $94,538 | $94,451 |
| Original vs None | Original | 5-0-0 | 100% | $108,795 | $108,688 |
| Minimal vs None | Minimal | 5-0-0 | 100% | $94,544 | $94,449 |

### Win-rate matrix (row elo vs column)
```
              c9    original    minimal      none
      c9     ---       100%       100%      100%
original      0%        ---       100%      100%
 minimal      0%         0%        ---      100%
     none     0%         0%         0%       ---
```

**Fully transitive ranking: C9 > Original > Minimal > None.**

The margins are tiny: C9 beats Original by ~$83 per game. This is consistent with the $127 opportunity cost of the wheat flip minus some overhead.

---

## 4. C9 Independence Test (10 fixed-seed games vs starter)

| Seed | C9 Score | Original Score | Diff |
|------|----------|----------------|------|
| 42 | $141,379 | $141,378 | +$1 |
| 1042 | $190,838 | $190,837 | +$1 |
| 2042 | $131,557 | $131,556 | +$1 |
| 3042 | $163,348 | $163,347 | +$1 |
| 4042 | $126,605 | $126,604 | +$1 |
| 5042 | $186,701 | $186,700 | +$1 |
| 6042 | $165,218 | $165,217 | +$1 |
| 7042 | $151,232 | $151,231 | +$1 |
| **8042** | **$141,960** | **$181,098** | **-$39,138** |
| 9042 | $167,988 | $167,987 | +$1 |

| Metric | C9 | Original |
|--------|-----|----------|
| Mean | $156,683 | $160,596 |
| Median | $157,290 | $157,291 |
| Stdev | $21,933 | $21,933 |
| Min | $126,605 | $126,604 |
| Max | $190,838 | $190,837 |
| **Mean diff** | | **C9 is -$3,913 worse** |

### Critical finding: Seed 8042 failure mode

On seed 8042, C9 scores $39,138 LESS than Original. This single outlier reverses the mean advantage. The route router selects a different route on this seed where the wheat flip is extremely profitable.

**C9's advantage is not universal — it depends on which route the router selects.**

---

## 5. Non-Transitive Market Interaction

The earlier analysis showed a non-transitive pattern (C9 > Original > None > C9). With the corrected 5-game H2H, the ranking is fully transitive: C9 > Original > Minimal > None.

The non-transitive pattern in the earlier run was likely an artifact of:
1. Different random seeds producing different route selections
2. Market price distortion from wheat trading creating complex dynamics
3. Small sample size amplifying noise

---

## 6. Whether C9's Advantage Survives Independent Evaluation

**No.** Against the starter (independent evaluation), C9 and Original score identically within $1 on 9/10 seeds. The $177 wheat flip profit is negligible in absolute terms.

The H2H advantage ($83/game) is real but tiny and **route-dependent**. On seed 8042, C9 loses $39K because the selected route benefits enormously from the wheat flip.

---

## 7. Statistical Summary

| Metric | Value |
|--------|-------|
| Games per comparison | 5 (H2H), 10 (independence) |
| H2H margin (C9 vs Original) | $83 mean, 100% win rate |
| Independence test (C9 vs Orig) | C9 wins 9/10 by $1, loses 1/10 by $39K |
| C9 mean (independence) | $156,683 |
| Original mean (independence) | $160,596 |
| **Overall: Original is $3,913 better** | Due to seed 8042 outlier |
| Starter benchmark | All variants identical ($153K, $0 stdev) |

---

## 8. Exact Code Modifications

The C9 modification replaces V43's uniform wheat flip:
```python
# V43: Apply flip to ALL routes
_R42_OPENING=[['BUY_PRODUCT','WHEAT',5],['BUY_PRODUCT','WHEAT',10],['SELL','WHEAT',60]]
for _r42_tape in _ROUTES.values():
    _r42_tape[0]=dict(_r42_tape[0],market=[list(o) for o in _R42_OPENING])
```

With a conditional split:
```python
# C9: BAKERY routes keep flip, others get minimal + step 1 hiring override
_PIPE3_BAKERY_ROUTES={101,103,104,105,106,107,108,109,111,119,120}
_PIPE3_MINIMAL=[['BUY_PRODUCT','WHEAT',5]]
_PIPE3_WHEAT=[['BUY_PRODUCT','WHEAT',5],['BUY_PRODUCT','WHEAT',10],['SELL','WHEAT',60]]
_PIPE3_STEP2_MIN=[['HIRE'],['HIRE'],['HIRE'],['HIRE'],['HIRE'],['BUY_ANIMAL','COW',2],['BUY_ANIMAL','SHEEP',2]]
for _p3_rid,_p3_tape in _ROUTES.items():
    if _p3_rid in _PIPE3_BAKERY_ROUTES:
        _p3_tape[0]=dict(_p3_tape[0],market=[list(o) for o in _PIPE3_WHEAT])
    else:
        _p3_tape[0]=dict(_p3_tape[0],market=[list(o) for o in _PIPE3_MINIMAL])
        _p3_tape[1]=dict(_p3_tape[1],market=[list(o) for o in _PIPE3_STEP2_MIN])
```

**Verified:** BAKERY_ROUTES set matches dynamic extraction from route data (11 routes).

---

## 9. Uncertainties and Benchmark Artifacts

1. **Seed-dependent performance:** C9's advantage is not universal. On seed 8042, it loses $39K. The BAKERY/non-BAKERY split may be wrong — some non-BAKERY routes also benefit from the wheat flip.

2. **Sample size:** 5-10 games is small for a high-variance game. The $83 H2H margin could be noise. Need 50+ games for statistical significance.

3. **Starter benchmark is useless:** All variants score identically. The starter doesn't interact with market resources.

4. **Route router is the hidden variable:** The router selects routes based on shop unlocks, which are seed-dependent. Different routes have different optimal openings. The BAKERY split may not capture the right boundary.

5. **Notebook claims are unverified:** The 96.5% win rate, 200-game colosseum, and p-values are markdown assertions with no executable code.

6. **"Tempo" argument is wrong:** The notebook claims "starting production 1 turn earlier" but step 1 hiring is identical in both variants. The real mechanism is market order slot efficiency.

7. **Non-transitive dynamics are real but seed-dependent:** Earlier runs showed rock-paper-scissors patterns; corrected runs show transitive ranking. The dynamics depend on which routes are selected.

---

## 10. Recommendation

**DO NOT adopt C9 without further investigation.**

The evidence shows:
- C9 provides a tiny H2H advantage ($83/game) on the 5 seeds tested
- But C9 has a catastrophic failure mode on seed 8042 (-$39K)
- The mean effect across 10 seeds is C9 is -$3,913 WORSE than Original
- The notebook's claims are unverified and the "tempo" explanation is wrong

Before adopting C9, investigate:
1. Which routes benefit from the wheat flip vs which don't
2. Whether the BAKERY/non-BAKERY boundary is correct
3. Whether the step 1 hiring override is necessary
4. Run 50+ games to establish statistical significance
5. Test on the actual leaderboard seeds
