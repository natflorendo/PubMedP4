import { DocumentSummary } from "../types";
import "../styles/components/tables.css";
import "../styles/components/buttons.css";

// Renders the documents list and delegates delete events to the parent.
type Props = {
  docs: DocumentSummary[];
  onDelete: (docId: number) => void;
};

export default function DocumentsTable({ docs, onDelete }: Props) {
  return (
    <table className="table">
      <thead>
        <tr>
          <th>Title</th>
          <th>PMID</th>
          <th>Chunks</th>
          <th>Embeddings</th>
          <th>Added</th>
          <th>Added By</th>
          <th></th>
        </tr>
      </thead>

      <tbody>
        {docs.map((d) => (
          <tr key={d.doc_id}>
            <td>{d.title}</td>
            <td>{d.pmid ?? "—"}</td>
            <td>{d.chunk_count}</td>
            <td>{d.embedding_count}</td>
            <td>{new Date(d.added_at).toLocaleString()}</td>
            <td>{d.curator_name ?? "-"}</td>
            <td>
              <button className="btn-secondary" onClick={() => onDelete(d.doc_id)}>
                Delete
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
