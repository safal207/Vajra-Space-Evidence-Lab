# Unified Evidence Record (UER) v0.1

## Purpose

Unified Evidence Record (UER) is a machine-readable format for preserving the chain from a scientific event or alert to later interpretation.

UER is intentionally narrower than a publication database. It does not replace observatory archives, circulars, papers, DOI infrastructure, or domain standards. It provides an integration, provenance, and reasoning layer over existing sources.

The core rule is:

> **Claim is not evidence. Observation is not inference. Model output is not direct measurement.**

## Core chain

```text
alert / event
  -> observation
  -> measurement
  -> derived result
  -> claim
  -> supporting / contradicting evidence
  -> assumptions
  -> competing hypotheses
  -> discriminating observation
```

Every object should preserve provenance and an explicit evidence type.

## Design goals

1. Represent heterogeneous observations in one common structure.
2. Keep direct observations separate from derived or model-dependent statements.
3. Preserve upper limits, non-detections, contradictions, and uncertainty.
4. Make assumptions visible instead of burying them in prose.
5. Preserve competing hypotheses instead of storing only the favored explanation.
6. Record which future observation would most efficiently discriminate among surviving hypotheses.
7. Minimize duplicate manual documentation by linking to existing sources rather than copying them.

## Top-level record

A UER record contains:

- `uer_version`
- `record_id`
- `event`
- `sources`
- `evidence`
- `claims`
- `assumptions`
- `hypotheses`
- `discriminating_observations`
- `readiness`

The machine-readable schema is defined in [`schemas/uer-v0.1.schema.json`](../schemas/uer-v0.1.schema.json).

## Evidence types

UER v0.1 supports these evidence types:

- `direct_observation`
- `derived_measurement`
- `upper_limit`
- `non_detection`
- `statistical_result`
- `model_output`
- `simulation`
- `literature_evidence`
- `negative_result`

An evidence object should state what was observed or derived, its source, and—where applicable—its value, unit, uncertainty, time, and band.

## Claim types

Claims are explicitly typed:

- `observational`
- `derived`
- `statistical`
- `interpretation`
- `model_dependent`
- `speculative`

A claim can reference evidence that supports or contradicts it and assumptions on which it depends.

## Hypothesis status

Competing hypotheses use one of:

- `active`
- `favored`
- `disfavored`
- `rejected`
- `unresolved`

UER does not require a single winning hypothesis.

## Readiness status

The same scientific claim can have different readiness for different decisions. UER v0.1 uses:

- `SUPPORTED`
- `CONDITIONAL`
- `DISPUTED`
- `INSUFFICIENT_EVIDENCE`

Suggested decision contexts include:

- public communication
- telescope-time allocation
- theoretical-model comparison
- AI training labels
- population inference
- mission forecasting

## Validation rules

### V1 — Claim provenance

Every non-speculative claim should reference at least one evidence object or explicitly explain why evidence is currently missing.

### V2 — Evidence provenance

Every evidence object must reference a source identifier.

### V3 — Measurement integrity

Numeric measurements should provide a unit when one exists. Missing values must be represented as `null`, not invented or silently inferred.

### V4 — Model separation

A model output must never be labeled `direct_observation`.

### V5 — Assumption visibility

A `model_dependent` claim should reference its assumptions. An empty assumption list means that none have yet been encoded, not that the claim is assumption-free.

### V6 — Negative evidence preservation

Upper limits and non-detections are first-class evidence and must not disappear from the chain.

### V7 — Contradiction support

A claim may contain both supporting and contradicting evidence.

### V8 — Source versioning

Preprints, accepted manuscripts, and versions of record should be distinguishable in source metadata.

## Initial pilot

The first public UER record is:

[`records/ep260321a-sn2026gzf.uer.json`](../records/ep260321a-sn2026gzf.uer.json)

It models the evidence boundary around Einstein Probe transient **EP260321a** and broad-lined Type Ic supernova **SN 2026gzf**.

The record deliberately distinguishes:

- soft X-ray detection and measured properties;
- the SN association;
- X-ray/radio non-detections and upper limits;
- constraints on successful relativistic-jet scenarios;
- the proposed weak/mildly relativistic choked-outflow interpretation.

The final interpretation is represented as an inference, not as a directly observed jet.

## Thesis

Scientific knowledge should be representable not only as documents, but as a verifiable chain:

```text
observation
-> measurement
-> evidence
-> claim
-> assumptions
-> uncertainty
-> competing hypotheses
-> next discriminating observation
```

UER v0.1 is an experimental open format. It is expected to change as domain experts review real records.