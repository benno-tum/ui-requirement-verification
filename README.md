# UI Requirement Verification

Code and sample outputs for deriving and verifying UI-facing software requirements from screenshot flows.

## Backend

Run the FastAPI server from the repository root:

```bash
PYTHONPATH=src uvicorn ui_verifier.api.main:app --reload
```

Relevant endpoints now include:

- `GET /flows`
- `GET /flows/{flow_id}`
- `GET /flows/{flow_id}/steps`
- `GET /flows/{flow_id}/candidates`
- `GET /flows/{flow_id}/gold`
- `GET /flows/{flow_id}/verification/latest`
- `POST /verify`

Static screenshots are served under `/static/flows/...`.

## Frontend

A lightweight React + Vite + TypeScript frontend is available in `frontend/`.

```bash
cd frontend
npm install
npm run dev
```

By default the frontend calls `http://127.0.0.1:8000`. To override this, set `VITE_API_BASE_URL`.
