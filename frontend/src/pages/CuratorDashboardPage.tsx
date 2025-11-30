import { useEffect, useState } from "react";
import { deleteDocument, listDocuments, uploadDocument } from "../api";
import { DocumentSummary } from "../types";
import CuratorUploadForm from "../components/CuratorUploadForm";
import DocumentsTable from "../components/DocumentsTable";
import "../styles/pages/curatorDashboard.css";
import "../styles/components/forms.css";
import "../styles/components/buttons.css";
import "../styles/components/tables.css";

// Container: loads docs, handles upload/delete, and passes state to child components.
export default function CuratorDashboardPage() {
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const loadDocs = async () => {
    try {
      setDocs(await listDocuments());
    } catch (err: any) {
      setMessage(err?.message || "Failed to load documents");
    }
  };

  useEffect(() => {
    loadDocs();
  }, []);

  const handleUpload = async (form: FormData) => {
    setLoading(true);
    setMessage(null);
    try {
      await uploadDocument(form);
      await loadDocs();
      setMessage("Upload complete");
    } catch (err: any) {
      setMessage(err?.message || "Upload failed");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (docId: number) => {
    if (!confirm("Delete this document?")) return;
    try {
      await deleteDocument(docId);
      await loadDocs();
    } catch (err: any) {
      alert(err?.message || "Delete failed");
    }
  };

  return (
    <div className="page">

      <h2>Curator Dashboard</h2>
      <CuratorUploadForm onUpload={handleUpload} loading={loading} message={message} />
      
      <h3>Documents</h3>
      <DocumentsTable docs={docs} onDelete={handleDelete} />
    </div>
  );
}
