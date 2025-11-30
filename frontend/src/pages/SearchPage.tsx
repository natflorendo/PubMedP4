import { FormEvent, useState } from "react";
import { runQuery } from "../api";
import { QueryResponse } from "../types";
import "../styles/pages/search.css";
import "../styles/components/forms.css";
import "../styles/components/buttons.css";
import "../styles/components/tables.css";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [k, setK] = useState(5);
  const [includeAnswer, setIncludeAnswer] = useState(true);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const resp = await runQuery({ query, k, include_answer: includeAnswer });
      setResult(resp);
    } catch (err: any) {
      setError(err?.message || "Query failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <h2>Search</h2>
      <form className="form" onSubmit={onSubmit}>
        <label>Question</label>
        <textarea value={query} onChange={(e) => setQuery(e.target.value)} required />

        <label>Top K</label>
        <input type="number" min={1} max={20} value={k} onChange={(e) => setK(parseInt(e.target.value) || 1)} />
        
        <label className="checkbox-inline">
          <input type="checkbox" checked={includeAnswer} onChange={(e) => setIncludeAnswer(e.target.checked)} />
          Include answer
        </label>
        <button className="btn-primary" type="submit" disabled={loading}>
          {loading ? "Searching..." : "Search"}
        </button>
      </form>
      {error && <p className="error">{error}</p>}
      
      {result && (
        <div className="results">
          <h3>Answer</h3>
          <p>{result.answer ?? "No answer (LLM disabled or unavailable)"}</p>

          <h3>Citations</h3>
          <ul>
            {result.citations.map((c) => (
              <li key={c.pmid}>
                PMID {c.pmid} — {c.title} {c.doc_id ? `(doc_id ${c.doc_id})` : ""}
              </li>
            ))}
          </ul>

          <h3>Retrieved Chunks</h3>
          <table className="table">
            <thead>
              <tr>
                <th>PMID</th>
                <th>Score</th>
                <th>Title</th>
                <th>Text</th>
              </tr>
            </thead>
            <tbody>
              {result.retrieved_chunks.map((ch) => (
                <tr key={ch.chunk_id}>
                  <td>{ch.pmid}</td>
                  <td>{ch.score.toFixed(4)}</td>
                  <td>{ch.title}</td>
                  <td className="chunk-text">{ch.chunk_text}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
