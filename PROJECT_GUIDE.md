# CloudEyes Project Guide

> Read this file before changing the architecture or starting major implementation work.

## Purpose

CloudEyes exists to answer:

> Is this provider worth using, for which workload, under what scope, and based on what evidence?

## Core principles

1. One sample never represents an entire provider.
2. CloudEyes must not conclude beyond the measured scope.
3. Raw output is preserved.
4. Every protocol and profile is versioned.
5. Measurement, evidence, assessment, and explanation are separate layers.
6. Compatible samples are grouped into cohorts before provider-level analysis.
7. Every verdict must be traceable to evidence.
8. Reproducibility and accuracy are more important than feature count.
9. A universal provider score is not the primary source of truth.
10. AI may summarize later, but deterministic evidence rules remain authoritative.

## Data flow

Agent → Measurement → Evidence → Sample → Validation → Cohort → Assessment → Explanation → Provider Report → Dashboard

## Main components

- `agent/`: runs discovery and benchmark profiles.
- `core/`: validates, normalizes, aggregates, assesses, and explains.
- `catalog/`: versioned metrics, criteria, use cases, capabilities, and protocols.
- `schemas/`: stable data contracts.
- `platform/`: future API, ingestion, repository, workers, moderation, and dashboard.
- `reports/`: report renderers and templates.
- `tests/`: unit, integration, contract, regression, and performance tests.

## Current status

- Phase: Foundation
- Version: 0.1.0-dev
- Functional benchmark logic: Not implemented
- Platform: Skeleton only

## Implementation order

1. Core data models and schemas
2. Agent discovery
3. General profile
4. Sample builder and validator
5. Storage profile
6. Networking profile
7. Cohort builder
8. Provider aggregation
9. Rule-based assessment and explanation
10. JSON and Markdown reports
11. API and dashboard

## Daily update rule

At the end of each development session:

1. Update `DEVELOPMENT_LOG.md`.
2. Update the status and next task in this file.
3. Record architectural decisions in `ARCHITECTURE_DECISIONS.md`.
4. Update `ROADMAP.md` if milestone scope changes.
5. Update `CHANGELOG.md` for externally visible behavior.
