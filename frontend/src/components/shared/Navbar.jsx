import { useNavigate, useLocation } from "react-router-dom";
import useAppStore from "../../store/useAppStore";

export default function Navbar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { step, reset } = useAppStore();

  const links = [
    { path: "/",       label: "Yükle",  minStep: 1 },
    { path: "/preliminary", label: "Ön Tasarım", minStep: 1 },
    { path: "/viewer", label: "3D",     minStep: 3 },
    { path: "/report", label: "Rapor",  minStep: 3 },
  ];

  return (
    <nav style={{
      position: "fixed",
      top: 0, left: 0, right: 0,
      height: "52px",
      background: "#0c1018",
      borderBottom: "1px solid #1e2738",
      display: "flex",
      alignItems: "center",
      padding: "0 24px",
      gap: "8px",
      zIndex: 1000,
    }}>
      {/* Logo */}
      <span
        style={{
          fontFamily: "monospace",
          fontSize: "13px",
          fontWeight: "700",
          color: "#5b9cf6",
          letterSpacing: "3px",
          marginRight: "24px",
          cursor: "pointer",
        }}
        onClick={() => navigate("/")}
      >
        STAT
      </span>

      {/* Links */}
      {links.map((link) => {
        const active = location.pathname === link.path;
        const disabled = step < link.minStep;

        return (
          <button
            key={link.path}
            onClick={() => !disabled && navigate(link.path)}
            style={{
              background: active ? "#1e2738" : "transparent",
              border: "1px solid",
              borderColor: active ? "#2a3650" : "transparent",
              borderRadius: "6px",
              padding: "5px 14px",
              fontSize: "12px",
              fontWeight: "600",
              color: disabled ? "#2a3650" : active ? "#fff" : "#7090b8",
              cursor: disabled ? "not-allowed" : "pointer",
              letterSpacing: "1px",
            }}
          >
            {link.label}
          </button>
        );
      })}

      {/* Reset */}
      <button
        onClick={() => { reset(); navigate("/"); }}
        style={{
          marginLeft: "auto",
          background: "transparent",
          border: "1px solid #2a3650",
          borderRadius: "6px",
          padding: "5px 14px",
          fontSize: "11px",
          color: "#4a5c7a",
          cursor: "pointer",
          letterSpacing: "1px",
        }}
      >
        Sıfırla
      </button>
    </nav>
  );
}