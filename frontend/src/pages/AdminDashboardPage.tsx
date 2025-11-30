import { useEffect, useState } from "react";
import { listUsers, updateUser } from "../api";
import { User } from "../types";
import "../styles/pages/adminDashboard.css";
import "../styles/components/tables.css";
import "../styles/components/buttons.css";

export default function AdminDashboardPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Editable fields - Values can only be name or email.
  const [editFields, setEditFields] = useState<Record<number, { name: string; email: string }>>({});
  // Per-row save status for the Save button
  type RowStatus = "idle" | "saving" | "saved" | "error";
  const [rowStatus, setRowStatus] = useState<Record<number, RowStatus>>({});


  // Load all users
  useEffect(() => {
    load();
  }, []);

  async function load() {
    try {
      const fetched = await listUsers();
      setUsers(fetched);

      const initialInfo: Record<number, { name: string; email: string }> = {};

      fetched.forEach((u) => {
        initialInfo[u.user_id] = { name: u.name, email: u.email };
      });
      setEditFields(initialInfo);
    } catch (err: any) {
      setError(err?.message || "Failed to load users");
    } finally {
      setLoading(false);
    }
  }


  // Toggle a single role (admin/curator/end_user) for a user and persist to the backend 
  // (don't need to press Save button).
  const handleRoleToggle = async (user: User, role: string) => {
    const roles = new Set((user.roles || []).map((r) => r.toLowerCase()));
    if (roles.has(role)) roles.delete(role);
    else roles.add(role);
    const newRoles = Array.from(roles);
    try {
      const updated = await updateUser(user.user_id, { roles: newRoles });
      setUsers((prev) => prev.map((u) => (u.user_id === user.user_id ? updated : u)));
    } catch (err: any) {
      alert(err?.message || "Update failed");
    }
  };

  // Save name/email edits for a user and show a temporary "Saved" state on the button
  const handleSave = async (user: User) => {
    const fields = editFields[user.user_id];
    if (!fields) return;
    setRowStatus((prev) => ({ ...prev, [user.user_id]: "saving" }));
    try {
      const updated = await updateUser(user.user_id, {
        name: fields.name,
        email: fields.email,
        roles: user.roles,
      });
      
      setUsers((prev) => prev.map((u) => (u.user_id === user.user_id ? updated : u)));
      setRowStatus((prev) => ({ ...prev, [user.user_id]: "saved" }));

      setTimeout(() => {
        setRowStatus((prev) => ({ ...prev, [user.user_id]: "idle" }));
      }, 2000);
    } catch (err: any) {
      alert(err?.message || "Update failed");
      setRowStatus((prev) => ({ ...prev, [user.user_id]: "error" }));
    }
  };


  // Update local editFields when the name/email inputs change for a given user
  const onFieldChange = (userId: number, key: "name" | "email", value: string) => {
    setEditFields((prev) => ({
      ...prev,
      [userId]: {
        ...(prev[userId] || { name: "", email: "" }),
        [key]: value,
      },
    }));
  };

  if (loading) return <p className="muted">Loading users...</p>;
  if (error) return <p className="error">{error}</p>;

  return (
    <div className="page">
      <h2>Admin Dashboard</h2>
      <table className="table">
        <thead>
          <tr>
            <th>Name</th><th>Email</th><th>Roles</th><th>Actions</th>
          </tr>
        </thead>
        
        <tbody>
          {users.map((u) => {
            const roles = new Set((u.roles || []).map((r) => r.toLowerCase()));
            const fields = editFields[u.user_id] || { name: u.name, email: u.email };
            const status = rowStatus[u.user_id] || "idle";
            const updatedInfo = fields.name !== u.name || fields.email !== u.email;
            return (
              <tr key={u.user_id}>
                <td>
                  <input
                    value={fields.name}
                    onChange={(e) => onFieldChange(u.user_id, "name", e.target.value)}
                  />
                </td>
                <td>
                  <input
                    value={fields.email}
                    onChange={(e) => onFieldChange(u.user_id, "email", e.target.value)}
                  />
                </td>
                <td>
                  {["admin", "curator", "end_user"].map((role) => (
                    <label key={role} className="role-toggle">
                      <input
                        type="checkbox"
                        checked={roles.has(role)}
                        onChange={() => handleRoleToggle(u, role)}
                      />
                      {role}
                    </label>
                  ))}
                </td>
                <td>
                  <button
                    className={
                      `btn-secondary` +
                      (status === "saved" ? " btn-secondary-saved" : "") +
                      (status === "error" ? " btn-secondary-error" : "")
                    }
                    onClick={() => handleSave(u)}
                    disabled={status === "saving" || !updatedInfo}
                  >
                    {status === "saving"
                      ? "Saving..."
                      : status === "saved"
                      ? "Saved"
                      : "Save"}
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
