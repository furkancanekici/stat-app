import { useNavigate } from "react-router-dom";
import useAppStore from "../store/useAppStore";
import SummaryCards from "../components/report/SummaryCards";

export default function ReportPage() {
  const navigate = useNavigate();
  const { summary, enrichedIFC, ifcFile, reset } = useAppStore();

  const handleDownloadIFC = () => {
    if (!enrichedIFC) return;
    const url = URL.createObjectURL(enrichedIFC);
    const a = document.createElement("a");
    a.href = url;
    a.download = ifcFile?.name?.replace(".ifc", "_enriched.ifc") || "enriched.ifc";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: "#080b10",
      padding: "80px 32px 48px",
      color: "#d8e4f8",
    }}>
      <div style={{ maxWidth: "860px", margin: "0 auto" }}>

        {/* Başlık */}
        <div style={{
          fontFamily: "monospace",
          fontSize: "11px",
          color: "#5b9cf6",
          letterSpacing: "3px",
          textTransform: "uppercase",
          marginBottom: "8px",
        }}>
          Adım 3
        </div>
        <div style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: "32px",
          flexWrap: "wrap",
          gap: "16px",
        }}>
          <div>
            <h1 style={{ fontSize: "24px", fontWeight: "800", marginBottom: "4px" }}>
              Analiz Raporu
            </h1>
            <p style={{ fontSize: "13px", color: "#7090b8" }}>
              Toplam {summary?.total ?? 0} eleman analiz edildi.
            </p>
          </div>

          {/* Butonlar */}
          <div style={{ display: "flex", gap: "10px" }}>
            <button
              onClick={() => navigate("/viewer")}
              style={{
                padding: "8px 18px",
                background: "transparent",
                border: "1px solid #2a3650",
                borderRadius: "8px",
                color: "#7090b8",
                fontSize: "12px",
                fontWeight: "700",
                cursor: "pointer",
                letterSpacing: "1px",
              }}
            >
              ← Viewer
            </button>

            {enrichedIFC && (
              <button
                onClick={handleDownloadIFC}
                style={{
                  padding: "8px 18px",
                  background: "#5b9cf6",
                  border: "none",
                  borderRadius: "8px",
                  color: "#fff",
                  fontSize: "12px",
                  fontWeight: "700",
                  cursor: "pointer",
                  letterSpacing: "1px",
                }}
              >
                ↓ Enriched IFC İndir
              </button>
            )}

            <button
              onClick={() => { reset(); navigate("/"); }}
              style={{
                padding: "8px 18px",
                background: "transparent",
                border: "1px solid #2a3650",
                borderRadius: "8px",
                color: "#4a5c7a",
                fontSize: "12px",
                cursor: "pointer",
                letterSpacing: "1px",
              }}
            >
              Yeni Analiz
            </button>
          </div>
        </div>

        {/* Summary Cards */}
        <SummaryCards summary={summary} />

        {/* Eşleşmeyen elemanlar */}
        {summary?.unmatched_elements?.length > 0 && (
          <div style={{
            marginTop: "24px",
            background: "#0c1018",
            border: "1px solid #300a0a",
            borderRadius: "10px",
            padding: "16px 18px",
          }}>
            <div style={{
              fontSize: "12px",
              fontWeight: "700",
              color: "#f06060",
              marginBottom: "10px",
              fontFamily: "monospace",
              letterSpacing: "1px",
              textTransform: "uppercase",
            }}>
              ⚠ Eşleşmeyen Elemanlar ({summary.unmatched_elements.length})
            </div>
            <div style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "6px",
            }}>
              {summary.unmatched_elements.slice(0, 20).map((id) => (
                <span key={id} style={{
                  fontFamily: "monospace",
                  fontSize: "10px",
                  padding: "2px 8px",
                  background: "#300a0a",
                  border: "1px solid #f0606033",
                  borderRadius: "4px",
                  color: "#f06060",
                }}>
                  {id}
                </span>
              ))}
              {summary.unmatched_elements.length > 20 && (
                <span style={{ fontSize: "11px", color: "#4a5c7a", alignSelf: "center" }}>
                  +{summary.unmatched_elements.length - 20} daha
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}