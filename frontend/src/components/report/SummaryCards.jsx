import { STATUS_COLORS, STATUS_LABELS } from "../../utils/colorPalette";

export default function SummaryCards({ summary }) {
  if (!summary) return null;

  const { total, status_counts, by_story } = summary;

  return (
    <div>
      {/* Genel özet kartları */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(5, 1fr)",
        gap: "12px",
        marginBottom: "32px",
      }}>
        {Object.entries(STATUS_COLORS).map(([status, color]) => {
          const count = status_counts?.[status] ?? 0;
          const pct = total > 0 ? ((count / total) * 100).toFixed(0) : 0;
          return (
            <div key={status} style={{
              background: "#0c1018",
              border: `1px solid ${color}33`,
              borderTop: `3px solid ${color}`,
              borderRadius: "10px",
              padding: "16px",
              textAlign: "center",
            }}>
              <div style={{
                fontSize: "28px",
                fontWeight: "800",
                color: color,
                marginBottom: "4px",
              }}>
                {count}
              </div>
              <div style={{ fontSize: "11px", color: "#7090b8", marginBottom: "2px" }}>
                {STATUS_LABELS[status]}
              </div>
              <div style={{
                fontSize: "10px",
                fontFamily: "monospace",
                color: "#4a5c7a",
              }}>
                %{pct}
              </div>
            </div>
          );
        })}
      </div>

      {/* Kat bazlı tablo */}
      <div style={{
        background: "#0c1018",
        border: "1px solid #1e2738",
        borderRadius: "10px",
        overflow: "hidden",
      }}>
        <div style={{
          padding: "12px 18px",
          borderBottom: "1px solid #1e2738",
          fontSize: "12px",
          fontWeight: "700",
          color: "#5b9cf6",
          fontFamily: "monospace",
          letterSpacing: "1px",
          textTransform: "uppercase",
        }}>
          Kat Bazlı Dağılım
        </div>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
          <thead>
            <tr style={{ background: "#111620" }}>
              {["Kat", "Toplam", "Yetersiz", "Sınırda"].map((h) => (
                <th key={h} style={{
                  padding: "8px 16px",
                  textAlign: "left",
                  color: "#4a5c7a",
                  fontFamily: "monospace",
                  fontSize: "10px",
                  letterSpacing: "1px",
                  textTransform: "uppercase",
                  borderBottom: "1px solid #1e2738",
                }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {by_story?.map((row) => (
              <tr key={row.story} style={{ borderBottom: "1px solid #1e273840" }}>
                <td style={{ padding: "9px 16px", color: "#d8e4f8", fontWeight: "600" }}>
                  {row.story}
                </td>
                <td style={{ padding: "9px 16px", color: "#7090b8" }}>{row.total}</td>
                <td style={{ padding: "9px 16px", color: row.fail > 0 ? "#f06060" : "#7090b8", fontWeight: row.fail > 0 ? "700" : "400" }}>
                  {row.fail}
                </td>
                <td style={{ padding: "9px 16px", color: row.warning > 0 ? "#f0c040" : "#7090b8" }}>
                  {row.warning}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}