import StatusBadge from "../shared/StatusBadge";
import useAppStore from "../../store/useAppStore";

export default function DetailPanel({ element, onClose }) {
  if (!element) return null;

  const { statusColors } = useAppStore();
  const statusColor = statusColors[element.status] || "#64748b";

  const uc = element.unity_check;
  const capacityPct = uc != null ? Math.min(Math.round(uc * 100), 200) : null;

  const getBarColor = (pct) => {
    if (pct == null) return "#64748b";
    if (pct < 90) return statusColors.OK || "#22c55e";
    if (pct < 100) return statusColors.WARNING || "#eab308";
    return statusColors.FAIL || "#ef4444";
  };

  const secDepth = element.sec_depth;
  const secWidth = element.sec_width;
  const sectionDisplay = (secDepth && secWidth)
    ? `${(secDepth * 100).toFixed(0)} × ${(secWidth * 100).toFixed(0)} cm`
    : element.excel_section || "-";
  const sectionArea = (secDepth && secWidth)
    ? `${(secDepth * secWidth * 10000).toFixed(0)} cm²`
    : "-";

  const typeLabel = element.ifc_type === "IfcBeam" ? "Kiriş"
    : element.ifc_type === "IfcColumn" ? "Kolon" : element.ifc_type;

  const failureModeMap = {
    "Moment": "Eğilme (Sünek)", "Shear": "Kesme (Gevrek)",
    "PMM": "Eksenel + Eğilme", "Overstressed": "Aşırı Gerilme",
  };
  const failureModeLabel = failureModeMap[element.failure_mode] || element.failure_mode || "-";

  const isBeam = element.ifc_type === "IfcBeam";
  const isColumn = element.ifc_type === "IfcColumn";
  const hasRebar = element.as_total != null || element.as_top != null || element.as_bot != null;
  const warnings = element.warnings || [];

  return (
    <div style={{
      position: "absolute", top: "12px", right: "12px", width: "300px",
      background: "#0c1018ee", border: "1px solid #1e2738", borderRadius: "12px",
      zIndex: 100, overflow: "hidden", backdropFilter: "blur(8px)",
      maxHeight: "calc(100vh - 140px)", overflowY: "auto",
    }}>
      {/* Header */}
      <div style={{ padding: "14px 16px", borderBottom: `2px solid ${statusColor}44`, background: `${statusColor}08` }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div style={{ fontSize: "16px", fontWeight: "800", color: "#fff", marginBottom: "2px" }}>
              {element.ifc_name || element.ifc_global_id}
            </div>
            <div style={{ fontSize: "11px", color: "#7090b8", marginBottom: "6px" }}>
              {typeLabel} · {element.ifc_story || "-"} · {element.excel_section || "-"}
            </div>
            <StatusBadge status={element.status} />
          </div>
          <button onClick={onClose} style={{ background: "transparent", border: "none", color: "#4a5c7a", fontSize: "20px", cursor: "pointer" }}>×</button>
        </div>
      </div>

      {/* Kapasite */}
      {capacityPct != null && (
        <div style={{ padding: "12px 16px", borderBottom: "1px solid #1e273840" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "6px" }}>
            <span style={labelStyle}>Kapasite Kullanımı</span>
            <span style={{ fontSize: "20px", fontWeight: "800", fontFamily: "monospace", color: getBarColor(capacityPct) }}>%{capacityPct}</span>
          </div>
          <div style={{ width: "100%", height: "8px", background: "#111620", borderRadius: "4px", overflow: "hidden" }}>
            <div style={{ width: `${Math.min(capacityPct, 100)}%`, height: "100%", background: getBarColor(capacityPct), borderRadius: "4px", transition: "width 0.3s" }} />
          </div>
          {capacityPct >= 100 && <div style={{ fontSize: "9px", color: "#ef4444", marginTop: "4px", fontWeight: "600" }}>⚠ Kapasite aşımı — %{capacityPct - 100} fazla</div>}
        </div>
      )}

      {/* Kesit */}
      <Section title="KESİT ÖZELLİKLERİ">
        <Row label="Kesit Adı" value={element.excel_section || "-"} />
        <Row label="Boyut" value={sectionDisplay} />
        <Row label="Kesit Alanı" value={sectionArea} />
      </Section>

      {/* Donatı */}
      {hasRebar && (
        <Section title="DONATI BİLGİLERİ">
          {isColumn && element.as_total != null && (
            <>
              <Row label="Mevcut Donatı (As)" value={`${element.as_total.toFixed(0)} mm²`} />
              {element.as_min != null && <Row label="Min. Donatı (As,min)" value={`${element.as_min.toFixed(0)} mm²`} />}
              {element.rebar_ratio != null && <Row label="Donatı Oranı" value={`${element.rebar_ratio.toFixed(2)}x`} highlight={element.rebar_ratio < 1.0} good={element.rebar_ratio >= 1.5} />}
            </>
          )}
          {isBeam && (
            <>
              {element.as_top != null && <Row label="Üst Donatı (As,üst)" value={`${element.as_top.toFixed(0)} mm²`} />}
              {element.as_bot != null && <Row label="Alt Donatı (As,alt)" value={`${element.as_bot.toFixed(0)} mm²`} />}
              {element.rebar_ratio != null && <Row label="Donatı Oranı" value={`${element.rebar_ratio.toFixed(2)}x`} highlight={element.rebar_ratio < 1.0} good={element.rebar_ratio >= 1.5} />}
            </>
          )}
          {element.v_rebar != null && <Row label="Kesme Donatısı" value={`${element.v_rebar.toFixed(1)} mm²/m`} />}

          {/* ρ kontrolü */}
          {element.rho != null && (
            <div style={{ marginTop: "6px", padding: "6px 8px", background: "#111620", borderRadius: "5px", fontSize: "10px", fontFamily: "monospace" }}>
              <div style={{ color: "#7090b8", marginBottom: "2px" }}>TS 500 Donatı Oranı Kontrolü</div>
              <div style={{ color: "#d8e4f8" }}>
                ρ = {(element.rho * 100).toFixed(2)}%
                <span style={{ color: "#4a5c7a" }}> &nbsp;(min: {(element.rho_min * 100).toFixed(2)}% — max: {(element.rho_max * 100).toFixed(2)}%)</span>
              </div>
              <div style={{
                marginTop: "4px",
                color: element.rho_status === "OK" ? "#22c55e" : "#ef4444",
                fontWeight: "600",
              }}>
                {element.rho_status === "OK" ? "✓ Donatı oranı yeterli" :
                 element.rho_status === "MIN_FAIL" ? "✗ Minimum donatı oranı altında" :
                 "✗ Maksimum donatı oranı aşıldı"}
              </div>
            </div>
          )}
        </Section>
      )}

      {/* Birleşim Bölgesi (sadece kolonlar) */}
      {isColumn && element.bc_ratio_maj != null && (
        <Section title="BİRLEŞİM BÖLGESİ (TBDY 7.3)">
          <Row label="BC Ratio (Majör)" value={element.bc_ratio_maj?.toFixed(3) ?? "-"}
            highlight={element.bc_status === "FAIL"} good={element.bc_status === "OK"} />
          <Row label="BC Ratio (Minör)" value={element.bc_ratio_min?.toFixed(3) ?? "-"} />
          <Row label="JS Ratio (Majör)" value={element.js_ratio_maj?.toFixed(3) ?? "-"}
            highlight={element.js_status === "FAIL"} />
          <Row label="JS Ratio (Minör)" value={element.js_ratio_min?.toFixed(3) ?? "-"} />

          <StatusTag
            status={element.bc_status}
            okText="✓ Güçlü kolon — zayıf kiriş sağlanıyor"
            warnText="◐ Sınırda — BCRatio > 0.833"
            failText="✗ Zayıf kolon — TBDY 7.3.3 ihlali"
          />
          {element.js_status === "FAIL" && (
            <StatusTag status="FAIL" failText="✗ Birleşim kesme kapasitesi aşıldı" />
          )}
        </Section>
      )}

      {/* Analiz Sonuçları */}
      <Section title="ANALİZ SONUÇLARI">
        <Row label="Unity Check (D/C)" value={uc != null ? uc.toFixed(3) : "-"} highlight={uc != null && uc >= 1.0} />
        <Row label="Göçme Modu" value={failureModeLabel} />
        <Row label="Yük Kombinasyonu" value={element.governing_combo || "-"} />
      </Section>

      {/* Uyarılar */}
      {warnings.length > 0 && (
        <Section title={`UYARILAR (${warnings.length})`}>
          {warnings.map((w, i) => (
            <div key={i} style={{
              fontSize: "10px", color: "#f0c040", background: "#f0c04010",
              border: "1px solid #f0c04033", borderRadius: "4px",
              padding: "5px 8px", marginBottom: "4px", lineHeight: "1.4",
            }}>
              ⚠ {w}
            </div>
          ))}
        </Section>
      )}

      {/* Konum */}
      <Section title="KONUM" last>
        <Row label="Kat" value={element.ifc_story || "-"} />
        <Row label="X" value={element.x != null ? `${element.x.toFixed(2)} m` : "-"} />
        <Row label="Y" value={element.y != null ? `${element.y.toFixed(2)} m` : "-"} />
        <Row label="Z" value={element.z != null ? `${element.z.toFixed(2)} m` : "-"} />
      </Section>
    </div>
  );
}

// ─── Yardımcılar ───

const labelStyle = { fontSize: "10px", color: "#4a5c7a", letterSpacing: "1px", textTransform: "uppercase" };

function Section({ title, children, last }) {
  return (
    <div style={{ padding: "10px 16px", borderBottom: last ? "none" : "1px solid #1e273840" }}>
      <div style={{
        fontSize: "10px", fontWeight: "700", color: "#5b9cf6",
        letterSpacing: "1.5px", textTransform: "uppercase",
        marginBottom: "6px", fontFamily: "monospace",
      }}>{title}</div>
      {children}
    </div>
  );
}

function Row({ label, value, highlight, good }) {
  let color = "#d8e4f8";
  if (highlight) color = "#ef4444";
  else if (good) color = "#22c55e";
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "4px 0" }}>
      <span style={{ fontSize: "11px", color: "#4a5c7a" }}>{label}</span>
      <span style={{
        fontSize: "11px", color, fontFamily: "monospace",
        fontWeight: (highlight || good) ? "700" : "400",
        maxWidth: "170px", textAlign: "right",
        overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
      }}>{value}</span>
    </div>
  );
}

function StatusTag({ status, okText, warnText, failText }) {
  if (!status) return null;
  const isOk = status === "OK";
  const isFail = status === "FAIL";
  const text = isFail ? failText : isOk ? okText : (warnText || "");
  if (!text) return null;
  return (
    <div style={{
      marginTop: "4px", padding: "4px 8px", borderRadius: "4px",
      fontSize: "10px", fontWeight: "600",
      background: isFail ? "#ef444415" : isOk ? "#22c55e15" : "#eab30815",
      color: isFail ? "#ef4444" : isOk ? "#22c55e" : "#eab308",
      border: `1px solid ${isFail ? "#ef444433" : isOk ? "#22c55e33" : "#eab30833"}`,
    }}>{text}</div>
  );
}
