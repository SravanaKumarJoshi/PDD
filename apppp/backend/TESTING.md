# Testing Guide — BioPolymer Backend

## Quick Start

```bash
cd backend
pip install -r requirements.txt
python -m pytest tests/ -v --tb=short
```

Unit tests (scoring, CSV ingestion, hard filters, dataset evaluation) run **without** a database.
Integration tests auto-skip locally unless Postgres is available.

---

## Running Integration Tests Locally

Integration tests require a running **PostgreSQL 16** instance.

### Option A: Docker Compose (recommended)

```bash
# Start Postgres
docker compose -f docker-compose.test.yml up -d db

# Run all tests including integration
DATABASE_URL="postgresql+asyncpg://biopolymer:biopolymer@localhost:5432/biopolymer_test" \
TEST_DB_AVAILABLE=true \
python -m pytest tests/ -v --tb=short

# Tear down
docker compose -f docker-compose.test.yml down
```

### Option B: testcontainers (auto-managed Docker)

```bash
pip install testcontainers[postgres]
# testcontainers will auto-start/stop a Postgres container
python -m pytest tests/ -v --tb=short
```

> Requires Docker Desktop running locally.

### Option C: Existing Postgres instance

```bash
# Point to your local Postgres
DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/test_db" \
TEST_DB_AVAILABLE=true \
python -m pytest tests/ -v --tb=short
```

---

## Environment Variables for Tests

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | For integration tests | Async Postgres connection string (`postgresql+asyncpg://...`) |
| `TEST_DB_AVAILABLE` | For integration tests | Set to `true` to enable integration tests |
| `APP_ENV` | Optional | Set to `test` for test-specific config |

---

## Running with Coverage

```bash
python -m pytest tests/ -v --tb=short \
  --cov=app/scoring --cov=app/ingestion \
  --cov-report=term-missing \
  --cov-report=html:htmlcov \
  --cov-fail-under=85
```

Open `htmlcov/index.html` in a browser to inspect coverage.

---

## Running the Evaluation Script

```bash
python evaluate_dataset.py --output evaluation_report.json
```

Exits with code **0** if all validations pass, **1** if any critical check fails (CI-compatible).

---

## Test Structure

| File | Type | DB Required | Tests |
|------|------|-------------|-------|
| `test_scoring.py` | Unit | No | Score helpers, determinism, ties, schema snapshot |
| `test_csv_ingestion.py` | Unit | No | CSV parsing, column remapping, edge cases |
| `test_hard_filters.py` | Unit | No | Sterilization/processing/bio hard constraints |
| `test_dataset_scoring.py` | Unit | No | All 34 materials × 5 profiles, robust ranking |
| `test_api_integration.py` | Integration | **Yes** | CRUD, 422 validation, auth, endpoints |

---

## Reproducibility

The scoring engine is **fully deterministic**:
- No randomness (no `random` module, no PRNG seeding needed)
- Python's `list.sort()` uses Timsort (stable sort) — tied scores preserve insertion order
- Tie-breaker rule: materials with equal scores appear in their original database/input order
- Verified by `test_determinism_100_runs` and `test_determinism_dataset` (50 full-dataset runs)
