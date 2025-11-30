import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { signup } from "../api";
import { useAuth } from "../AuthContext";
import "../styles/pages/signup.css";
import "../styles/components/forms.css";
import "../styles/components/buttons.css";

export default function SignupPage() {
  const navigate = useNavigate();
  const { setAuth } = useAuth();
  const [form, setForm] = useState({ name: "", email: "", password: "", roles: ["end_user"] });
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const auth = await signup(form);
      setAuth(auth);
      navigate("/search");
    } catch (err: any) {
      let msg = "Signup failed."
      try {
        const parsed = JSON.parse(err?.message)?.detail[0];
        console.log(parsed);
        msg = parsed.msg || msg;
      } catch {
        // If parse fails, fall back to this.
        msg = err?.message || msg;
      }
      console.log(msg);
      setError(msg);
    }
  };

  return (
    <div className="page card">
      <h2>Signup</h2>
      <form className="form" onSubmit={onSubmit}>
        <label>Name</label>
        <input 
          value={form.name} 
          onChange={(e) => setForm({ ...form, name: e.target.value })} 
          required 
        />

        <label>Email</label>
        <input 
          type="email" 
          value={form.email} 
          onChange={(e) => setForm({ ...form, email: e.target.value })} 
          required 
        />

        <label>Password</label>
        <input 
          type="password" 
          value={form.password} 
          onChange={(e) => setForm({ ...form, password: e.target.value })} 
          required 
        />

        <button className="btn-primary" type="submit">
          Create Account
        </button>
        {error && <p className="error">{error}</p>}
      </form>
      <p>
        Already have an account? <Link to="/login">Login</Link>
      </p>
    </div>
  );
}
