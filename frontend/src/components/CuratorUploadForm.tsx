import { FormEvent, useState } from "react";

// Handles upload form UI, metadata mode toggling, and building FormData for parent.
export type MetadataMode = "csv" | "manual";

export type ManualMetaData = {
  pmid: string;
  title: string;
  authors: string;
  doi: string;
  journal_name: string;
  publication_year: string;
  create_date: string;
  citation: string;
  first_author: string;
  pmcid: string;
  nihmsid: string;
};

type Props = {
  onUpload: (form: FormData) => Promise<void>;
  loading: boolean;
  message: string | null;
};

export default function CuratorUploadForm({ onUpload, loading, message }: Props) {
  const [documentFile, setDocumentFile] = useState<File | null>(null);
  const [metadataFile, setMetadataFile] = useState<File | null>(null);
  const [metadataMode, setMetadataMode] = useState<MetadataMode>("csv");
  const [ManualMetaData, setManualMetaData] = useState<ManualMetaData>({
    pmid: "",
    title: "",
    authors: "",
    doi: "",
    journal_name: "",
    publication_year: "",
    create_date: "",
    citation: "",
    first_author: "",
    pmcid: "",
    nihmsid: "",
  });

  const resetForm = () => {
    setDocumentFile(null);
    setMetadataFile(null);
    setManualMetaData({
      pmid: "",
      title: "",
      authors: "",
      doi: "",
      journal_name: "",
      publication_year: "",
      create_date: "",
      citation: "",
      first_author: "",
      pmcid: "",
      nihmsid: "",
    });
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!documentFile) {
      alert("Please choose a document");
      return;
    }
    if (metadataMode === "manual" && (!ManualMetaData.pmid || !ManualMetaData.title)) {
      alert("PMID and Title are required when entering metadata manually.");
      return;
    }

    const form = new FormData();
    form.append("document", documentFile);

    if (metadataMode === "csv") {
      if (metadataFile) form.append("metadata_csv", metadataFile);
    } else {
      // Turns the object into an array of [key, value] pairs.
      Object.entries(ManualMetaData).forEach(([key, value]) => {
        if (value) form.append(key, value);
      });
    }

    await onUpload(form);
    resetForm();
  };

  return (
    <form className="form" onSubmit={onSubmit}>
      <label>Document (PDF/TXT)</label>
      <input type="file" accept=".pdf,.txt" onChange={(e) => setDocumentFile(e.target.files?.[0] || null)} required />

      <div className="metadata-mode">
        <label className="checkbox-inline">
          <input
            type="radio"
            name="metadata-mode"
            value="csv"
            checked={metadataMode === "csv"}
            onChange={() => setMetadataMode("csv")}
          />
          Use metadata CSV
        </label>
        <label className="checkbox-inline">
          <input
            type="radio"
            name="metadata-mode"
            value="manual"
            checked={metadataMode === "manual"}
            onChange={() => setMetadataMode("manual")}
          />
          Enter metadata manually
        </label>
      </div>

      {metadataMode === "csv" ? (
        <>
          <label>Metadata CSV</label>
          <input type="file" accept=".csv" onChange={(e) => setMetadataFile(e.target.files?.[0] || null)} />
        </>
      ) : (
        <>
          <label>PMID *</label>
          <input value={ManualMetaData.pmid} onChange={(e) => setManualMetaData({ ...ManualMetaData, pmid: e.target.value })} required />

          <label>Title *</label>
          <input value={ManualMetaData.title} onChange={(e) => setManualMetaData({ ...ManualMetaData, title: e.target.value })} required />

          <label>Authors</label>
          <input value={ManualMetaData.authors} onChange={(e) => setManualMetaData({ ...ManualMetaData, authors: e.target.value })} />

          <label>DOI</label>
          <input value={ManualMetaData.doi} onChange={(e) => setManualMetaData({ ...ManualMetaData, doi: e.target.value })} />

          <label>Journal Name</label>
          <input
            value={ManualMetaData.journal_name}
            onChange={(e) => setManualMetaData({ ...ManualMetaData, journal_name: e.target.value })}
          />

          <label>Publication Year</label>
          <input
            value={ManualMetaData.publication_year}
            onChange={(e) => setManualMetaData({ ...ManualMetaData, publication_year: e.target.value })}
          />

          <label>Create Date</label>
          <input value={ManualMetaData.create_date} onChange={(e) => setManualMetaData({ ...ManualMetaData, create_date: e.target.value })} />

          <label>Citation</label>
          <input value={ManualMetaData.citation} onChange={(e) => setManualMetaData({ ...ManualMetaData, citation: e.target.value })} />
          
          <label>First Author</label>
          <input
            value={ManualMetaData.first_author}
            onChange={(e) => setManualMetaData({ ...ManualMetaData, first_author: e.target.value })}
          />
          
          <label>PMCID</label>
          <input value={ManualMetaData.pmcid} onChange={(e) => setManualMetaData({ ...ManualMetaData, pmcid: e.target.value })} />
          
          <label>NIHMSID</label>
          <input value={ManualMetaData.nihmsid} onChange={(e) => setManualMetaData({ ...ManualMetaData, nihmsid: e.target.value })} />
        </>
      )}

      <button className="btn-primary" type="submit" disabled={loading}>
        {loading ? "Uploading..." : "Upload"}
      </button>
      {message && <p className={message.toLowerCase().includes("fail") ? "error" : "muted"}>{message}</p>}
    </form>
  );
}
