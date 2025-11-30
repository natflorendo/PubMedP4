import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";
import "../styles/components/navbar.css";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const roles = new Set((user?.roles || []).map((r) => r.toLowerCase()));

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <nav className="navbar glass">
      <div className="nav-left">
        {user && (
          <>
            <NavLink
              to="/search"
              className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
            >
              Search
            </NavLink>

            {(roles.has("curator") || roles.has("admin")) && (
              <NavLink
                to="/curator"
                className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
              >
                Curator
              </NavLink>
            )}

            {roles.has("admin") && (
              <NavLink
                to="/admin"
                className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
              >
                Admin
              </NavLink>
            )}
          </>
        )}
      </div>
      <div className="nav-right">
        {user ? (
          <>
            <span className="nav-user">{user.name}</span>
            <button className="btn-secondary" onClick={handleLogout}>
              Logout
            </button>
          </>
        ) : (
          <>
            <NavLink
              to="/login"
              className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
            >
              Login
            </NavLink>

            <NavLink
              to="/signup"
              className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
            >
              Signup
            </NavLink>
          </>
        )}
      </div>
    </nav>
  );
}
