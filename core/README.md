# CloudEyes Core

CloudEyes Core contains deterministic, dependency-light logic shared by the local agent and the future platform.

## Complete foundation flow

```text
Sample JSON
→ validation
→ JSON repository
→ compatible cohorts
→ descriptive statistics
→ coverage
→ confidence
→ provider report JSON
```

## Run tests

From the repository root:

```powershell
python -m pip install -e ".[dev]"
python -m pytest
```

## Design rules

- Input samples are immutable dataclasses.
- Every timestamp must include timezone information.
- Cohorts only combine matching provider, product, machine, profile, and protocol identities.
- Repeated measurements inside one sample are reduced to one median value per metric.
- Reports separate measurement, statistical, and coverage confidence.
- Repository writes are validated and atomic.
