import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";

// Suggestions only - users can still type their own department.
const DEPARTMENTS = [
  "Computer Science",
  "Electronics",
  "Mechanical",
  "Civil",
  "Biotechnology",
  "Management",
];

export default function Register() {
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "student", department: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  // one handler for every field: uses the input's name attribute
  function update(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await register({ ...form, department: form.department || null });
      navigate("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card auth-card" onSubmit={handleSubmit}>
      <h1>Create account</h1>
      {error && <p className="error">{error}</p>}

      <label>
        Full name
        <input name="name" value={form.name} onChange={update} required autoFocus />
      </label>

      <label>
        Email
        <input name="email" type="email" value={form.email} onChange={update} required />
      </label>

      <label>
        Password <span className="muted">(at least 6 characters)</span>
        <input name="password" type="password" value={form.password} onChange={update} minLength={6} required />
      </label>

      <label>
        Role
        <select name="role" value={form.role} onChange={update}>
          <option value="student">Student</option>
          <option value="faculty">Faculty</option>
          <option value="researcher">Researcher</option>
        </select>
      </label>

      <label>
        Department
        <input name="department" list="departments" value={form.department} onChange={update} />
        <datalist id="departments">
          {DEPARTMENTS.map((d) => <option key={d} value={d} />)}
        </datalist>
      </label>

      <button type="submit" disabled={busy}>{busy ? "Creating…" : "Create account"}</button>
      <p className="muted">Already have an account? <Link to="/login">Log in</Link></p>
    </form>
  );
}
