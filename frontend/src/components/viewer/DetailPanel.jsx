import StatusBadge from "../shared/StatusBadge";

export default function DetailPanel({ element, onClose }) {
  if (!element) return null;

  const rows = [
    { key: "IFC Global ID", val: element.ifc_global_id },
    { key: "Tip",           val: element.ifc_type },
    { key: "İsim",          val: element.ifc_name || "-" },
    { key: "Tag",           val: element.ifc_tag || "-" },
    { key: "Kat",           val: element.ifc_story || "-" },
    { key: "Excel Label",   val: element.excel_label || "-" },
    { key: "Unity Check",   val: element.unity_check?.toFixed(3) ?? "-" },
    { key: "Failure Mode",  val: element.failure_mode || "-" },
    { key: "Kombinasyon",   val: element.governing_combo || "-" },
    { key: "Eşleşme Skoru", val: element.match_score?.toFixed(3) ?? "-" },
  ];

  return (
    <div style={{
      position: "absolute",
      top: "60px",
      right: "16px",
      width: "280px",
      background: "#0c1018",
      border: "1px solid #1e2738",
      borderRadius: "12px",
      zIndex: 100,
      overflow: "hidden",
    }}>
      {/* Header */}
      <div style={{
        padding: "12px 16px",
        borderBottom: "1px solid #1e2738",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
      }}>
        <div>
          <div style={{ fontSize: "13px", fontWeight: "700", color: "#fff", marginBottom: "4px" }}>
            {element.ifc_name || element.ifc_global_id}
          </div>
          <StatusBadge status={element.status} />
        </div>
        <button
          onClick={onClose}
          style={{
            background: "transparent",
            border: "none",
            color: "#4a5c7a",
            fontSize: "18px",
            cursor: "pointer",
            padding: "0 4px",
          }}
        >
          ×
        </button>
      </div>

      {/* Rows */}
      <div style={{ padding: "8px 0" }}>
        {rows.map(({ key, val }) => (
          <div key={key} style={{
            display: "flex",
            justifyContent: "space-between",
            padding: "6px 16px",
            borderBottom: "1px solid #1e273820",
          }}>
            <span style={{ fontSize: "11px", color: "#4a5c7a" }}>{key}</span>
            <span style={{
              fontSize: "11px",
              color: "#d8e4f8",
              fontFamily: "monospace",
              maxWidth: "160px",
              textAlign: "right",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}>
              {val}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}