/**
 * types.ts 
 *  
 * Backend data models
 */ 


// User record returned by the backend.
export type User = {
  user_id: number;
  name: string;
  email: string;
  roles: string[];
  created_at?: string;
};

// Payload used for updating a user.
export type UpdateUserPayload = {
  name?: string;
  email?: string;
  roles?: string[];
};


// Response returned from /login and /signup.
export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: User;
};


// Info about a document (used for curator).
export type DocumentSummary = {
  doc_id: number;
  title: string;
  type?: string | null;
  source_url?: string | null;
  processed: boolean;
  added_at: string;
  added_by?: number | null;
  curator_name?: string | null;
  pmid?: number | null;
  chunk_count: number;
  embedding_count: number;
};


// A citation that points a paper/doc (for QueryResponse).
export type Citation = {
  pmid: number;
  title: string;
  doc_id?: number | null;
};


// A single retrieved text chunk with metadata and relevance score.
export type ChunkResult = {
  chunk_id: number;
  pmid: number;
  doc_id?: number | null;
  title: string;
  score: number;
  chunk_text: string;
};


// Full response from a query (and optionally the answer and the supporting evidence).
export type QueryResponse = {
  query_id?: number | null;
  answer?: string | null;
  citations: Citation[];
  retrieved_chunks: ChunkResult[];
};