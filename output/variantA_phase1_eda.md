# Variant A · Phase 1 — funding feature, joint distribution, Edge predictive structure

Daily funding = Σ of the day's 8h payments (the day's total funding cost to a long). Lagged ≥1 bar, next-open execution (same convention as MFI). No strategy PnL here.

## Phase 0 — funding integrity
```
             n: 2061
           nan: 0
          mean: 0.000342
           std: 0.000570
           min: -0.002550
           max: 0.004865
  pct_negative: 0.098981
    ann_mean_%: 12.479391
```

## Phase 1 Step 1 — joint distribution & divergence-cell sparsity

- corr(MFI, funding): Pearson **+0.315**, Spearman **+0.347**  (rank-rank +0.347)
- Favourable divergence cell (trailing W=90: MFI_rank>0.8 & Fund_rank<0.2): **58 days = 2.8%** of sample  (full-sample-rank version: 43 days)
- **⚠️ SPARSE**: the most-informative divergence observations are rare — this caps how much the premise can deliver and inflates small-sample noise.

## Phase 1 Step 2 — Edge predictive structure (honest, non-overlapping IC)

Non-overlapping IC (sample every h bars) — the decisive test:
```
IC:
               1       3       5       10      21
Edge_W60  -0.0003 -0.0078 -0.0012 -0.0277  0.0411
Edge_W90  -0.0029  0.0062  0.0173  0.0093  0.0230
Edge_W252  0.0107  0.0246  0.0128 -0.0233  0.0591
raw_MFI    0.0209  0.0287  0.0366  0.0721  0.0860

p-values:
              1      3      5      10     21
Edge_W60   0.988  0.842  0.981  0.697  0.693
Edge_W90   0.899  0.873  0.731  0.897  0.827
Edge_W252  0.648  0.547  0.808  0.756  0.589
raw_MFI    0.344  0.453  0.459  0.304  0.400

(overlapping IC, for reference only):
               1       3       5       10      21
Edge_W60  -0.0003 -0.0011 -0.0030 -0.0194 -0.0005
Edge_W90  -0.0029  0.0125  0.0124  0.0049  0.0320
Edge_W252  0.0107  0.0159  0.0109  0.0240  0.0963
raw_MFI    0.0209  0.0305  0.0255  0.0574  0.1558
```

- Edge_W90 mean honest IC across horizons: **+0.0106** → direction: **LONG high-Edge (positive IC)**
- Decile forward-return shape (Edge_W90):
  - 5d: [0.61, 0.47, 0.4, 1.08, 0.66, 0.42, 1.66, 0.12, 0.77, 1.31]
  - 10d: [3.0, 0.22, 0.68, 2.41, 1.28, 1.2, 2.66, 1.33, 1.0, 1.31]
  - 21d: [7.84, 2.09, 1.77, 2.52, 2.02, 3.17, 2.7, 2.72, 2.91, 5.8]

**Crux — does funding add information over raw MFI?** Compare the Edge rows to `raw_MFI` above: if Edge's honest IC is no larger (or same sign/insignificant), funding does not rescue the signal.

## Figures
- `figures/variantA_funding_dist.png`
- `figures/variantA_joint_dist.png`
- `figures/variantA_ic_compare.png`