from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
import uvicorn
import datetime
from openai import OpenAI
import os
import json
import logging
from dotenv import load_dotenv
import httpx

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Allow frontend to access backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _format_hhmmss(seconds: float) -> str:
    if seconds is None:
        return "00:00:00"
    ms = int(round((seconds - int(seconds)) * 1000))
    s = int(seconds)
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    return f"{h:02d}:{m:02d}:{sec:02d}.{ms:03d}"


def _safe_parse_json(text: str) -> Dict[str, Any]:
    # First attempt direct parse
    try:
        return json.loads(text)
    except Exception:
        pass
    # Try to extract largest JSON-looking substring
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except Exception:
            pass
    # Fallback
    return {"raw_response": text}


def _group_into_turns(words: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Group consecutive words by speaker_id into turns.
    Returns:
      - turns: List[{speaker_id, start, end, text}]
      - speakers: Ordered unique list of speaker_ids encountered
      - duration: max end time
    """
    turns: List[Dict[str, Any]] = []
    speakers_order: List[str] = []
    curr: Optional[Dict[str, Any]] = None
    duration = 0.0

    # Filter only word-type items if present
    wlist = [w for w in words if w.get("type") in (None, "word")]
    wlist.sort(key=lambda w: (w.get("start", 0.0), w.get("end", 0.0)))

    for w in wlist:
        spk = w.get("speaker_id") or "speaker_1"
        start = float(w.get("start", 0.0))
        end = float(w.get("end", start))
        txt = str(w.get("text", "")).strip()

        if spk not in speakers_order:
            speakers_order.append(spk)

        if not txt:
            duration = max(duration, end)
            continue

        if curr is None:
            curr = {"speaker_id": spk, "start": start, "end": end, "text": txt}
        else:
            if spk == curr["speaker_id"]:
                # continue same turn
                curr["end"] = end
                curr["text"] += (" " + txt)
            else:
                # flush previous turn
                turns.append(curr)
                curr = {"speaker_id": spk, "start": start, "end": end, "text": txt}

        duration = max(duration, end)

    if curr is not None:
        turns.append(curr)

    return {"turns": turns, "speakers": speakers_order, "duration": duration}


def _render_transcript(turns: List[Dict[str, Any]], label_map: Dict[str, str]) -> str:
    lines: List[str] = []
    for t in turns:
        spk = label_map.get(t["speaker_id"], t["speaker_id"])
        start_s = _format_hhmmss(float(t["start"]))
        end_s = _format_hhmmss(float(t["end"]))
        text = t["text"].strip()
        lines.append(f"[{start_s} - {end_s}] {spk}: {text}")
    return "\n".join(lines)


async def transcribe_with_elevenlabs(
    file_bytes: bytes,
    filename: str,
    content_type: Optional[str],
    model_id: str = "scribe_v1",
    diarize: bool = True,
    timestamps_granularity: str = "word",
    tag_audio_events: bool = True,
    num_speakers: Optional[int] = None,
    language_code: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calls ElevenLabs Speech-to-Text Convert API.
    Docs: https://elevenlabs.io/docs/api-reference/speech-to-text/convert
    """
    xi_api_key = os.getenv("ELEVENLABS_API_KEY")
    if not xi_api_key:
        raise HTTPException(
            status_code=500,
            detail="ElevenLabs API key not configured. Please set ELEVENLABS_API_KEY in environment.",
        )

    url = "https://api.elevenlabs.io/v1/speech-to-text"
    headers = {
        "xi-api-key": xi_api_key,
        # Content-Type is set by httpx when using files= and data=
    }

    data = {
        "model_id": model_id,
        "diarize": "true" if diarize else "false",
        "timestamps_granularity": timestamps_granularity,  # 'word' | 'character' | 'none'
        "tag_audio_events": "true" if tag_audio_events else "false",
    }
    if num_speakers is not None:
        data["num_speakers"] = str(num_speakers)
    if language_code:
        data["language_code"] = language_code

    mime = content_type or "application/octet-stream"
    files = {"file": (filename or "audio_file", file_bytes, mime)}

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, headers=headers, data=data, files=files)

    if resp.status_code != 200:
        logger.error("ElevenLabs STT error %s: %s", resp.status_code, resp.text)
        raise HTTPException(
            status_code=502,
            detail=f"ElevenLabs STT failed ({resp.status_code}): {resp.text}",
        )

    try:
        return resp.json()
    except Exception as e:
        logger.exception("Failed to parse ElevenLabs STT JSON: %s", e)
        raise HTTPException(status_code=502, detail="Invalid JSON from ElevenLabs STT")


@app.post("/analyze/")
async def analyze_audio(files: List[UploadFile] = File(...)):
    logger.info(f"Received {len(files)} files for analysis")

    # Check if API keys are set
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("OpenAI API key not configured")
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key not configured. Please set OPENAI_API_KEY environment variable.",
        )
    if not os.getenv("ELEVENLABS_API_KEY"):
        logger.error("ElevenLabs API key not configured")
        raise HTTPException(
            status_code=500,
            detail="ElevenLabs API key not configured. Please set ELEVENLABS_API_KEY environment variable.",
        )

    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    results = []
    client = OpenAI(api_key=openai_api_key)

    # Enriched analysis schema template (as instruction for the model)
    schema_template = """
Return ONLY a JSON object with this exact structure and keys (no markdown, no extra text). If a field is not applicable, use an empty string for strings, [] for arrays, and null where allowed:

{
  "emotion_overall": "very_negative | negative | neutral | positive | very_positive",
  "emotion_confidence": 0.0,
  "satisfaction": "very_unsatisfied | unsatisfied | neutral | satisfied | very_satisfied",
  "satisfaction_confidence": 0.0,
  "summary": "2-4 concise sentences summarizing the conversation",
  "customer_intent": "primary customer intent in one sentence",
  "issues": ["list of key issues raised by the customer"],
  "action_items": [
    {
      "owner": "agent | customer | other",
      "item": "what needs to be done",
      "due": "YYYY-MM-DD or null"
    }
  ],
  "agent_speaker_label": "Speaker 1 | Speaker 2 | Speaker 3 | unknown",
  "agent_identification_confidence": 0.0,
  "agent_improvement_opportunities": [
    {
      "category": "empathy | discovery | clarity | solution_quality | ownership | pace | listening | policy_adherence | product_knowledge",
      "observation": "what the agent did/said",
      "evidence": "short direct quote",
      "recommended_change": "what to do better next time",
      "impact": "low | medium | high"
    }
  ],
  "post_call_recommendations": [
    "specific next steps the agent should take after the call (e.g., send recap email with X, create ticket Y, schedule follow-up by DATE, update CRM with Z, proactive checks)"
  ],
  "follow_up_message_draft": "1 short paragraph the agent can send as a follow-up now",
  "sentiment_analysis": "2-4 sentences of critical-thinking analysis on the transcription, citing brief evidence/quotes where useful"
}
"""

    for i, file in enumerate(files):
        try:
            logger.info(f"Processing file {i+1}: {file.filename}")

            # Validate file
            if not file.filename:
                logger.warning(f"File {i+1} has no filename, skipping")
                continue

            # Read file content
            content = await file.read()
            logger.info(f"File {file.filename} size: {len(content)} bytes")

            # 1) Transcribe with ElevenLabs STT + diarization
            stt = await transcribe_with_elevenlabs(
                file_bytes=content,
                filename=file.filename,
                content_type=file.content_type,
                model_id="scribe_v1",
                diarize=True,
                timestamps_granularity="word",
                tag_audio_events=True,
                num_speakers=None,  # let model infer
                language_code=None,  # auto-detect
            )

            # Extract text and words
            transcript_text = stt.get("text", "").strip()
            words = stt.get("words", []) or []
            grouping = _group_into_turns(words)
            turns = grouping["turns"]
            speakers = grouping["speakers"]
            duration = grouping["duration"]

            # Build human-readable speaker labels
            label_map: Dict[str, str] = {}
            for idx, spk in enumerate(speakers, start=1):
                label_map[spk] = f"Speaker {idx}"

            transcript_block = _render_transcript(turns, label_map)
            duration_str = _format_hhmmss(duration)

            # 2) Enriched prompt for sentiment/summary/compliance analysis
            system_msg = (
                "You are an expert conversation analyst for customer support calls. "
                "Return responses STRICTLY as a single JSON object following the provided schema. "
                "Do not include any additional commentary or markdown."
            )

            user_prompt = (
                "Analyze the following diarized transcript from a call.\n\n"
                f"Filename: {file.filename}\n"
                f"Duration: {duration_str}\n\n"
                "Transcript (with timestamps and speakers):\n"
                f"{transcript_block}\n\n"
                "Perform the analysis with the following goals:\n"
                "- Detect overall sentiment/emotion and confidence.\n"
                "- Assess customer satisfaction and confidence.\n"
                "- Provide a concise call summary.\n"
                "- Identify customer intent and key issues.\n"
                "- Extract concrete action items with owner and due date if present.\n"
                "- THINK about which speaker is the agent; set 'agent_speaker_label' to the best guess and a confidence score.\n"
                "- Provide 'agent_improvement_opportunities' that focus on what the agent could do better next time, with evidence quotes and impact.\n"
                "- Provide 'post_call_recommendations' that specify what the agent should do after the call from this point on (follow-up, ticketing, documentation, proactive checks), and include a short 'follow_up_message_draft'.\n"
                "- Provide a 'sentiment_analysis' section with critical-thinking insight on the transcription.\n\n"
                "Output must STRICTLY match the JSON schema below. Do not include any text outside the JSON object.\n\n"
                + schema_template.strip()
            )

            logger.info("Sending request to OpenAI for analysis")
            # Use OpenAI Responses API with GPT-5
            response = client.responses.create(
                model="gpt-5",
                input=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_prompt},
                ],
                reasoning={"effort": "low"},
                text={"verbosity": "low"},
            )

            # Extract and parse response (prefer output_text helper, with safe fallback)
            sentiment_response = getattr(response, "output_text", None)
            if not sentiment_response:
                try:
                    parts = []
                    output = getattr(response, "output", None)
                    if output:
                        for item in output:
                            content = getattr(item, "content", None)
                            if content:
                                for c in content:
                                    txt = getattr(c, "text", None)
                                    if txt:
                                        parts.append(txt)
                    sentiment_response = "\n".join(parts) if parts else None
                except Exception:
                    sentiment_response = None

            if not sentiment_response:
                raise HTTPException(status_code=502, detail="Empty response from OpenAI")

            logger.info(f"OpenAI response received, length={len(sentiment_response or '')}")

            sentiment_data = _safe_parse_json(sentiment_response)

            # Enforce schema adjustments for output
            if isinstance(sentiment_data, dict):
                sentiment_data.pop("per_turn", None)
                # Remove deprecated fields if present
                for k in ("compliance_flags", "escalation_risk", "escalation_reason"):
                    sentiment_data.pop(k, None)
                sentiment_data.setdefault(
                    "sentiment_analysis",
                    "Critical-thinking analysis on the transcription covering tone, intent, evidence, and context."
                )

            # Add metadata
            now = datetime.datetime.now()
            result = {
                "filename": file.filename,
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "audio_length": duration_str,
                "file_size": len(content),
                "transcription": transcript_text,
                "analysis": sentiment_data,
            }

            results.append(result)
            logger.info(f"Successfully processed file: {file.filename}")

        except HTTPException as he:
            logger.error(f"HTTP error processing file {file.filename}: {he.detail}")
            results.append(
                {
                    "filename": file.filename,
                    "error": he.detail if isinstance(he.detail, str) else str(he.detail),
                    "date": datetime.datetime.now().strftime("%Y-%m-%d"),
                    "time": datetime.datetime.now().strftime("%H:%M:%S"),
                }
            )
        except Exception as e:
            logger.exception(f"Error processing file {file.filename}: {str(e)}")
            results.append(
                {
                    "filename": file.filename,
                    "error": str(e),
                    "date": datetime.datetime.now().strftime("%Y-%m-%d"),
                    "time": datetime.datetime.now().strftime("%H:%M:%S"),
                }
            )

    if not results:
        raise HTTPException(status_code=400, detail="No files could be processed")

    logger.info(f"Returning {len(results)} results")
    return {"results": results, "total_processed": len(results)}


@app.get("/")
async def root():
    return {"message": "Voice Sentiment Analysis API is running"}


@app.get("/health")
async def health_check():
    api_key_configured = bool(os.getenv("OPENAI_API_KEY"))
    eleven_configured = bool(os.getenv("ELEVENLABS_API_KEY"))
    return {
        "status": "healthy",
        "openai_configured": api_key_configured,
        "elevenlabs_configured": eleven_configured,
    }


if __name__ == "__main__":
    # Ensure the app can be run directly for local testing
    uvicorn.run(app, host="0.0.0.0", port=8000)
