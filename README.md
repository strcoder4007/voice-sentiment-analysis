# Voice Sentiment Analysis

Customer call analysis app with:
- Speech-to-Text + speaker diarization via ElevenLabs
- Structured conversation analysis via OpenAI
- React frontend for multi-file upload and rich results display
- FastAPI backend orchestrating transcription, diarization, and analysis

This repository contains both the backend API (FastAPI) and the frontend web app (React).

- GitHub: https://github.com/strcoder4007/voice-sentiment-analysis

---

## Features

- Upload one or more audio files (wav, mp3, m4a, flac)
- Automatic transcription with timestamps and speaker diarization
- Grouped human-readable transcript by speaker turns with HH:MM:SS.mmm ranges
- Structured JSON analysis including:
  - emotion_overall + confidence
  - satisfaction + confidence
  - summary, customer_intent, issues
  - action_items with owner and due date
  - agent_speaker_label + identification confidence
  - agent_improvement_opportunities (category, evidence, impact, recommendation)
  - post_call_recommendations
  - follow_up_message_draft
  - sentiment_analysis narrative
- Health check endpoint and robust error handling
- CORS enabled for local development
- Simple UI with results cards and JSON viewer

---

## Architecture and Flow

- Frontend (React)
  - Multi-file audio selection and upload
  - Displays result cards and raw JSON
  - Default backend URL: http://localhost:8000/analyze/

- Backend (FastAPI)
  - POST /analyze/: accepts multipart form-data (field key: files, repeated)
  - Transcribes using ElevenLabs STT with diarization and word-level timestamps
  - Groups words into speaker turns; renders readable transcript with timecodes
  - Sends transcript summary to OpenAI for structured conversation analysis
  - Returns combined metadata, transcript, and analysis JSON per file

- External Services
  - ElevenLabs Speech-to-Text API
  - OpenAI Responses API

---

## Repository Structure

```
voice-sentiment-analysis/
├─ backend/
│  ├─ main.py                # FastAPI app and orchestration logic
│  └─ requirements.txt       # Python dependencies
├─ frontend/
│  ├─ package.json           # React app and scripts
│  ├─ public/                # CRA public assets
│  └─ src/
│     ├─ App.js              # Upload UI and results grid
│     ├─ App.css             # Styles
│     └─ components/
│        ├─ ResultCard.jsx   # Result card UI
│        └─ JsonViewer.jsx   # JSON viewer component
├─ TODO.md                   # Project roadmap
├─ voxtral.py                # (not used by app runtime)
└─ README.md                 # This file
```

---

## Prerequisites

- macOS, Linux, or Windows
- Python 3.10+ recommended
- Node.js 18+ and npm
- API keys:
  - OpenAI API key (with access to the selected model)
  - ElevenLabs API key

Costs: Using OpenAI and ElevenLabs APIs incurs usage charges. Ensure your accounts are configured appropriately.

---

## Quick Start

1) Configure environment variables (create a .env file in the project root):
```
OPENAI_API_KEY=sk-...
ELEVENLABS_API_KEY=eleven-...
```

2) Start the backend (FastAPI):
```
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt

# Option A: run via uvicorn (recommended during dev)
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Option B: run the module directly
python backend/main.py
```

3) Start the frontend (React):
```
cd frontend
npm install
npm start
```

- Frontend dev server: http://localhost:3000
- Backend API: http://localhost:8000
- The default frontend expects the backend at http://localhost:8000/analyze/

---

## Configuration

- Environment variables (in project root .env; loaded by python-dotenv):
  - `OPENAI_API_KEY` — required
  - `ELEVENLABS_API_KEY` — required

- Backend ports
  - Default is 8000; change via uvicorn flag if desired
  - CORS is enabled for all origins by default (FastAPI middleware)

- OpenAI model
  - Backend code uses `model="gpt-5"` in `backend/main.py`
  - Ensure your account has access to this model; otherwise update the model string to an available one (e.g., `gpt-4o` or `gpt-4o-mini`) in `backend/main.py`

- Frontend API URL
  - Currently hardcoded in `frontend/src/App.js`:
    ```
    fetch("http://localhost:8000/analyze/", { ... })
    ```
  - If deploying or changing ports, update this URL accordingly

---

## API

Base URL: `http://localhost:8000`

- GET `/`
  - Returns: `{ "message": "Voice Sentiment Analysis API is running" }`

- GET `/health`
  - Returns:
    ```
    {
      "status": "healthy",
      "openai_configured": true|false,
      "elevenlabs_configured": true|false
    }
    ```

- POST `/analyze/`
  - Content-Type: multipart/form-data
  - Field name for files: `files` (repeat for multiple)
  - Returns:
    ```
    {
      "results": [
        {
          "filename": "call1.mp3",
          "date": "YYYY-MM-DD",
          "time": "HH:MM:SS",
          "audio_length": "HH:MM:SS.mmm",
          "file_size": 12345,
          "transcription": "...",
          "analysis": {
            "emotion_overall": "very_negative | negative | neutral | positive | very_positive",
            "emotion_confidence": 0.0,
            "satisfaction": "very_unsatisfied | unsatisfied | neutral | satisfied | very_satisfied",
            "satisfaction_confidence": 0.0,
            "summary": "2-4 sentences...",
            "customer_intent": "one sentence...",
            "issues": ["..."],
            "action_items": [
              { "owner": "agent|customer|other", "item": "...", "due": "YYYY-MM-DD|null" }
            ],
            "agent_speaker_label": "Speaker 1 | Speaker 2 | Speaker 3 | unknown",
            "agent_identification_confidence": 0.0,
            "agent_improvement_opportunities": [
              {
                "category": "empathy|discovery|clarity|solution_quality|ownership|pace|listening|policy_adherence|product_knowledge",
                "observation": "...",
                "evidence": "\"short quote\"",
                "recommended_change": "...",
                "impact": "low|medium|high"
              }
            ],
            "post_call_recommendations": ["..."],
            "follow_up_message_draft": "short paragraph...",
            "sentiment_analysis": "2-4 sentences of critical-thinking analysis..."
          }
        }
      ],
      "total_processed": 1
    }
    ```

Example curl (single file):
```
curl -X POST http://localhost:8000/analyze/ \
  -F "files=@/path/to/audio.mp3;type=audio/mpeg"
```

Example curl (multiple files):
```
curl -X POST http://localhost:8000/analyze/ \
  -F "files=@/path/to/call1.wav;type=audio/wav" \
  -F "files=@/path/to/call2.m4a;type=audio/m4a"
```

---

## Frontend

- Tech: React (CRA), Result cards and JSON viewer
- File input accepts multiple audio files
- Action button posts to `/analyze/`
- Error states shown inline

To change the API URL:
- Edit `frontend/src/App.js` and update the fetch URL to your backend endpoint

Run:
```
cd frontend
npm install
npm start
```

Build for production:
```
npm run build
```

---

## Backend

- Tech: FastAPI, httpx, python-dotenv
- Entrypoints:
  - `backend/main.py` (direct run)
  - `uvicorn backend.main:app --reload --port 8000`
- Key pipeline (per file):
  1) Validate and read bytes
  2) ElevenLabs STT with diarization and `timestamps_granularity="word"`
  3) Group words into speaker turns, render readable transcript with time ranges
  4) Send enriched prompt to OpenAI Responses API for structured analysis JSON
  5) Safe-parse JSON; add metadata and return

Python dependencies: see `backend/requirements.txt`

---

## ElevenLabs and OpenAI Notes

- ElevenLabs Speech-to-Text API:
  - Endpoint: `POST https://api.elevenlabs.io/v1/speech-to-text`
  - Requires `xi-api-key` header
  - This app requests diarization and word-level timestamps
  - Supported formats include common audio types (mp3, wav, m4a, flac)

- OpenAI Responses API:
  - Model string configurable in `backend/main.py` (`gpt-5` by default)
  - If your account lacks access to the default model, change it to one you can use (e.g., `gpt-4o`)

---

## Troubleshooting

- 500: OpenAI API key not configured
  - Ensure `.env` contains `OPENAI_API_KEY` and the backend process can read it
- 500: ElevenLabs API key not configured
  - Ensure `.env` contains `ELEVENLABS_API_KEY`
- 502 from ElevenLabs STT
  - Check file format, account plan/limits, and API key validity
- Empty or invalid OpenAI response
  - Ensure model access; if needed, switch to a supported model in `backend/main.py`
- CORS or network errors in the browser
  - Confirm backend running at http://localhost:8000
  - Verify fetch URL in `frontend/src/App.js`
- Large files/slow responses
  - Backend uses httpx timeout of 120s; adjust if needed

---

## Security and Privacy

- API keys are loaded from environment variables; do not commit them to source control
- Uploaded audio is processed in-memory for analysis then returned in results
- Be mindful of sensitive content in audio/transcripts and downstream storage

---

## Roadmap

See [TODO.md](./TODO.md). Planned items include:
- Improved multiple upload UX
- Robust error states and retries
- Accuracy validation and diarization quality checks
- Deployment docs and environment management
- CI, unit/integration tests with sample audio

---

## Development Tips

- Run backend with `--reload` for hot reload during API edits:
  ```
  uvicorn backend.main:app --reload --port 8000
  ```
- Adjust the analysis schema/prompt in `backend/main.py` under `schema_template`, `system_msg`, and `user_prompt`
- To change diarization behavior or language hints, modify `transcribe_with_elevenlabs` parameters in `backend/main.py`

---

## License

No license specified.
