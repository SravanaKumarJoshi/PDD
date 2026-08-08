# BioPolymer AI Screening Platform

AI-powered decision-support platform that recommends natural biopolymers (polysaccharides) for biomedical packaging applications.

## Project Structure

```
├── android/          # Kotlin / Jetpack Compose Android app
├── backend/          # Python FastAPI backend
├── docs/             # Documentation
└── .github/          # CI/CD workflows
```

---

## Quick Start

### Backend

```bash
cd backend

# Copy environment file
cp .env.example .env

# Start with Docker
docker-compose up --build

# API will be available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

#### Load Starter Dataset

```bash
# Via curl (while backend is running)
curl -X POST "http://localhost:8000/api/v1/admin/import/csv" \
  -H "X-Admin-Token: change-this-to-a-secure-random-string" \
  -F "file=@data/starter_dataset.csv"
```

### Android

1. Open `android/` in Android Studio
2. Sync Gradle dependencies
3. Add `google-services.json` from Firebase Console to `android/app/`
4. Connect emulator or device
5. Run the app

#### Prepopulated Database

The app ships with a bundled Room database (`assets/databases/biopolymer_starter.db`).
To generate this file from the CSV:

```bash
# Use the provided SQLite generation script (or populate via the backend + sync)
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Android | Kotlin, Jetpack Compose, MVVM, Hilt, Room, Retrofit |
| Backend | Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL |
| Auth | Firebase Auth (email + magic link) |
| Scoring | Rule-based weighted scoring (on-device + server) |
| Deployment | Docker, GitHub Actions |

---

## Key Features

- **Guided requirements form** — 7-step wizard covering mechanical, barrier, biological, degradation, processing, sterilization, and sustainability
- **On-device scoring** — Works fully offline with prepopulated database
- **Ranked recommendations** — Score + confidence + explanations for each material
- **Materials catalog** — Offline searchable database with detailed property profiles
- **Save projects** — Store requirement sets + results locally; sync with cloud when logged in
- **Privacy controls** — Data export, deletion, analytics opt-in toggle

---

## API Documentation

Start the backend and visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

See [docs/API.md](docs/API.md) for endpoint details.

---

## Replacing the Starter Dataset

The included dataset contains **34 materials** with `evidence_level` marked as `low` or `med`.
To replace with real, peer-reviewed data:

1. Prepare a CSV matching the schema in `backend/data/starter_dataset.csv`
2. Set `evidence_level` to `high` for well-sourced entries
3. Include DOI references in the `references` column
4. Upload via the admin CSV import endpoint
5. Trigger a material sync from the Android app Settings

---

## Build & Release

### Android Release Bundle

```bash
cd android
./gradlew bundleRelease
# Output: app/build/outputs/bundle/release/app-release.aab
```

### Play Store Checklist

See [docs/PLAY_STORE_CHECKLIST.md](docs/PLAY_STORE_CHECKLIST.md)

---

## License

Proprietary — All Rights Reserved
