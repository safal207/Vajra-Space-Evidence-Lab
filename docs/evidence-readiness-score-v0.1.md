# Evidence Readiness Score v0.1

Evidence Readiness Score (ERS) is a deterministic 0–100 score for each UER claim.

**ERS is not a probability that a scientific claim is true.** It measures how ready the encoded claim is for responsible review and downstream use given the evidence structure currently represented in the UER.

## Dimensions

| Dimension | Max | Purpose |
|---|---:|---|
| Provenance | 20 | Are linked evidence objects traceable to sources? |
| Evidence directness | 20 | How direct are the supporting evidence types? |
| Inferential distance | 20 | How far is the claim type from direct observation? |
| Assumption transparency | 15 | Are assumptions explicit and source-linked when needed? |
| Challenge coverage | 15 | Are negative evidence, contradictions, or claim-relevant alternatives represented? |
| Discriminating path | 10 | For inferential claims, is there a concrete future observation that distinguishes claim-relevant hypotheses? |

Total: **100**.

## Evidence directness weights

- direct observation: 20
- derived measurement / statistical result: 16
- upper limit / non-detection / negative result: 14
- literature evidence: 12
- model output / simulation: 6

For a claim with multiple supporting evidence objects, the component is the rounded mean of their evidence-type weights.

## Inferential-distance weights

- observational: 20
- derived: 18
- statistical: 16
- interpretation: 10
- model-dependent: 5
- speculative: 2

This intentionally prevents a model-dependent mechanism from receiving the same readiness score as a directly observed or tightly derived claim merely because both have good provenance.

## Claim-local challenge and discrimination

ERS v0.1 prevents event-level leakage between unrelated claims.

A hypothesis is **relevant to a claim** only when the hypothesis supporting/contradicting evidence overlaps the evidence linked to that claim. Challenge coverage and discriminating-path credit for interpretive, model-dependent, or speculative claims are computed only from those claim-relevant hypotheses.

This means that competing mechanism hypotheses elsewhere in the same event record cannot raise the readiness score of an unrelated claim.

For `observational`, `derived`, and `statistical` claims:

- mechanism-level competing hypotheses are not required for challenge coverage;
- challenge coverage receives 12/15 when no explicit negative/contradicting evidence is linked;
- a future hypothesis-discriminating experiment is treated as **not applicable**, so the discriminating-path component receives 10/10 rather than penalizing the claim for unrelated mechanism uncertainty.

For `interpretation`, `model_dependent`, and `speculative` claims:

- challenge coverage receives credit from explicit negative/contradicting evidence or from at least two claim-relevant alternatives;
- discriminating-path credit is awarded only when a recorded future observation distinguishes at least two claim-relevant hypotheses.

## Bands

- **REVIEW_READY — 85–100**: evidence chain is structurally strong enough for direct expert review, while preserving stated uncertainty.
- **CONDITIONAL — 70–84**: useful and reviewable, but meaningful inferential or model dependencies remain.
- **LIMITED — 50–69**: substantial evidence-chain gaps or inferential distance limit downstream use.
- **INSUFFICIENT — 0–49**: not ready for responsible downstream use without additional evidence or structure.

## Interpretation rules

1. Do not convert ERS into a confidence probability.
2. Do not average unrelated claims into a single event-truth score.
3. Do not let hypotheses attached to one claim inflate another claim's challenge or discrimination score.
4. A high ERS can coexist with scientific uncertainty; it means the uncertainty is well represented and reviewable.
5. A model-dependent claim should remain penalized for inferential distance even when assumptions and provenance are excellent.
6. Scores are reproducible from the UER and must change when the canonical evidence structure changes.
7. ERS v0.1 is a protocol heuristic, not a validated scientific metric; its weights should be calibrated with domain-expert review before decision-critical use.

## EP260321a pilot

The initial pilot deliberately scores claims separately:

- SN association: high readiness because it is close to observed/derived evidence; unrelated jet hypotheses do not affect its score.
- shock-breakout interpretation: conditional because model output contributes to the inference and its challenge/discrimination credit comes only from hypotheses sharing its evidence.
- powerful on-axis jet disfavoring: conditional because the conclusion is model-dependent even though non-detections and upper limits are strong constraints.
- choked-outflow explanation: conditional because the mechanism is inferred rather than directly observed.

This separation is the point of ERS: **strong evidence hygiene must not collapse observation, constraint, and mechanism into one undifferentiated confidence label.**
