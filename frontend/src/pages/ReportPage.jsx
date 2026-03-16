import { useState } from "react";
import { useNavigate } from "react-router-dom";
import useAppStore from "../store/useAppStore";
import SummaryCards from "../components/report/SummaryCards";
import { compareRevisions } from "../services/api";

export default function ReportPage() {
  const navigate = useNavigate();
  const { summary, enrichedIFC, elements, reset, excelFile, statusColors } = useAppStore();

  const [compareResult, setCompareResult] = useState(null);
  const [oldFile, setOldFile] = useState(null);
  const [comparing, setComparing] = useState(false);
  const [activeTab, setActiveTab] = useState("summary"); // summary | compare

  // ─── IFC İndir ───
  const handleDownloadIFC = () => {
    if (!enrichedIFC) return;
    const url = URL.createObjectURL(enrichedIFC);
    const a = document.createElement("a");
    a.href = url;
    a.download = "enriched.ifc";
    a.click();
    URL.revokeObjectURL(url);
  };

  // ─── Excel Export ───
  const handleExportExcel = () => {
    if (!elements || elements.length === 0) return;

    const headers = ["Kat", "Eleman", "Tip", "Kesit", "Durum", "Unity Check", "Göçme Modu", "Kombinasyon",
      "As (mm²)", "AsMin (mm²)", "Donatı Oranı", "VRebar (mm²/m)", "ρ (%)", "ρ Durum",
      "BC Ratio", "BC Durum", "Uyarı Sayısı"];

    const rows = elements.map((el) => [
      el.ifc_story || "",
      el.ifc_name || "",
      el.ifc_type === "IfcBeam" ? "Kiriş" : "Kolon",
      el.excel_section || "",
      el.status || "",
      el.unity_check != null ? el.unity_check.toFixed(3) : "",
      el.failure_mode || "",
      el.governing_combo || "",
      el.as_total != null ? el.as_total.toFixed(0) : "",
      el.as_min != null ? el.as_min.toFixed(0) : "",
      el.rebar_ratio != null ? el.rebar_ratio.toFixed(2) + "x" : "",
      el.v_rebar != null ? el.v_rebar.toFixed(1) : "",
      el.rho != null ? (el.rho * 100).toFixed(3) : "",
      el.rho_status || "",
      el.bc_ratio_maj != null ? el.bc_ratio_maj.toFixed(3) : "",
      el.bc_status || "",
      el.warning_count || 0,
    ]);

    // CSV olarak indir (Excel açabilir)
    const csv = [headers.join(";"), ...rows.map(r => r.join(";"))].join("\n");
    const bom = "\uFEFF"; // UTF-8 BOM for Turkish chars
    const blob = new Blob([bom + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "analiz_raporu.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  // ─── PDF Export ───
  const handleExportPDF = () => {
    if (!elements || elements.length === 0) return;

    const sc = summary?.status_counts || {};
    const total = summary?.total || 0;

    // Basit HTML → print
    const criticalElements = elements.filter(e => e.status === "FAIL" || e.status === "BRITTLE").slice(0, 30);
    const warningElements = elements.filter(e => (e.warning_count || 0) > 0).slice(0, 20);

    const html = `<!DOCTYPE html><html><head><meta charset="utf-8">
    <title>Yapısal Analiz Raporu</title>
    <style>
      body { font-family: Arial, sans-serif; padding: 40px; color: #1a1a1a; max-width: 800px; margin: 0 auto; }
      h1 { font-size: 22px; border-bottom: 2px solid #333; padding-bottom: 8px; }
      h2 { font-size: 16px; color: #444; margin-top: 28px; border-bottom: 1px solid #ddd; padding-bottom: 4px; }
      .meta { font-size: 12px; color: #666; margin-bottom: 24px; }
      .grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; margin: 16px 0; }
      .card { border: 1px solid #ddd; border-radius: 6px; padding: 12px; text-align: center; }
      .card .num { font-size: 24px; font-weight: 800; }
      .card .label { font-size: 10px; color: #888; margin-top: 2px; }
      table { width: 100%; border-collapse: collapse; font-size: 11px; margin: 12px 0; }
      th { background: #f5f5f5; padding: 6px 8px; text-align: left; border: 1px solid #ddd; font-size: 10px; }
      td { padding: 5px 8px; border: 1px solid #eee; }
      .ok { color: #16a34a; } .warn { color: #ca8a04; } .fail { color: #dc2626; font-weight: 700; }
      .brittle { color: #ea580c; font-weight: 700; }
      @media print { body { padding: 20px; } }
    </style></head><body>
    <h1>Yapısal Analiz Raporu</h1>
    <div class="meta">Tarih: ${new Date().toLocaleDateString("tr-TR")} · Toplam Eleman: ${total}</div>

    <h2>Genel Özet</h2>
    <div class="grid">
      <div class="card"><div class="num ok">${sc.OK || 0}</div><div class="label">Yeterli</div></div>
      <div class="card"><div class="num warn">${sc.WARNING || 0}</div><div class="label">Sınırda</div></div>
      <div class="card"><div class="num fail">${sc.FAIL || 0}</div><div class="label">Yetersiz</div></div>
      <div class="card"><div class="num brittle">${sc.BRITTLE || 0}</div><div class="label">Gevrek</div></div>
      <div class="card"><div class="num" style="color:#94a3b8">${sc.UNMATCHED || 0}</div><div class="label">Eşleşmedi</div></div>
    </div>

    <h2>Kat Bazlı Dağılım</h2>
    <table>
      <tr><th>Kat</th><th>Toplam</th><th>Yetersiz</th><th>Sınırda</th></tr>
      ${(summary?.by_story || []).map(r => `<tr><td>${r.story}</td><td>${r.total}</td><td class="fail">${r.fail}</td><td class="warn">${r.warning}</td></tr>`).join("")}
    </table>

    <h2>Kritik Elemanlar (FAIL + BRITTLE)</h2>
    <table>
      <tr><th>Kat</th><th>Eleman</th><th>Tip</th><th>Durum</th><th>UC</th><th>Göçme</th></tr>
      ${criticalElements.map(e => `<tr>
        <td>${e.ifc_story}</td><td>${e.ifc_name}</td>
        <td>${e.ifc_type === "IfcBeam" ? "Kiriş" : "Kolon"}</td>
        <td class="${e.status === "BRITTLE" ? "brittle" : "fail"}">${e.status}</td>
        <td>${e.unity_check?.toFixed(3) ?? "-"}</td>
        <td>${e.failure_mode || "-"}</td>
      </tr>`).join("")}
      ${criticalElements.length === 0 ? '<tr><td colspan="6" style="text-align:center;color:#16a34a">Kritik eleman bulunmadı ✓</td></tr>' : ""}
    </table>

    ${warningElements.length > 0 ? `
    <h2>Yapısal Uyarılar</h2>
    <table>
      <tr><th>Kat</th><th>Eleman</th><th>Uyarılar</th></tr>
      ${warningElements.map(e => `<tr>
        <td>${e.ifc_story}</td><td>${e.ifc_name}</td>
        <td style="font-size:10px">${(e.warnings || []).join("<br>")}</td>
      </tr>`).join("")}
    </table>` : ""}

    </body></html>`;

    const win = window.open("", "_blank");
    win.document.write(html);
    win.document.close();
    setTimeout(() => win.print(), 500);
  };

  // ─── Revizyon Karşılaştırma ───
  const handleCompare = async () => {
    if (!oldFile || !excelFile) return;
    setComparing(true);
    try {
      const result = await compareRevisions(oldFile, excelFile);
      setCompareResult(result);
    } catch (err) {
      alert("Karşılaştırma hatası: " + (err.message || "Bilinmeyen hata"));
    } finally {
      setComparing(false);
    }
  };

  const tabs = [
    { key: "summary", label: "Özet Rapor" },
    { key: "compare", label: "Revizyon Karşılaştırma" },
  ];

  return (
    <div style={{
      minHeight: "100vh",
      background: "#080b10",
      padding: "80px 32px 48px",
      color: "#d8e4f8",
    }}>
      <div style={{ maxWidth: "900px", margin: "0 auto" }}>

        {/* Başlık */}
        <div style={{
          fontFamily: "monospace", fontSize: "11px", color: "#5b9cf6",
          letterSpacing: "3px", textTransform: "uppercase", marginBottom: "8px",
        }}>
          Adım 3
        </div>
        <div style={{
          display: "flex", justifyContent: "space-between", alignItems: "flex-start",
          marginBottom: "24px", flexWrap: "wrap", gap: "16px",
        }}>
          <div>
            <h1 style={{ fontSize: "24px", fontWeight: "800", marginBottom: "4px" }}>Analiz Raporu</h1>
            <p style={{ fontSize: "13px", color: "#7090b8" }}>
              Toplam {summary?.total ?? 0} eleman analiz edildi.
              {summary?.total_warnings > 0 && (
                <span style={{ color: "#eab308" }}> · {summary.total_warnings} yapısal uyarı</span>
              )}
            </p>
          </div>

          {/* Butonlar */}
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            <Btn onClick={() => navigate("/viewer")} label="← Viewer" />
            <Btn onClick={handleExportPDF} label="📄 PDF" color="#5b9cf6" filled />
            <Btn onClick={handleExportExcel} label="📊 Excel" color="#22c55e" filled />
            {enrichedIFC && <Btn onClick={handleDownloadIFC} label="↓ IFC" color="#f97316" filled />}
            <Btn onClick={() => { reset(); navigate("/"); }} label="Yeni Analiz" muted />
          </div>
        </div>

        {/* Sekmeler */}
        <div style={{ display: "flex", gap: "4px", marginBottom: "24px" }}>
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setActiveTab(t.key)}
              style={{
                padding: "8px 18px", borderRadius: "6px",
                border: activeTab === t.key ? "1px solid #5b9cf655" : "1px solid #1e2738",
                background: activeTab === t.key ? "#5b9cf615" : "transparent",
                color: activeTab === t.key ? "#5b9cf6" : "#4a5c7a",
                fontSize: "12px", fontWeight: "700", cursor: "pointer", letterSpacing: "1px",
              }}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* ═══ ÖZET RAPOR SEKMESİ ═══ */}
        {activeTab === "summary" && (
          <>
            <SummaryCards summary={summary} />

            {/* Kritik Elemanlar */}
            {elements.filter(e => e.status === "FAIL" || e.status === "BRITTLE").length > 0 && (
              <div style={panelStyle}>
                <div style={panelTitle}>
                  Kritik Elemanlar ({elements.filter(e => e.status === "FAIL" || e.status === "BRITTLE").length})
                </div>
                <table style={tableStyle}>
                  <thead>
                    <tr style={{ background: "#111620" }}>
                      {["Kat", "Eleman", "Tip", "Durum", "UC", "Göçme Modu"].map(h => (
                        <th key={h} style={thStyle}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {elements
                      .filter(e => e.status === "FAIL" || e.status === "BRITTLE")
                      .slice(0, 50)
                      .map((e, i) => (
                        <tr key={i} style={{ borderBottom: "1px solid #1e273830" }}>
                          <td style={tdStyle}>{e.ifc_story}</td>
                          <td style={{ ...tdStyle, fontWeight: "600" }}>{e.ifc_name}</td>
                          <td style={tdStyle}>{e.ifc_type === "IfcBeam" ? "Kiriş" : "Kolon"}</td>
                          <td style={{ ...tdStyle, color: e.status === "BRITTLE" ? "#f97316" : "#ef4444", fontWeight: "700" }}>
                            {e.status === "BRITTLE" ? "Gevrek" : "Yetersiz"}
                          </td>
                          <td style={{ ...tdStyle, fontFamily: "monospace" }}>{e.unity_check?.toFixed(3) ?? "-"}</td>
                          <td style={tdStyle}>{e.failure_mode || "-"}</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Yapısal Uyarılar */}
            {elements.filter(e => (e.warning_count || 0) > 0).length > 0 && (
              <div style={{ ...panelStyle, borderColor: "#eab30833" }}>
                <div style={{ ...panelTitle, color: "#eab308" }}>
                  Yapısal Uyarılar ({elements.filter(e => (e.warning_count || 0) > 0).length} eleman)
                </div>
                {elements
                  .filter(e => (e.warning_count || 0) > 0)
                  .slice(0, 20)
                  .map((e, i) => (
                    <div key={i} style={{ padding: "8px 16px", borderBottom: "1px solid #1e273820" }}>
                      <span style={{ fontSize: "12px", fontWeight: "600", color: "#d8e4f8" }}>
                        {e.ifc_name} · {e.ifc_story}
                      </span>
                      {(e.warnings || []).map((w, j) => (
                        <div key={j} style={{ fontSize: "10px", color: "#eab308", marginTop: "2px", paddingLeft: "8px" }}>
                          ⚠ {w}
                        </div>
                      ))}
                    </div>
                  ))}
              </div>
            )}

            {/* Eşleşmeyen elemanlar */}
            {summary?.unmatched_elements?.length > 0 && (
              <div style={{ ...panelStyle, borderColor: "#300a0a" }}>
                <div style={{ ...panelTitle, color: "#f06060" }}>
                  Eşleşmeyen Elemanlar ({summary.unmatched_elements.length})
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", padding: "0 16px 12px" }}>
                  {summary.unmatched_elements.slice(0, 30).map((id) => (
                    <span key={id} style={{
                      fontFamily: "monospace", fontSize: "10px", padding: "2px 8px",
                      background: "#300a0a", border: "1px solid #f0606033", borderRadius: "4px", color: "#f06060",
                    }}>{id}</span>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* ═══ REVİZYON KARŞILAŞTIRMA SEKMESİ ═══ */}
        {activeTab === "compare" && (
          <div>
            <div style={panelStyle}>
              <div style={panelTitle}>Revizyon Karşılaştırma</div>
              <div style={{ padding: "16px" }}>
                <p style={{ fontSize: "12px", color: "#7090b8", marginBottom: "16px" }}>
                  Mevcut analiz (yeni) ile eski bir Excel dosyasını karşılaştırın. Hangi elemanlar iyileşti, hangilerinde kötüleşme var, yeni eklenen veya kaldırılan elemanları görün.
                </p>

                <div style={{ marginBottom: "16px" }}>
                  <label style={{ fontSize: "10px", color: "#4a5c7a", letterSpacing: "1px", display: "block", marginBottom: "6px" }}>
                    ESKİ EXCEL DOSYASI (REVİZYON ÖNCESİ)
                  </label>
                  <input
                    type="file"
                    accept=".xlsx"
                    onChange={(e) => setOldFile(e.target.files[0])}
                    style={{ fontSize: "12px", color: "#d8e4f8" }}
                  />
                </div>

                <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                  <button
                    onClick={handleCompare}
                    disabled={!oldFile || comparing}
                    style={{
                      padding: "8px 20px",
                      background: !oldFile || comparing ? "#1e2738" : "#5b9cf6",
                      border: "none", borderRadius: "6px",
                      color: !oldFile || comparing ? "#4a5c7a" : "#fff",
                      fontSize: "12px", fontWeight: "700", cursor: !oldFile ? "not-allowed" : "pointer",
                    }}
                  >
                    {comparing ? "Karşılaştırılıyor..." : "Karşılaştır"}
                  </button>
                  {compareResult && (
                    <span style={{ fontSize: "11px", color: "#22c55e" }}>✓ Karşılaştırma tamamlandı</span>
                  )}
                </div>
              </div>
            </div>

            {/* Karşılaştırma Sonuçları */}
            {compareResult && (
              <>
                {/* Özet kartları */}
                <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "10px", margin: "20px 0" }}>
                  <CompareCard label="İyileşen" count={compareResult.summary.improved_count} color="#22c55e" icon="↑" />
                  <CompareCard label="Kötüleşen" count={compareResult.summary.worsened_count} color="#ef4444" icon="↓" />
                  <CompareCard label="Değişmeyen" count={compareResult.summary.unchanged_count} color="#64748b" icon="=" />
                  <CompareCard label="Yeni Eklenen" count={compareResult.summary.added_count} color="#5b9cf6" icon="+" />
                  <CompareCard label="Kaldırılan" count={compareResult.summary.removed_count} color="#eab308" icon="-" />
                </div>

                {/* İyileşen elemanlar */}
                {compareResult.improved.length > 0 && (
                  <div style={panelStyle}>
                    <div style={{ ...panelTitle, color: "#22c55e" }}>↑ İyileşen Elemanlar ({compareResult.improved.length})</div>
                    <table style={tableStyle}>
                      <thead><tr style={{ background: "#111620" }}>
                        {["Kat", "Eleman", "Eski Durum", "Yeni Durum", "Eski UC", "Yeni UC"].map(h => <th key={h} style={thStyle}>{h}</th>)}
                      </tr></thead>
                      <tbody>
                        {compareResult.improved.slice(0, 30).map((e, i) => (
                          <tr key={i} style={{ borderBottom: "1px solid #1e273830" }}>
                            <td style={tdStyle}>{e.story}</td>
                            <td style={{ ...tdStyle, fontWeight: "600" }}>{e.label}</td>
                            <td style={{ ...tdStyle, color: "#ef4444" }}>{e.old_status}</td>
                            <td style={{ ...tdStyle, color: "#22c55e" }}>{e.new_status}</td>
                            <td style={{ ...tdStyle, fontFamily: "monospace" }}>{e.old_uc?.toFixed(3) ?? "-"}</td>
                            <td style={{ ...tdStyle, fontFamily: "monospace" }}>{e.new_uc?.toFixed(3) ?? "-"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Kötüleşen elemanlar */}
                {compareResult.worsened.length > 0 && (
                  <div style={{ ...panelStyle, borderColor: "#ef444433" }}>
                    <div style={{ ...panelTitle, color: "#ef4444" }}>↓ Kötüleşen Elemanlar ({compareResult.worsened.length})</div>
                    <table style={tableStyle}>
                      <thead><tr style={{ background: "#111620" }}>
                        {["Kat", "Eleman", "Eski Durum", "Yeni Durum", "Eski UC", "Yeni UC"].map(h => <th key={h} style={thStyle}>{h}</th>)}
                      </tr></thead>
                      <tbody>
                        {compareResult.worsened.slice(0, 30).map((e, i) => (
                          <tr key={i} style={{ borderBottom: "1px solid #1e273830" }}>
                            <td style={tdStyle}>{e.story}</td>
                            <td style={{ ...tdStyle, fontWeight: "600" }}>{e.label}</td>
                            <td style={{ ...tdStyle, color: "#22c55e" }}>{e.old_status}</td>
                            <td style={{ ...tdStyle, color: "#ef4444" }}>{e.new_status}</td>
                            <td style={{ ...tdStyle, fontFamily: "monospace" }}>{e.old_uc?.toFixed(3) ?? "-"}</td>
                            <td style={{ ...tdStyle, fontFamily: "monospace" }}>{e.new_uc?.toFixed(3) ?? "-"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Yardımcı bileşenler ───

function Btn({ onClick, label, color, filled, muted }) {
  return (
    <button onClick={onClick} style={{
      padding: "7px 16px", borderRadius: "7px",
      background: filled ? color : "transparent",
      border: filled ? "none" : `1px solid ${muted ? "#2a3650" : "#2a3650"}`,
      color: filled ? "#fff" : muted ? "#4a5c7a" : "#7090b8",
      fontSize: "11px", fontWeight: "700", cursor: "pointer", letterSpacing: "0.5px",
    }}>
      {label}
    </button>
  );
}

function CompareCard({ label, count, color, icon }) {
  return (
    <div style={{
      background: "#0c1018", border: `1px solid ${color}33`, borderTop: `3px solid ${color}`,
      borderRadius: "8px", padding: "12px", textAlign: "center",
    }}>
      <div style={{ fontSize: "10px", color: "#4a5c7a", marginBottom: "4px" }}>{icon}</div>
      <div style={{ fontSize: "22px", fontWeight: "800", color }}>{count}</div>
      <div style={{ fontSize: "10px", color: "#7090b8" }}>{label}</div>
    </div>
  );
}

const panelStyle = {
  marginTop: "20px", background: "#0c1018", border: "1px solid #1e2738",
  borderRadius: "10px", overflow: "hidden",
};
const panelTitle = {
  padding: "12px 16px", borderBottom: "1px solid #1e2738",
  fontSize: "12px", fontWeight: "700", color: "#5b9cf6",
  fontFamily: "monospace", letterSpacing: "1px", textTransform: "uppercase",
};
const tableStyle = { width: "100%", borderCollapse: "collapse", fontSize: "12px" };
const thStyle = {
  padding: "8px 12px", textAlign: "left", color: "#4a5c7a",
  fontFamily: "monospace", fontSize: "10px", letterSpacing: "1px",
  borderBottom: "1px solid #1e2738",
};
const tdStyle = { padding: "7px 12px", color: "#d8e4f8" };
