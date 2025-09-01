import React from "react";

/**
 * Lightweight JSON syntax highlighter with safe HTML escaping.
 * Renders pretty-printed JSON inside <pre><code> with span classes.
 */
function escapeHtml(str) {
  // Use entity strings (written here as &amp; etc.) so that the saved file contains
  // literal &, <, > for proper HTML escaping at runtime.
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function syntaxHighlight(json) {
  if (typeof json !== "string") {
    try {
      json = JSON.stringify(json, null, 2);
    } catch {
      json = String(json);
    }
  }
  json = escapeHtml(json);

  // Strings, keys, numbers, booleans, null
  return json.replace(
    /("(\\u[\da-fA-F]{4}|\\[^u]|[^\\"])*"(?:\s*:)?|\b(?:true|false|null)\b|-?\d+(?:\.\d+)?(?:[eE][+\-]?\d+)?)/g,
    (match) => {
      let cls = "json-number";
      if (match.startsWith('"')) {
        cls = match.endsWith(":") ? "json-key" : "json-string";
      } else if (/true|false/.test(match)) {
        cls = "json-boolean";
      } else if (/null/.test(match)) {
        cls = "json-null";
      }
      return `<span class="${cls}">${match}</span>`;
    }
  );
}

const JsonViewer = ({ data, className = "" }) => {
  const html = syntaxHighlight(data);
  return (
    <pre className={`json-viewer ${className}`}>
      <code dangerouslySetInnerHTML={{ __html: html }} />
    </pre>
  );
};

export default JsonViewer;
