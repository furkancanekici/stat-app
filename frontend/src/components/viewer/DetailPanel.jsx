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
    "Moment": "Eğilme (Sünek)",
    "Shear": "Kesme (Gevrek)",
    "PMM": "Eksenel + Eğilme",
    "Overstressed": "Aşırı Gerilme",
  };
  const failureModeLabel = failureModeMap[element.failure_mode] || element.failure_mode || "-";

  const isBeam = element.ifc_type === "IfcBeam";
  const isColumn = element.ifc_type === "IfcColumn";

  // Donatı değerleri
  const asTotal = element.as_total;
  const asMin = element.as_min;
  const asTop = element.as_top;
  const asBot = element.as_bot;
  const vRebar = element.v_rebar;
  const rebarRatio = element.rebar_ratio;

  const hasRebar = asTotal != null || asTop != null || asBot != null;

  return (
    <div style={{
      position: "absolute",
      top: "12px",
      right: "12px",
      width: "300px",
      background: "#0c1018ee",
      border: "1px solid #1e2738",
      borderRadius: "12px",
      zIndex: 100,
      overflow: "hidden",
      backdropFilter: "blur(8px)",
      maxHeight: "calc(100vh - 140px)",
      overflowY: "auto",
    }}>
      {/* ─── Header ─── */}
      <div style={{
        padding: "14px 16px",
        borderBottom: `2px solid ${statusColor}44`,
        background: `${statusColor}08`,
      }}>
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
          <button
            onClick={onClose}
            style={{ background: "transparent", border: "none", color: "#4a5c7a", fontSize: "20px", cursor: "pointer", padding: "0 2px", lineHeight: "1" }}
          >
            ×
          </button>
        </div>
      </div>

      {/* ─── Kapasite Göstergesi ─── */}
      {capacityPct != null && (
        <div style={{ padding: "12px 16px", borderBottom: "1px solid #1e273840" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "6px" }}>
            <span style={sectionLabelStyle}>Kapasite Kullanımı</span>
            <span style={{
              fontSize: "20px", fontWeight: "800", fontFamily: "monospace",
              color: getBarColor(capacityPct),
            }}>
              %{capacityPct}
            </span>
          </div>
          <div style={{ width: "100%", height: "8px", background: "#111620", borderRadius: "4px", overflow: "hidden" }}>
            <div style={{
              width: `${Math.min(capacityPct, 100)}%`,
              height: "100%",
              background: getBarColor(capacityPct),
              borderRadius: "4px",
              transition: "width 0.3s ease",
            }} />
          </div>
          {capacityPct >= 100 && (
            <div style={{ fontSize: "9px", color: "#ef4444", marginTop: "4px", fontWeight: "600" }}>
              ⚠ Kapasite aşımı — %{capacityPct - 100} fazla
            </div>
          )}
        </div>
      )}

      {/* ─── Kesit Özellikleri ─── */}
      <div style={{ padding: "10px 16px", borderBottom: "1px solid #1e273840" }}>
        <div style={sectionTitleStyle}>KESİT ÖZELLİKLERİ</div>
        <Row label="Kesit Adı" value={element.excel_section || "-"} />
        <Row label="Boyut" value={sectionDisplay} />
        <Row label="Kesit Alanı" value={sectionArea} />
        {secDepth != null && <Row label="Derinlik (h)" value={`${(secDepth * 100).toFixed(1)} cm`} />}
        {secWidth != null && <Row label="Genişlik (b)" value={`${(secWidth * 100).toFixed(1)} cm`} />}
      </div>

      {/* ─── Donatı Bilgileri ─── */}
      {hasRebar && (
        <div style={{ padding: "10px 16px", borderBottom: "1px solid #1e273840" }}>
          <div style={sectionTitleStyle}>DONATI BİLGİLERİ</div>

          {/* Kolon donatısı */}
          {isColumn && asTotal != null && (
            <>
              <Row label="Mevcut Donatı (As)" value={`${asTotal.toFixed(0)} mm²`} />
              {asMin != null && <Row label="Minimum Donatı (As,min)" value={`${asMin.toFixed(0)} mm²`} />}
              {rebarRatio != null && (
                <Row
                  label="Donatı Oranı (As/As,min)"
                  value={`${rebarRatio.toFixed(2)}x`}
                  highlight={rebarRatio < 1.0}
                  good={rebarRatio >= 1.5}
                />
              )}
            </>
          )}

          {/* Kiriş donatısı */}
          {isBeam && (
            <>
              {asTop != null && <Row label="Üst Donatı (As,üst)" value={`${asTop.toFixed(0)} mm²`} />}
              {asBot != null && <Row label="Alt Donatı (As,alt)" value={`${asBot.toFixed(0)} mm²`} />}
              {asTotal != null && <Row label="Toplam Donatı" value={`${asTotal.toFixed(0)} mm²`} />}
              {asMin != null && <Row label="Minimum Donatı" value={`${asMin.toFixed(0)} mm²`} />}
              {rebarRatio != null && (
                <Row
                  label="Donatı Oranı (As/As,min)"
                  value={`${rebarRatio.toFixed(2)}x`}
                  highlight={rebarRatio < 1.0}
                  good={rebarRatio >= 1.5}
                />
              )}
            </>
          )}

          {/* Kesme donatısı */}
          {vRebar != null && (
            <Row label="Kesme Donatısı" value={`${vRebar.toFixed(1)} mm²/m`} />
          )}

          {/* Donatı yeterlilik göstergesi */}
          {rebarRatio != null && (
            <div style={{
              marginTop: "6px",
              padding: "4px 8px",
              borderRadius: "4px",
              fontSize: "10px",
              fontWeight: "600",
              background: rebarRatio >= 1.0 ? "#22c55e15" : "#ef444415",
              color: rebarRatio >= 1.0 ? "#22c55e" : "#ef4444",
              border: `1px solid ${rebarRatio >= 1.0 ? "#22c55e33" : "#ef444433"}`,
            }}>
              {rebarRatio >= 1.5
                ? "✓ Donatı yeterli — güvenli bölge"
                : rebarRatio >= 1.0
                ? "✓ Donatı yeterli — minimum sınırda"
                : "✗ Donatı yetersiz — minimum altında"}
            </div>
          )}
        </div>
      )}

      {/* ─── Analiz Sonuçları ─── */}
      <div style={{ padding: "10px 16px", borderBottom: "1px solid #1e273840" }}>
        <div style={sectionTitleStyle}>ANALİZ SONUÇLARI</div>
        <Row label="Unity Check (D/C)" value={uc != null ? uc.toFixed(3) : "-"} highlight={uc != null && uc >= 1.0} />
        <Row label="Göçme Modu" value={failureModeLabel} />
        <Row label="Yük Kombinasyonu" value={element.governing_combo || "-"} />
        <Row label="Eşleşme Skoru" value={element.match_score?.toFixed(2) ?? "-"} />
      </div>

      {/* ─── Konum ─── */}
      <div style={{ padding: "10px 16px" }}>
        <div style={sectionTitleStyle}>KONUM</div>
        <Row label="Kat" value={element.ifc_story || "-"} />
        <Row label="X" value={element.x != null ? `${element.x.toFixed(2)} m` : "-"} />
        <Row label="Y" value={element.y != null ? `${element.y.toFixed(2)} m` : "-"} />
        <Row label="Z" value={element.z != null ? `${element.z.toFixed(2)} m` : "-"} />
      </div>
    </div>
  );
}

// ─── Stiller ───
const sectionTitleStyle = {
  fontSize: "10px",
  fontWeight: "700",
  color: "#5b9cf6",
  letterSpacing: "1.5px",
  textTransform: "uppercase",
  marginBottom: "6px",
  fontFamily: "monospace",
};

const sectionLabelStyle = {
  fontSize: "10px",
  color: "#4a5c7a",
  letterSpacing: "1px",
  textTransform: "uppercase",
};

function Row({ label, value, highlight, good }) {
  let color = "#d8e4f8";
  if (highlight) color = "#ef4444";
  else if (good) color = "#22c55e";

  return (
    <div style={{
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      padding: "4px 0",
    }}>
      <span style={{ fontSize: "11px", color: "#4a5c7a" }}>{label}</span>
      <span style={{
        fontSize: "11px",
        color: color,
        fontFamily: "monospace",
        fontWeight: (highlight || good) ? "700" : "400",
        maxWidth: "170px",
        textAlign: "right",
        overflow: "hidden",
        textOverflow: "ellipsis",
        whiteSpace: "nowrap",
      }}>
        {value}
      </span>
    </div>
  );
}
