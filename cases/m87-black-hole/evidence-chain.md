# M87* Evidence Chain v0.1

## Current Vajra status

**Bundle status:** `incomplete`  
**Vajra evidence level:** `S0`

This does **not** mean the EHT result has no scientific support. It means Vajra has not yet ingested and hashed the released dataset bytes, pinned the exact calibration and imaging environments, or reproduced the result locally. External confidence must not be silently converted into an internal reproducibility verdict.

## Primary-source register

| Ref | Primary source | Role in the chain |
|---|---|---|
| EHT-I | [Paper I: The Shadow of the Supermassive Black Hole](https://arxiv.org/abs/1906.11238) | Headline observational and physical interpretation claims |
| EHT-II | [Paper II: Array and Instrumentation](https://arxiv.org/abs/1906.11239) | Array design, wavelength, resolution, recording, timing and instrumentation |
| EHT-III | [Paper III: Data Processing and Calibration](https://arxiv.org/abs/1906.11240) | Correlation, calibration, fringe fitting, QA and systematic-error claims |
| EHT-IV | [Paper IV: Imaging the Central Supermassive Black Hole](https://arxiv.org/abs/1906.11241) | Blind imaging teams, CLEAN/RML methods, synthetic tests and parameter surveys |
| DATA-2019-D01-01 | [First M87 EHT Results: Calibrated Data](https://doi.org/10.25739/g85n-f134) | Public calibrated-data release identifier |
| PIPELINES-2019-D01-02 | [First M87 EHT Results: Imaging Pipelines](https://github.com/eventhorizontelescope/2019-D01-02) | Public imaging pipeline repository |
| EHT-DATA-CATALOG | [EHT Data Products](https://eventhorizontelescope.org/for-astronomers/data) | Official release catalog and later data products |

## Causal and evidential chain

### 1. Instrument configuration

The 2017 EHT campaign used an Earth-scale very-long-baseline interferometry array at approximately 1.3 mm wavelength. EHT Paper II reports an angular resolution of approximately 25 microarcseconds, high-bandwidth recording systems, and hydrogen-maser frequency standards for coherent capture across geographically separated stations.

**Vajra type:** `OBS-supporting infrastructure`  
**What this establishes:** the array was designed with sufficient nominal resolution to sample horizon-scale structure in M87.  
**What this does not establish:** that a black-hole shadow was directly photographed.

### 2. Recorded interferometric observables

The primary measurements are not ordinary camera pixels. The array records signals that are correlated into interferometric observables, including visibility amplitudes/phases and closure quantities.

**Vajra type:** `OBS`  
**Boundary:** the ring-shaped image is downstream of calibration and computational reconstruction.

### 3. Calibration and quality assurance

EHT Paper III describes three independent pipelines for phase calibration and fringe detection. The publication reports cross-pipeline consistency and baseline systematic limits of approximately 2% in amplitude and 1 degree in phase.

Calibration chain to model:

```text
station clocks / receivers
→ high-bandwidth recordings
→ correlation
→ atmospheric and instrumental corrections
→ fringe detection and phase calibration
→ amplitude calibration
→ closure and consistency checks
→ calibrated VLBI data products
```

**Current Vajra gap:** exact released files have not been downloaded and content-hashed; pipeline commits, parameters and execution environments are not pinned.

### 4. Image reconstruction

EHT Paper IV describes a two-stage robustness procedure:

1. Four teams worked blind to one another and used both CLEAN and regularized maximum-likelihood approaches.
2. Synthetic datasets with known ground truth were reconstructed across broad parameter surveys to assess method and parameter sensitivity.

The published analysis reports that the ring diameter and asymmetry were stable across imaging methods and observing nights.

**Vajra type:** `REC`  
**Current Vajra status:** `partial` reproducibility because data and pipelines are publicly identified, but this repository has not executed the pinned workflow.

### 5. Physical interpretation

Paper I reports an asymmetric ring of roughly 42 ± 3 microarcseconds with a central brightness depression. The collaboration interprets the result as consistent with the expected shadow-scale morphology of a Kerr black hole and compares the observations with general-relativistic magnetohydrodynamic and radiative-transfer models.

**Vajra type:** `INF`  
**Critical boundary:** consistency with a Kerr black-hole model is not logically identical to direct observation of an event horizon. The observation, reconstruction and physical interpretation must remain separate claims.

## Alternative hypotheses and falsifiers

### A. Calibration artefact

**Alternative:** the ring-scale signature is produced by shared calibration errors.

Evidence that weakens it:
- agreement among independently developed calibration pipelines;
- closure-quantity checks;
- persistence across observing days;
- station-removal and systematic-error sensitivity analyses.

Vajra falsifier:
- reproduce the ring from independently calibrated data;
- demonstrate that plausible calibration perturbations do not create or erase the core morphology beyond declared tolerances.

### B. Imaging-prior or algorithm artefact

**Alternative:** sparse Fourier coverage plus chosen priors forces a ring.

Evidence that weakens it:
- blind teams;
- CLEAN and multiple regularized maximum-likelihood methods;
- synthetic-data reconstruction tests;
- parameter surveys;
- later independent reanalyses reported by EHT.

Vajra falsifier:
- execute independent algorithms against the same pinned observables;
- compare morphology metrics rather than only visual similarity;
- include negative controls where non-ring ground truths must not become rings.

### C. Jet-dominated compact structure without a shadow interpretation

**Alternative:** the measured compact structure is primarily a jet-base morphology that does not require a shadow-scale compact object.

Required test:
- compare visibility-domain predictions of jet-only, crescent, ring and hybrid models;
- test whether each model reproduces null locations, closure quantities, temporal behavior and multiwavelength constraints.

### D. Non-Kerr compact object

**Alternative:** the central object is ultracompact but not described by the Kerr solution.

Boundary:
- a ring and central depression alone do not uniquely eliminate all exotic compact-object models.

Required test:
- register explicit alternative models;
- derive distinguishable predictions for ring size, sub-ring structure, polarization, variability or multi-epoch behavior;
- update the verdict only when those predictions are tested.

### E. Source variability interacting with Earth-rotation synthesis

**Alternative:** time variability biases the reconstructed static morphology.

Required test:
- reconstruct individual days and shorter intervals;
- model excess variability in visibility space;
- compare stable versus variable-source reconstructions.

## Fail-closed verdict

At this stage Vajra may say:

> Public primary sources describe an Earth-scale 1.3 mm VLBI observation, three independent calibration pipelines, multiple blind imaging approaches, synthetic-data tests, and a stable ring-scale reconstruction interpreted as consistent with a Kerr black-hole shadow.

Vajra may **not yet** say:

> Vajra independently reproduced and verified the M87* black-hole image.

## Next executable acceptance criteria

- [ ] Download the exact calibrated-data release and record per-file SHA-256 hashes.
- [ ] Pin calibration and imaging repository commits.
- [ ] Record container image digest and dependency lock.
- [ ] Execute at least one published imaging pipeline.
- [ ] Run negative-control and parameter-sensitivity fixtures.
- [ ] Register independent-reanalysis evidence objects.
- [ ] Replace the sentinel observation hash.
- [ ] Recalculate the evidence level deterministically.
