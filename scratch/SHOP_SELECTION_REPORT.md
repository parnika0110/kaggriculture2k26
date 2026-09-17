# Investigation Report: Shop Selection Influenceability

**Date**: September 16, 2026
**Status**: COMPLETE — Shop selection CANNOT be usefully controlled.

---

## Phase 1: Shop Selection Mechanism (REVERSE-ENGINEERED)

### Source Code
```python
# kaggle_environments/envs/kaggriculture/kaggriculture.py, ~line 850
if day > 0 and day % 3 == 0 and len(unlocked_shops) < 8:
    rng = random.Random((seed * 1_000_003) ^ day)
    shop = rng.choice(sorted(SHOPS))
```

### Facts
- **When**: Every 3 days (day 3, 6, 9, 12, 15, 18, 21, 24), up to 8 shops
- **Candidates**: All 8 shops: BAKERY, BRUNCH_SPOT, FARMERS_MARKET, ICE_CREAM_SHOP, PET_CAFE, PIZZA_SHOP, SMOOTHIE_SHOP, YARN_STORE
- **Selection**: `rng.choice(sorted(SHOPS))` — uniform random, alphabetically sorted
- **Seed**: `(seed * 1_000_003) ^ day` — depends ONLY on global seed and day
- **Deterministic**: YES — verified by running same seed twice (identical shops)
- **Influenceable by agent**: **NO** — the RNG is created fresh with a fixed formula; no game state, market prices, or agent actions affect it

### Verified shop sequences for key seeds
```
Seed 7: FARMERS_MARKET, YARN_STORE, PIZZA_SHOP, PET_CAFE, BRUNCH_SPOT, SMOOTHIE_SHOP, ICE_CREAM_SHOP, YARN_STORE
Seed 0: ICE_CREAM_SHOP, BRUNCH_SPOT, YARN_STORE, YARN_STORE, ICE_CREAM_SHOP, FARMERS_MARKET, FARMERS_MARKET, SMOOTHIE_SHOP
```

### Conclusion
**Shop selection is a pure function of `(seed, day)`.** No market action, no wheat flip, no opening modification can influence which shop appears.

---

## Phase 2: C9 vs Original Divergence Analysis

### Self-play (identical agent vs identical agent)
Both C9 and Original produce **identical scores** in self-play for the same seed. When the same agent plays against itself, the market is symmetric and the opening makes no difference.

### H2H (C9 vs Original)
**10-seed benchmark results:**
```
Seed 0:  C9=$61,561  O=$62,264  d=$-703    Winner: O
Seed 1:  C9=$91,725  O=$87,053  d=$+4,672  Winner: C9
Seed 2:  C9=$90,994  O=$68,000  d=$+22,994 Winner: C9
Seed 3:  C9=$125,729 O=$117,561 d=$+8,168  Winner: C9
Seed 4:  C9=$70,922  O=$55,108  d=$+15,814 Winner: C9
Seed 5:  C9=$72,220  O=$100,076 d=$-27,856 Winner: O
Seed 6:  C9=$89,648  O=$117,666 d=$-28,018 Winner: O
Seed 7:  C9=$109,603 O=$55,504  d=$+54,099 Winner: C9
Seed 8:  C9=$98,112  O=$106,859 d=$-8,747  Winner: O
Seed 9:  C9=$127,953 O=$43,855  d=$+84,098 Winner: C9
```
**C9 wins 6/10, Original wins 4/10.**

### The Divergence Mechanism (traced on seed 0)

1. **Step 0**: C9 buys 5 wheat ($50). Original buys 15 wheat ($150), sells 60 wheat (from shed, +$1,500). Net: C9 starts at $2,950 with 5 wheat in shed; Original starts at $3,000 with 0 wheat.

2. **Steps 1-360 (days 0-15)**: Both follow identical route tape actions. Shed contents are nearly identical (C9 has 1 extra wheat). Money diff stays at +$1 for C9.

3. **Step 410 (day 17, hour 2)**: Money diff jumps to +$41 for C9. Both sell the same items at the same prices, but C9 acts first (P0), getting a slightly better price.

4. **Step 428 (day 17, hour 20)**: Money diff **flips to -$336**. Both execute identical SELL STRAWBERRY actions, but C9's worker carries 4 strawberries while Original's carries 6. Original places more strawberries in the shed, sells more, earns $377 more at this step.

5. **Steps 428-718**: The gap persists and grows slightly to -$703 by end.

### Why the inventories differ

The reactive layer `sell_lead` (fieldbook `_lead_sale`) sells high-value items one step early based on projected shed contents. At step 418, C9's worker inventory[2] has 4 STRAWBERRY while Original's has 6. This means the reactive layers made different decisions about which items to carry, sell, or place — cascading from the initial $1 shed difference at step 2.

---

## Phase 3: Candidate Openings

### Tested candidates
1. **C9 minimal**: BUY 5 wheat on step 0 (no wheat flip)
2. **Original wheat flip**: BUY 5+10 wheat, SELL 60 wheat on step 0
3. **Raw tape**: BUY 13+30 wheat, SELL 30 wheat on step 0

### Key finding
All three produce **identical self-play scores** for the same seed. The only differences appear in H2H, where they create different market price trajectories through sequential processing.

### Why no candidate can control shop selection
Since shop selection depends ONLY on `(seed, day)` via a fixed RNG formula, no market action can influence it. The wheat flip changes market prices, shed contents, and reactive layer behavior — but none of these affect the shop RNG.

---

## Phase 4: Shop Value Assessment

Since shop selection cannot be influenced, evaluating individual shop value is moot for this investigation. However, for completeness:

- **BAKERY**: Produces bread from wheat — high wheat demand
- **FARMERS_MARKET**: Sells various products — diverse demand
- **PIZZA_SHOP**: Produces pizza from wheat+tomato — moderate demand
- **BRUNCH_SPOT**: Produces brunch from wheat+egg — moderate demand

The route tapes already account for shop types. The agent doesn't need to "exploit" a specific shop — the pre-computed routes already do this.

---

## Phase 5: Strategy Assessment

### Can shop selection be intentionally influenced?
**No.** The shop RNG is `(seed * 1_000_003) ^ day`, a pure function of constants.

### Can the opening affect game outcome through other mechanisms?
**Yes, but marginally.** The wheat flip creates a ~$1 initial advantage that compounds through:
1. Sequential market processing (P0 acts first, gets slightly better prices)
2. Reactive layer differences (sell_lead, dead_stock react to different shed states)
3. Worker inventory divergence (different items carried by workers)

### Is this controllable?
**Partially.** The opening determines whether the agent has wheat in the shed at step 2, which triggers different reactive layer behavior. But:
- The effect is seed-dependent (sometimes +$84K, sometimes -$28K)
- The mechanism is indirect (through reactive layers, not through shop selection)
- No static guard can predict which seeds will benefit or suffer

---

## Phase 6: Benchmark Results

### Self-play (independent performance)
| Seed | C9     | Original | Diff |
|------|--------|----------|------|
| 0    | $61,561| $61,561  | $0   |
| 5    | $93,097| $93,097  | $0   |
| 7    | $106,837| $106,837| $0   |

**Identical.** The opening makes zero difference when the agent plays itself.

### H2H (C9 vs Original)
| Seed | C9     | Original | Diff     | Winner  |
|------|--------|----------|----------|---------|
| 0    | $61,561| $62,264  | -$703    | Original|
| 1    | $91,725| $87,053  | +$4,672  | C9      |
| 2    | $90,994| $68,000  | +$22,994 | C9      |
| 3    | $125,729| $117,561| +$8,168  | C9      |
| 4    | $70,922| $55,108  | +$15,814 | C9      |
| 5    | $72,220| $100,076 | -$27,856 | Original|
| 6    | $89,648| $117,666 | -$28,018 | Original|
| 7    | $109,603| $55,504 | +$54,099 | C9      |
| 8    | $98,112| $106,859 | -$8,747  | Original|
| 9    | $127,953| $43,855  | +$84,098 | C9      |

**C9 wins 6/10, but margins are highly variable** (-$28K to +$84K).

---

## Recommendations

1. **Do NOT attempt to influence shop selection** — it's impossible by design.

2. **The C9 opening is NOT a reliable improvement** — it wins 6/10 H2H seeds but the variance is enormous. The self-play scores are identical, confirming the effect is purely from market competition dynamics.

3. **The earlier "seed 8042 failure" and "seed 7 different shops" findings were incorrect** — both were artifacts of:
   - Using different code versions (notebook-deleted agent vs current)
   - Misattributing shop selection differences (which don't exist) to the opening

4. **The real mechanism is market price interaction** — C9's opening creates different shed states at step 2, which cascade through reactive layers into different sell/buy patterns, creating different market price trajectories in H2H play.

5. **If the goal is a robust improvement over V43**, focus on:
   - Improving the route tapes themselves (better production plans)
   - Optimizing reactive layers (sell_lead timing, dead_stock thresholds)
   - NOT on the opening, which has negligible impact on independent performance

6. **For leaderboard submission**, the current C9 opening is acceptable but not optimal. The differences are too small and too seed-dependent to justify further optimization of the opening alone.
