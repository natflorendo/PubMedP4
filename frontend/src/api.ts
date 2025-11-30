/**
 * app.ts 
 *  
 */ 

import { AuthResponse, User, UpdateUserPayload, DocumentSummary, QueryResponse } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";


// Returns common Authorization headers if a JWT token is present in localStorage.
function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  const token = localStorage.getItem("token");
  if (token) { headers.Authorization = `Bearer ${token}`; }
  return headers;
}


// Handles a fetch Response: throws an Error if !resp.ok OR parses JSON and returns it as type T.
async function handle<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    const msg = await resp.text();
    throw new Error(msg || resp.statusText);
  }
  return (await resp.json()) as T;
}


// Log in with username/password and return auth tokens and user info.
export async function login(username: string, password: string): Promise<AuthResponse> {
  const body = new URLSearchParams();
  body.append("username", username);
  body.append("password", password);
  const resp = await fetch(`${API_BASE}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });

  return handle<AuthResponse>(resp);
}


// Create a new user account.
export async function signup(payload: { name: string; email: string; password: string; roles?: string[] }) {
  const resp = await fetch(`${API_BASE}/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  return handle<AuthResponse>(resp);
}


// Fetch the currently authenticated user based on access token.
export async function me(): Promise<User> {
  const resp = await fetch(`${API_BASE}/me`, { 
    headers: authHeaders() 
  });

  return handle<User>(resp);
}


// List all users (admin only).
export async function listUsers(): Promise<User[]> {
  const resp = await fetch(`${API_BASE}/admin/users`, { 
    headers: authHeaders() 
  });

  return handle<User[]>(resp);
}


// Update a user by their ID (admin only).
export async function updateUser(userId: number, payload: UpdateUserPayload) {
  const resp = await fetch(`${API_BASE}/admin/users/${userId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload),
  });

  return handle<User>(resp);
}


// Delete a user by their ID (admin only).
export async function deleteUser(userId: number) {
  const resp = await fetch(`${API_BASE}/admin/users/${userId}`, {
    method: "DELETE",
    headers: authHeaders() ,
  });

  if (!resp.ok) throw new Error(await resp.text());
}


// Upload a new document (curator and admin).
export async function uploadDocument(form: FormData) {
  const resp = await fetch(`${API_BASE}/curator/upload`, {
    method: "POST",
    headers: authHeaders(),
    body: form,
  });

  return handle<any>(resp);
}


// List all documents (curator and admin).
export async function listDocuments(): Promise<DocumentSummary[]> {
  const resp = await fetch(`${API_BASE}/curator/documents`, {
    method: "GET",
    headers: authHeaders(),
  });

  return handle<DocumentSummary[]>(resp);
}


// Delete a document by ID (curator and admin).
// Backend api route makes it so that curators may only delete documents they originally uploaded, while admins can delete any document.
export async function deleteDocument(docId: number) {
  const resp = await fetch(`${API_BASE}/curator/documents/${docId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });

  if (!resp.ok) throw new Error(await resp.text());
}


// Run a query against the backend (RAG/search) and return the results and optional answer.
export async function runQuery(payload: { query: string; k: number; include_answer: boolean; answer_model?: string | null }) {
  const resp = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload),
  });

  return handle<QueryResponse>(resp);
}
