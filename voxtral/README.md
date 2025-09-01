# Voxtral (Voice Sentiment & Call Analysis)

Lightweight pipeline to analyze voice calls with Mistral's Voxtral model and render actionable insights in a simple web UI.

- Backend: FastAPI service wrapping the Voxtral model (`voxtral/server.py`)
- Frontend: Static HTML/JS/CSS (`voxtral/frontend/*`) that uploads audio and renders the returned JSON
- Schema: Lean, high-value JSON output optimized for actionability and low redundancy

## Quickstart

### 1) Environment

- Python 3.9+ (3.10 recommended)
- Optional GPU with CUDA for faster inference (CPU works but is slower)

Install dependencies:

```bash
cd voxtral
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Run the backend (FastAPI + Voxtral)

Run from the `voxtral/` directory (so `server:app` can be imported):

```bash
uvicorn server:app --host 0.0.0.0 --port 8002
```

- Health check: http://localhost:8002/health
- API endpoint: POST http://localhost:8002/api/analyze (multipart upload: `file=@/path/to/audio`)

Dev mode with hot reload (optional):

```bash
uvicorn server:app --reload --port 8002
```

### 3) Run the frontend (static)

Serve the static frontend from `voxtral/frontend/`:

```bash
cd voxtral/frontend
python3 -m http.server 8001
```

Open http://localhost:8001

The frontend targets the backend at `http://localhost:8002` by default (see `frontend/app.js` `API_BASE`). If you change backend host/port, update `API_BASE` accordingly.

---

## Architecture Overview

- `voxtral/server.py`
  - Loads Hugging Face model `mistralai/Voxtral-Mini-3B-2507` using `AutoProcessor` and `VoxtralForConditionalGeneration`
  - Auto-selects device & dtype (CUDA with bf16/fp16, else CPU fp32)
  - Exposes:
    - `GET /health` — device/dtype/model_loaded
    - `POST /api/analyze` — accepts audio file, returns structured JSON per schema
  - Saves uploaded audio to a temporary file, analyzes, then cleans up
  - Generates responses with `max_new_tokens=1536`, attempts strict JSON parsing (and trims to outermost braces if needed)

- `voxtral/frontend/*`
  - Static HTML/CSS/JS
  - Uploads audio & calls backend
  - Renders the returned JSON into sections with auto-hide for empty sections
  - Falls back to a sample JSON if backend is unavailable

---

## API

### POST /api/analyze

- Content-Type: `multipart/form-data`
- Field: `file` (the audio file to analyze)

Example:

```bash
curl -X POST http://localhost:8002/api/analyze \
  -F "file=@/path/to/audio.wav"
```

#### Supported audio formats

The server infers extension by MIME or filename:

- mp3 (`audio/mpeg`, `audio/mp3`)
- wav (`audio/wav`, `audio/x-wav`)
- ogg (`audio/ogg`)
- webm (`audio/webm`)
- flac (`audio/flac`, `audio/x-flac`)
- aac (`audio/aac`)
- m4a (`audio/mp4`)

If no extension can be inferred, defaults to `.wav`.

---

## Output JSON Schema (Contract)

The backend returns a JSON object matching the schema below (lists are concise — 3–5 items max). If a field is not applicable, the backend instructs the model to use `""` (strings), `[]` (arrays), or appropriate nulls.

```json
{
  "emotion_overall": "very_negative | negative | neutral | positive | very_positive",
  "emotion_confidence": 0.0,
  "satisfaction": "very_unsatisfied | unsatisfied | neutral | satisfied | very_satisfied",
  "satisfaction_confidence": 0.0,

  "summary": "2-4 concise sentences summarizing the conversation",
  "customer_intent": "primary customer intent in one sentence",
  "issues": ["list of key issues raised by the customer"],

  "agent_speaker_label": "Speaker 1 | Speaker 2 | Speaker 3 | unknown",
  "agent_identification_confidence": 0.0,

  "speaker_sentiment": [
    {
      "speaker_label": "Speaker 1 | Speaker 2 | Speaker 3 | unknown",
      "role": "agent | customer | other | unknown",
      "sentiment": "very_negative | negative | neutral | positive | very_positive",
      "confidence": 0.0
    }
  ],

  "objections": [
    {
      "type": "price | timing | competitor | feature_gap | trust | contract | other",
      "severity": "low | medium | high",
      "evidence": "short quote showing the objection",
      "agent_response_quality": "poor | adequate | strong",
      "recommended_response": "improved response for next time"
    }
  ],

  "next_best_actions_ranked": [
    {
      "priority": 1,
      "action": "specific action",
      "owner": "agent | customer | other",
      "due": "YYYY-MM-DD or null",
      "rationale": "why this helps"
    }
  ],

  "agent_improvement_opportunities": [
    {
      "category": "empathy | discovery | clarity | solution_quality | ownership | pace | listening | policy_adherence | product_knowledge",
      "observation": "what the agent did/said",
      "evidence": "short direct quote",
      "recommended_change": "what to do better next time",
      "impact": "low | medium | high"
    }
  ],

  "knowledge_gaps": ["areas where the agent lacked info"],

  "customer_commitment": {
    "level": "none | soft | strong",
    "statements": ["quotes indicating commitment level"]
  },

  "outcome": {
    "resolution_status": "resolved | partially_resolved | unresolved | n/a",
    "reason": "brief reason supporting status",
    "follow_up_required": true
  },

  "clarifying_questions_to_ask_next_time": ["high-leverage questions to ask next time"],
  "follow_up_message_draft": "1 short paragraph the agent can send as a follow-up now",

  "key_quotes": [
    {
      "type": "pain | value | objection | decision | other",
      "quote": "short, verbatim quote"
    }
  ],

  "timeline": [
    {
      "approx_time": "MM:SS or HH:MM:SS",
      "event": "turning point or key moment in one short phrase"
    }
  ]
}
```

### Field Notes (short)

- emotion_*: overall affect; compact signal
- satisfaction_*: business outcome proxy distinct from emotion
- summary / customer_intent / issues: human/contextual overview
- agent_speaker_label (+confidence): best-guess mapping for agent
- speaker_sentiment[]: per-speaker granularity with confidence
- objections[]: high leverage for sales/support; includes evidence and improved response
- next_best_actions_ranked[]: prioritized, owned actions with rationale
- agent_improvement_opportunities[]: coaching surface with evidence and impact
- knowledge_gaps[]: where enablement is needed
- customer_commitment: deal/progress proxy with supporting quotes
- outcome: resolution status, reason, and whether follow-up is needed
- clarifying_questions_to_ask_next_time[]: high-leverage prompts
- follow_up_message_draft: ready-to-send short paragraph
- key_quotes[]: traceability/explainability
- timeline[]: turning points with approximate timestamps

> Note: The frontend hides sections that are missing/empty. If you see sections like “What Worked/Didn't Work” in the UI, they will simply remain hidden unless the JSON contains those fields (the current backend schema does not produce them).

---

## Development Notes

- Edit schema/prompt in: `voxtral/server.py`
  - `SCHEMA_TEMPLATE`: authoritative output contract
  - `USER_PROMPT`: instructions aligned to the schema
- Token budget: `max_new_tokens=1536`. If outputs truncate or become verbose, prune schema further or simplify prompt.
- Device selection:
  - CUDA: prefers `bfloat16` if supported, else `float16`
  - CPU: uses `float32`
- JSON parsing:
  - Strict parse; if model leaks tokens, server trims to outermost braces and retries parse. If parsing fails, returns HTTP 502.

---

## Troubleshooting

- Backend 500 “Model not available”:
  - Check internet for model download on first run
  - Ensure sufficient VRAM for GPU (fallback is CPU but slower)
  - See `/health` for `device`, `dtype`, and `model_loaded`
- Backend 502 “invalid JSON”:
  - Model emitted malformed JSON; try again
  - Consider reducing schema size or `max_new_tokens`
- CORS:
  - Server allows `allow_origins=["*"]` (ok for local/dev). Restrict in production.
- Port conflicts:
  - Change ports or stop existing services
  - If backend port changes, update `API_BASE` in `frontend/app.js`
- Slow inference:
  - CPU inference can be slow for long audio; trim audio or use GPU

---

## Credits

- Model: [mistralai/Voxtral-Mini-3B-2507](https://huggingface.co/mistralai/Voxtral-Mini-3B-2507)
- Stack: FastAPI, Hugging Face Transformers, plain HTML/CSS/JS
