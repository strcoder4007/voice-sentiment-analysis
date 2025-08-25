import React from "react";
import JsonViewer from "./JsonViewer";

function humanFileSize(bytes) {
  if (!bytes && bytes !== 0) return "-";
  const thresh = 1024;
  if (Math.abs(bytes) < thresh) return bytes + " B";
  const units = ["KB", "MB", "GB", "TB"];
  let u = -1;
  do {
    bytes /= thresh;
    ++u;
  } while (Math.abs(bytes) >= thresh && u < units.length - 1);
  return bytes.toFixed(1) + " " + units[u];
}

function pct(n) {
  if (typeof n !== "number" || Number.isNaN(n)) return "-";
  return Math.round(n * 100) + "%";
}

function variantForSentiment(v) {
  switch (String(v || "").toLowerCase()) {
    case "very_negative":
      return "danger";
    case "negative":
      return "warning";
    case "neutral":
      return "neutral";
    case "positive":
    case "very_positive":
      return "success";
    default:
      return "neutral";
  }
}

function variantForSatisfaction(v) {
  const s = String(v || "").toLowerCase();
  if (s.includes("very_unsatisfied")) return "danger";
  if (s.includes("unsatisfied")) return "warning";
  if (s.includes("neutral")) return "neutral";
  if (s.includes("satisfied")) return "success";
  return "neutral";
}

const Section = ({ title, children, right, large = false }) => (
  <section className="section">
    <div className="section-head">
      <h4 className={`section-title-strong ${large ? "lg" : ""}`}>{title}</h4>
      {right ? <div className="section-right">{right}</div> : null}
    </div>
    {children}
  </section>
);

const ResultCard = ({ result, index }) => {
  const a = result?.analysis || {};
  const issues = Array.isArray(a.issues) ? a.issues : [];
  const actionItems = Array.isArray(a.action_items) ? a.action_items : [];
  const opps = Array.isArray(a.agent_improvement_opportunities)
    ? a.agent_improvement_opportunities
    : [];
  const recs = Array.isArray(a.post_call_recommendations)
    ? a.post_call_recommendations
    : [];

  const sentimentVariant = variantForSentiment(a.emotion_overall);
  const satisfactionVariant = variantForSatisfaction(a.satisfaction);

  return (
    <div className="result-card modern-card">
      <div className="card-header">
        <div className="title-block">
          <div className="filename">{result.filename || "Analysis"}</div>
          <div className="subtle">
            {result.date} • {result.time}
          </div>
        </div>

        <div className="meta">
          <div className="meta-item">
            <span>Duration</span>
            <strong>{result.audio_length || "-"}</strong>
          </div>
          <div className="meta-item">
            <span>Size</span>
            <strong>{humanFileSize(result.file_size)}</strong>
          </div>
        </div>
      </div>

      {result.error ? (
        <div className="alert error">{String(result.error)}</div>
      ) : (
        <div className="content">
          <div className="chips-row">
            <span className={`badge ${"badge-" + sentimentVariant}`}>
              Sentiment: {a.emotion_overall || "-"}
            </span>
            <span className="chip chip-ghost">
              Conf: {pct(a.emotion_confidence)}
            </span>
            <span className={`badge ${"badge-" + satisfactionVariant}`}>
              Satisfaction: {a.satisfaction || "-"}
            </span>
            <span className="chip chip-ghost">
              Conf: {pct(a.satisfaction_confidence)}
            </span>
          </div>

          <Section title="Summary" large>
            <p className="para">{a.summary || "—"}</p>
            <div className="subtle mt-8">
              Intent: <strong>{a.customer_intent || "—"}</strong>
            </div>
          </Section>

          {issues.length > 0 && (
            <Section title="Key Issues" large>
              <div className="chips-row wrap">
                {issues.map((it, i) => (
                  <span key={i} className="chip">{it}</span>
                ))}
              </div>
            </Section>
          )}

          {actionItems.length > 0 && (
            <Section title="Action Items" large>
              <div className="table">
                <div className="table-row table-header">
                  <div>Owner</div>
                  <div>Item</div>
                  <div>Due</div>
                </div>
                {actionItems.map((ai, i) => (
                  <div key={i} className="table-row">
                    <div>
                      <span className="chip chip-ghost">{ai.owner || "—"}</span>
                    </div>
                    <div>{ai.item || "—"}</div>
                    <div>{ai.due || "—"}</div>
                  </div>
                ))}
              </div>
            </Section>
          )}

          <Section
            title="Agent Identification"
            large
            right={
              a.agent_speaker_label ? (
                <span className="chip chip-ghost">
                  {a.agent_speaker_label} • Conf {pct(a.agent_identification_confidence)}
                </span>
              ) : null
            }
          >
            <div className="subtle">
              Sentiment analysis:&nbsp;
              <span>{a.sentiment_analysis || "—"}</span>
            </div>
          </Section>

          {opps.length > 0 && (
            <Section title="Improvement Opportunities">
              <div className="stack">
                {opps.map((op, i) => (
                  <div key={i} className="panel">
                    <div className="panel-head">
                      <span className="chip chip-ghost">{op.category || "—"}</span>
                      {op.impact ? (
                        <span
                          className={`badge ${
                            "badge-" +
                            (String(op.impact).toLowerCase() === "high"
                              ? "danger"
                              : String(op.impact).toLowerCase() === "medium"
                              ? "warning"
                              : "neutral")
                          }`}
                        >
                          Impact: {op.impact}
                        </span>
                      ) : null}
                    </div>
                    {op.observation ? (
                      <p className="para mb-6">Observation: {op.observation}</p>
                    ) : null}
                    {op.evidence ? (
                      <blockquote className="quote">“{op.evidence}”</blockquote>
                    ) : null}
                    {op.recommended_change ? (
                      <p className="para mt-8">
                        Recommendation: {op.recommended_change}
                      </p>
                    ) : null}
                  </div>
                ))}
              </div>
            </Section>
          )}

          {recs.length > 0 && (
            <Section title="Post-Call Recommendations">
              <ul className="list">
                {recs.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </Section>
          )}

          {a.follow_up_message_draft ? (
            <Section title="Follow-up Message Draft">
              <div className="note">{a.follow_up_message_draft}</div>
            </Section>
          ) : null}

          <details className="disclosure">
            <summary>Transcript</summary>
            <pre className="transcript">
{(result.transcription || "—")}
            </pre>
          </details>

          <div className="divider" />

          <details className="disclosure" open={false}>
            <summary>Raw JSON</summary>
            <JsonViewer data={result} />
          </details>
        </div>
      )}
    </div>
  );
};

export default ResultCard;
