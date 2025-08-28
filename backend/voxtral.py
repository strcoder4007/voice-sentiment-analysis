from transformers import VoxtralForConditionalGeneration, AutoProcessor
import torch
import os
from pathlib import Path
import sys

device = "cuda"
repo_id = "mistralai/Voxtral-Mini-3B-2507"

processor = AutoProcessor.from_pretrained(repo_id)
model = VoxtralForConditionalGeneration.from_pretrained(repo_id, torch_dtype=torch.bfloat16, device_map=device)

# Resolve audio path relative to this script (backend/). Place your audio under backend/audios/f0.mp3
# or update the path below as needed.
script_dir = Path(__file__).resolve().parent
audio_rel = Path("audios") / "f1.mp3"
audio_path = script_dir / audio_rel

if not audio_path.exists():
    sys.exit(
        f"Error loading audio: File not found: {audio_path}\n"
        "Put your audio file at this location or update the path in this script."
    )

# Schema template must be defined before the prompt since the prompt appends schema_template.
schema_template = """
Return ONLY a JSON object with this exact structure and keys (no markdown, no extra text). If a field is not applicable, use an empty string for strings, [] for arrays, and null where allowed. Keep lists concise (3-5 items max) and prefer brief quotes.

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

  "what_worked": [
    {
      "category": "rapport | empathy | discovery | value_proposition | objection_handling | clarity | pacing | personalization | next_steps",
      "observation": "what specifically helped",
      "evidence": "short direct quote",
      "impact": "low | medium | high"
    }
  ],

  "what_didnt_work": [
    {
      "category": "empathy | discovery | clarity | solution_quality | ownership | pace | listening | policy_adherence | product_knowledge | pricing | urgency",
      "observation": "what hindered progress",
      "evidence": "short direct quote",
      "recommended_fix": "what to change next time",
      "impact": "low | medium | high"
    }
  ],

  "win_back_strategy": {
    "root_cause": "root reason for dissatisfaction in one phrase",
    "messaging_pillars": ["3 short points that address the root cause"],
    "sample_response": "short paragraph the agent can say now to win the customer back",
    "do": ["tactics to use"],
    "avoid": ["pitfalls to avoid"]
  },

  "next_best_actions_ranked": [
    {
      "priority": 1,
      "action": "specific action",
      "owner": "agent | customer | other",
      "due": "YYYY-MM-DD or null",
      "rationale": "why this helps"
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

  "speaker_sentiment": [
    {
      "speaker_label": "Speaker 1 | Speaker 2 | Speaker 3 | unknown",
      "role": "agent | customer | other | unknown",
      "sentiment": "very_negative | negative | neutral | positive | very_positive",
      "confidence": 0.0
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
  "post_call_recommendations": [
    "specific next steps the agent should take after the call (e.g., send recap email with X, create ticket Y, schedule follow-up by DATE, update CRM with Z, proactive checks)"
  ],
  "follow_up_message_draft": "1 short paragraph the agent can send as a follow-up now",
  "sentiment_analysis": "2-4 sentences of critical-thinking analysis on the transcription, citing brief evidence/quotes where useful",

  "manager_coach_notes_top3": ["3 concise bullets a manager should coach on"],
  "agent_takeaways_top3": ["3 concise bullets the agent should remember next time"]
}
"""

user_prompt = (
    "Perform the analysis with the following goals:\n"
    "- Detect overall sentiment/emotion and confidence.\n"
    "- Assess customer satisfaction and confidence.\n"
    "- Provide a concise call summary.\n"
    "- Identify customer intent and key issues.\n"
    "- Extract concrete action items with owner and due date if present.\n"
    "- THINK about which speaker is the agent; set 'agent_speaker_label' to the best guess and a confidence score.\n"
    "- Provide 'agent_improvement_opportunities' that focus on what the agent could do better next time, with evidence quotes and impact.\n"
    "- Provide 'what_worked' and 'what_didnt_work' with specific evidence; focus on tactics, questions, and phrasing that helped or hurt outcomes.\n"
    "- Provide a 'coaching_plan' with SMART goals, micro_skills, practice exercises, and resources.\n"
    "- Provide a 'win_back_strategy' including messaging pillars and a 'sample_response' the agent can say now to win the customer back.\n"
    "- Identify 'objections' with severity and recommend improved responses.\n"
    "- Assess 'risk_of_churn' with drivers and mitigations.\n"
    "- Outline 'next_best_actions_ranked' with priorities, owners, due dates if present, and rationale.\n"
    "- Capture turning points with approximate timestamps in 'timeline' and outline 'topic_segments' with topic and sentiment.\n"
    "- Note any 'knowledge_gaps'.\n"
    "- Fill 'metrics' and question/filler/crosstalk stats if derivable from the transcript; otherwise use nulls.\n"
    "- Evaluate 'qualification.bant' with brief evidence; list 'decision_criteria'.\n"
    "- Summarize 'competitive_context' if competitors are mentioned.\n"
    "- Extract 'key_quotes' (pain, value, objection, decision) and 'entities'.\n"
    "- Score 'qa_scores' and 'readiness_scores' with brief rationale in notes.\n"
    "- Determine 'outcome.resolution_status' and if follow-up is required.\n"
    "- Suggest structured 'crm_updates_suggested'.\n"
    "- Provide 'post_call_recommendations' and a short 'follow_up_message_draft'.\n"
    "- Provide a 'sentiment_analysis' with critical thinking and quotes.\n"
    "- Keep lists concise (max 3-5 items) and avoid repetition.\n\n"
    "Output must STRICTLY match the JSON schema below. Do not include any text outside the JSON object. "
    "If information is not present, use empty string for strings, [] for arrays, and null where allowed.\n\n"
    + schema_template.strip()
)

conversation = [
    {
        "role": "user",
        "content": [
            {
                "type": "audio",
                "path": str(audio_path),
            },
            {"type": "text", "text": user_prompt},
        ],
    }
]

inputs = processor.apply_chat_template(conversation)
inputs = inputs.to(device, dtype=torch.bfloat16)

outputs = model.generate(**inputs, max_new_tokens=1536)
decoded_outputs = processor.batch_decode(outputs[:, inputs.input_ids.shape[1]:], skip_special_tokens=True)

print("\nGenerated response:")
print("=" * 80)
print(decoded_outputs[0])
print("=" * 80)
