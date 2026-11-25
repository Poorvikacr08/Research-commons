import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [q, setQ] = useState("");

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <header className="navbar">
      <Link to="/" className="brand-lockup" aria-label="Chanakya ScholarSphere home">
        <span className="brand-mark" aria-hidden="true"><span>CS</span></span>
        <span className="brand-copy"><strong>Chanakya</strong><span>ScholarSphere</span></span>
      </Link>
      {user && (
        <form className="nav-search" onSubmit={(e) => { e.preventDefault(); if (q.trim()) navigate(`/search?q=${encodeURIComponent(q.trim())}`); }}>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search topics, papers, people…" />
        </form>
      )}
      <nav>
        {user ? (
          <>
            <NavLink to="/" end>Home</NavLink>
            <NavLink to="/library">Library</NavLink>
            <NavLink to="/people">People</NavLink>
            <NavLink to="/ask">Ask</NavLink>
            {user.role === "admin" && <NavLink to="/admin">Admin</NavLink>}
            <NavLink to={`/users/${user.id}`}>{user.name}</NavLink>
            <button className="link-button" onClick={handleLogout}>Log out</button>
          </>
        ) : (
          <>
            <NavLink to="/login">Log in</NavLink>
            <NavLink to="/register">Register</NavLink>
          </>
        )}
      </nav>
    </header>
  );
}
