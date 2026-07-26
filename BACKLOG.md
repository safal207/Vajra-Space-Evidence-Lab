# Product Backlog

## Product principles

1. Evidence before confidence.
2. Observation is not interpretation.
3. Every transformation must be traceable.
4. Uncertainty is first-class data.
5. Verdicts are superseded, never silently rewritten.
6. AI may assist analysis but may not manufacture authority.
7. Safety decisions require explicit human accountability.

## Evidence levels

- **S0** — claim without inspectable evidence
- **S1** — single-source observation
- **S2** — data available, full reproduction unavailable
- **S3** — result reproduced from published data and code
- **S4** — independently confirmed by another method, instrument, or team
- **S5** — robust multi-channel confirmation with successful predictions

---

## EPIC 0 — Foundation `P0`

### VS-001 Project charter and non-goals
**Acceptance criteria**
- Mission is explicit.
- Scientific verification is separated from institutional trust.
- The project does not claim to replace peer review or physical observatories.
- Safety-relevant boundaries are documented.

### VS-002 Core claim taxonomy
Implement `OBS`, `REC`, `INF`, `SIM`, `PRED`, `SPEC`.

**Acceptance criteria**
- Each claim has exactly one primary type.
- Mixed claims are decomposed into linked atomic claims.
- Unknown claim types fail validation.

### VS-003 Evidence scale S0–S5
**Acceptance criteria**
- Rules are deterministic.
- Missing evidence cannot be compensated by prose confidence.
- Independent confirmation is defined operationally.
- Scores include a machine-readable explanation.

### VS-004 Immutable provenance and supersession
**Acceptance criteria**
- Every card has source hashes and timestamps.
- Previous verdicts remain addressable.
- Corrections create a superseding version.
- No silent mutation of historical evidence.

---

## EPIC 1 — Evidence Card MVP `P0`

### VS-010 Claim JSON schema
### VS-011 Evidence JSON schema
### VS-012 Observation and instrument schemas
### VS-013 Transformation and assumption schemas
### VS-014 Verdict schema
### VS-015 Evidence Card validator
### VS-016 Markdown renderer
### VS-017 Deterministic evidence-level calculator
### VS-018 Audit trail and supersession chain

**Definition of done for the epic**
- Valid cards pass schema validation.
- Unknown verdicts and missing required fields fail closed.
- JSON and Markdown outputs represent the same claim state.
- Test fixtures cover valid, invalid, partial, and superseded cards.

---

## EPIC 2 — M87* Reference Case `P0`

### VS-020 Decompose the headline claim
Split “M87* is a black hole” into atomic claims.

### VS-021 Observation inventory
Record raw observable classes without treating reconstruction as photography.

### VS-022 Instrument and calibration chain
Model telescope network, calibration, synchronization, and uncertainty.

### VS-023 Reconstruction pipeline
Record algorithms, parameters, transformations, and sensitivity.

### VS-024 Alternative hypotheses and falsifiers
### VS-025 Independent confirmations
### VS-026 Publish first complete Evidence Card
### VS-027 Reproducibility limitations report

---

## EPIC 3 — Reproduction Engine `P1`

### VS-030 Reproduction manifest
### VS-031 Pin code, data, environment, and checksums
### VS-032 Containerized execution
### VS-033 Expected-vs-observed comparator
### VS-034 Partial and negative reproduction support
### VS-035 Signed reproduction attestation

---

## EPIC 4 — Causal Universe Graph `P1`

### VS-040 Causal node schema
### VS-041 Causal edge schema
### VS-042 Separate correlation, mechanism, assumption, intervention
### VS-043 Competing causal models
### VS-044 Temporal ordering
### VS-045 Uncertainty propagation
### VS-046 Evidence-to-decision path visualization

---

## EPIC 5 — Space Safety `P1`

### VS-050 Solar storm Evidence Card
### VS-051 Hazardous asteroid Evidence Card
### VS-052 Orbital conjunction Evidence Card
### VS-053 Satellite maneuver execution-proof chain
### VS-054 Human approval and residual-risk model
### VS-055 Mission operator safety-case template

---

## EPIC 6 — Data Connectors `P2`

### VS-060 NASA open-data connector
### VS-061 ESA open-data connector
### VS-062 arXiv metadata connector
### VS-063 DOI / Crossref provenance connector
### VS-064 Observation checksum registry
### VS-065 Freshness, caching, and rate-limit policy

---

## EPIC 7 — Governance `P2`

### VS-070 Public claim registry
### VS-071 Reviewer roles and conflict disclosures
### VS-072 Challenge / rebuttal / supersession workflow
### VS-073 Signed evidence bundles
### VS-074 Transparent appeal process
### VS-075 Adversarial evidence threat model

---

## Current sprint — Foundation Sprint 001

1. **VS-001** Project charter and non-goals
2. **VS-002** Claim taxonomy
3. **VS-003** S0–S5 rules
4. **VS-010** Claim schema
5. **VS-011** Evidence schema
6. **VS-020** M87* claim decomposition
7. Add CI schema validation

## Definition of Done

A task is done only when:

- the contract is documented;
- acceptance criteria are testable;
- implementation and tests exist where applicable;
- provenance is preserved;
- uncertainty and failure states are explicit;
- no public claim exceeds available evidence.

---

## Sprint 001 progress update

- [x] VS-001 Project charter and non-goals
- [x] VS-002 Core claim taxonomy
- [x] VS-003 Evidence scale S0–S5
- [x] VS-010 Claim JSON schema
- [x] VS-011 Evidence JSON schema
- [x] VS-015 Evidence Card validator v0.1
- [x] VS-016 Markdown renderer v0.1
- [x] VS-017 Deterministic evidence-level calculator
- [x] VS-018 Audit trail and supersession ledger foundation
- [x] VS-020 M87* claim decomposition
- [x] VS-021 M87* observation inventory foundation
- [x] VS-022 M87* calibration chain
- [x] VS-023 M87* reconstruction pipeline analysis
- [x] VS-024 Machine-readable alternatives and falsifiers
- [x] CI schema and unit-test validation
- [x] Official M87 data-release ingestion and exact SHA-256 manifest
- [x] Official M87 imaging-release ingestion and exact SHA-256 manifest
- [x] Reproduction Engine v0.1
- [x] Verified OCI environment for `eht-imaging 1.1.0`
- [x] Exact Conda lock with 132 immutable package artifacts
- [x] OCI build, push, pull-by-digest, package import, and official pipeline smoke-test

### Verified OCI checkpoint

- OCI reference: `ghcr.io/safal207/vajra-m87-ehtim@sha256:ced397b05da668df2d07c28ecf8139dde719e9c5f0f7551857d3b63a41076ee5`
- Base image digest: `sha256:e3797091302382ea841498bc93a7b0a50f7c1448333d5e946d2d1608d0c5f43d`
- Environment lock SHA-256: `099067a3cc02fb6cb6e556ada2f9ebeb0d6d9e173e2c61aac3e6b13c0d4527c7`
- Upstream `eht-imaging` commit: `22ae35f307921a4d423aa69f6aed6e93a74ecbc0`
- Upstream tree SHA-256: `efea21644ef3dc837b878431bf1081c4e7e1570084a690e57cfa2ec0714fe5ef`
- Audited compatibility patch SHA-256: `7b432916770f1e45108329aff59b4200e148b864e564ab669a5a841402e7d167`

### Next queue

- [ ] Generate the first M87 FITS output in the verified OCI environment
- [ ] Repeat the reconstruction to test exact determinism
- [ ] Establish expected FITS SHA-256 or a justified semantic comparison contract
- [ ] Encode ring diameter, width, asymmetry, orientation, and data-consistency metrics
- [ ] Add materially independent confirmation objects
- [ ] Publish the complete M87 Evidence Card
