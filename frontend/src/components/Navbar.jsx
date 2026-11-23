import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <header className="navbar">
      <Link to="/" className="brand">Chanakya Research Commons</Link>
      <nav>
        {user ? (
          <>
            <NavLink to="/" end>Home</NavLink>
            <NavLink to="/people">People</NavLink>
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
