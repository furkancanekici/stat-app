import StatusBadge from "../shared/StatusBadge";
import useAppStore from "../../store/useAppStore";

export default function DetailPanel({ element, onClose }) {
  if (!element) return null;

  const { statusColors } = useAppStore();
  const sc = statusColors[element.status] || "#64748b";

  const uc = element.unity_check;
  const capPct = uc != null ? Math.min(Math.round(uc * 100), 200) : null;
  const barColor = (p) => p == null ? "#64748b" : p < 90 ? (statusColors.OK || "#22c55e") : p < 100 ? (statusColors.WARNING || "#eab308") : (statusColors.FAIL || "#ef4444");

  const secD = element.sec_depth, secW = element.sec_width;
  const sizeStr = (secD && secW) ? `${(secD*100).toFixed(0)} × ${(secW*100).toFixed(0)} cm` : element.excel_section || "-";
  const areaStr = (secD && secW) ? `${(secD*secW*10000).toFixed(0)} cm²` : "-";
  const typeStr = element.ifc_type === "IfcBeam" ? "Kiriş" : element.ifc_type === "IfcColumn" ? "Kolon" : element.ifc_type;

  const fmMap = { "Moment": "Eğilme (Sünek)", "Shear": "Kesme (Gevrek)", "PMM": "Eksenel + Eğilme", "Overstressed": "Aşırı Gerilme" };
  const fmLabel = fmMap[element.failure_mode] || element.failure_mode || "-";

  const isBeam = element.ifc_type === "IfcBeam";
  const isCol = element.ifc_type === "IfcColumn";
  const hasRebar = element.as_total != null || element.as_top != null;
  const warnings = element.warnings || [];

  return (
    <div style={{
      position: "absolute", top: "12px", right: "12px", width: "300px",
      background: "#0c1018ee", border: "1px solid #1e2738", borderRadius: "12px",
      zIndex: 100, overflow: "hidden", backdropFilter: "blur(8px)",
      maxHeight: "calc(100vh - 140px)", overflowY: "auto",
    }}>
      {/* Header */}
      <div style={{ padding: "14px 16px", borderBottom: `2px solid ${sc}44`, background: `${sc}08` }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div style={{ fontSize: "16px", fontWeight: "800", color: "#fff", marginBottom: "2px" }}>{element.ifc_name}</div>
            <div style={{ fontSize: "11px", color: "#7090b8", marginBottom: "6px" }}>{typeStr} · {element.ifc_story || "-"} · {element.excel_section || "-"}</div>
            <StatusBadge status={element.status} />
          </div>
          <button onClick={onClose} style={{ background: "transparent", border: "none", color: "#4a5c7a", fontSize: "20px", cursor: "pointer" }}>×</button>
        </div>
      </div>

      {/* Kapasite */}
      {capPct != null && (
        <Sec borderless>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "6px" }}>
            <span style={lblS}>Kapasite Kullanımı</span>
            <span style={{ fontSize: "20px", fontWeight: "800", fontFamily: "monospace", color: barColor(capPct) }}>%{capPct}</span>
          </div>
          <div style={{ width: "100%", height: "8px", background: "#111620", borderRadius: "4px", overflow: "hidden" }}>
            <div style={{ width: `${Math.min(capPct,100)}%`, height: "100%", background: barColor(capPct), borderRadius: "4px", transition: "width 0.3s" }} />
          </div>
          {capPct >= 100 && <div style={{ fontSize: "9px", color: "#ef4444", marginTop: "4px", fontWeight: "600" }}>⚠ Kapasite aşımı — %{capPct-100} fazla</div>}
        </Sec>
      )}

      {/* Kesit */}
      <Sec title="KESİT ÖZELLİKLERİ">
        <Row l="Kesit Adı" v={element.excel_section || "-"} />
        <Row l="Boyut" v={sizeStr} />
        <Row l="Kesit Alanı" v={areaStr} />
        {element.material_concrete && <Row l="Beton" v={element.material_concrete} />}
        {element.material_rebar && <Row l="Donatı Çeliği" v={element.material_rebar} />}
      </Sec>

      {/* Donatı */}
      {hasRebar && (
        <Sec title="DONATI BİLGİLERİ">
          {isCol && element.as_total != null && <>
            <Row l="Mevcut (As)" v={`${element.as_total.toFixed(0)} mm²`} />
            {element.as_min != null && <Row l="Minimum (As,min)" v={`${element.as_min.toFixed(0)} mm²`} />}
            {element.rebar_ratio != null && <Row l="Oran (As/As,min)" v={`${element.rebar_ratio.toFixed(2)}x`} hi={element.rebar_ratio<1} ok={element.rebar_ratio>=1.5} />}
          </>}
          {isBeam && <>
            {element.as_top != null && <Row l="Üst (As,üst)" v={`${element.as_top.toFixed(0)} mm²`} />}
            {element.as_bot != null && <Row l="Alt (As,alt)" v={`${element.as_bot.toFixed(0)} mm²`} />}
            {element.rebar_ratio != null && <Row l="Oran (As/As,min)" v={`${element.rebar_ratio.toFixed(2)}x`} hi={element.rebar_ratio<1} ok={element.rebar_ratio>=1.5} />}
          </>}
          {element.v_rebar != null && <Row l="Kesme Donatısı" v={`${element.v_rebar.toFixed(1)} mm²/m`} />}
          {element.rho != null && (
            <div style={{ marginTop: "6px", padding: "6px 8px", background: "#111620", borderRadius: "5px", fontSize: "10px", fontFamily: "monospace" }}>
              <div style={{ color: "#7090b8", marginBottom: "2px" }}>TS 500 Donatı Oranı</div>
              <div style={{ color: "#d8e4f8" }}>ρ = {(element.rho*100).toFixed(2)}% <span style={{ color: "#4a5c7a" }}>(min: {(element.rho_min*100).toFixed(2)}% — max: {(element.rho_max*100).toFixed(1)}%)</span></div>
              <Tag status={element.rho_status} ok="✓ Donatı oranı uygun" fail={element.rho_status === "MIN_FAIL" ? "✗ Minimum altında" : "✗ Maksimum aşıldı"} />
            </div>
          )}
        </Sec>
      )}

      {/* Birleşim Bölgesi */}
      {isCol && element.bc_ratio_maj != null && (
        <Sec title="BİRLEŞİM BÖLGESİ (TBDY 7.3)">
          <Row l="BC Ratio (Majör)" v={element.bc_ratio_maj?.toFixed(3)} hi={element.bc_status==="FAIL"} ok={element.bc_status==="OK"} />
          <Row l="BC Ratio (Minör)" v={element.bc_ratio_min?.toFixed(3) ?? "-"} />
          <Row l="JS Ratio (Majör)" v={element.js_ratio_maj?.toFixed(3) ?? "-"} hi={element.js_status==="FAIL"} />
          <Tag status={element.bc_status} ok="✓ Güçlü kolon sağlanıyor" warn="◐ Sınırda (>0.833)" fail="✗ Zayıf kolon — TBDY ihlali" />
        </Sec>
      )}

      {/* Kat Ötelemesi */}
      {element.drift_value != null && (
        <Sec title="KAT ÖTELEMESİ (TBDY 4.9)">
          <Row l="δi/hi" v={element.drift_value?.toFixed(5)} hi={element.drift_status==="FAIL"} ok={element.drift_status==="OK"} />
          <Row l="Sınır Değer" v={element.drift_limit?.toString()} />
          <Tag status={element.drift_status} ok="✓ Öteleme sınır içinde" warn="◐ Sınıra yakın" fail="✗ Kat ötelemesi aşıldı" />
        </Sec>
      )}

      {/* Burulma Düzensizliği */}
      {element.torsion_ratio != null && (
        <Sec title="BURULMA DÜZENSİZLİĞİ (TBDY 3.6)">
          <Row l="ηbi" v={element.torsion_ratio?.toFixed(3)} hi={element.torsion_status==="FAIL"} ok={element.torsion_status==="OK"} />
          <Row l="Sınır" v="1.200" />
          <Tag status={element.torsion_status} ok="✓ Düzensizlik yok" warn="◐ A1b düzensizliği" fail="✗ Ağır burulma düzensizliği" />
        </Sec>
      )}

      {/* Kesme Talebi */}
      {element.vd != null && (
        <Sec title="KESME KONTROLÜ (TS 500)">
          <Row l="Kesme Talebi (Vd)" v={`${element.vd?.toFixed(0)} kN`} />
          <Row l="Beton Kapasitesi (Vr)" v={`${element.vr_approx?.toFixed(0)} kN`} />
          <Row l="Vr/Vd Oranı" v={element.vr_vd_ratio?.toFixed(2)} hi={element.vr_vd_status==="FAIL"} ok={element.vr_vd_status==="OK"} />
          <Tag status={element.vr_vd_status} ok="✓ Beton kapasitesi yeterli" warn="◐ Kesme talebi yüksek" fail="✗ Beton kapasitesi yetersiz — donatı gerekli" />
        </Sec>
      )}

      {/* Analiz Sonuçları */}
      <Sec title="ANALİZ SONUÇLARI">
        <Row l="Unity Check (D/C)" v={uc != null ? uc.toFixed(3) : "-"} hi={uc != null && uc >= 1.0} />
        <Row l="Göçme Modu" v={fmLabel} />
        <Row l="Yük Kombinasyonu" v={element.governing_combo || "-"} />
        {element.ductility_level && element.ductility_level !== "unknown" && (
          <Row l="Süneklik Düzeyi" v={element.ductility_level === "high" ? "Yüksek (R≥6)" : "Sınırlı"} />
        )}
        {element.seismic_R && <Row l="R Katsayısı" v={element.seismic_R} />}
        {element.seismic_SDS && <Row l="SDS" v={element.seismic_SDS} />}
      </Sec>

      {/* Uyarılar */}
      {warnings.length > 0 && (
        <Sec title={`UYARILAR (${warnings.length})`}>
          {warnings.map((w, i) => (
            <div key={i} style={{
              fontSize: "10px", color: "#f0c040", background: "#f0c04010",
              border: "1px solid #f0c04033", borderRadius: "4px",
              padding: "5px 8px", marginBottom: "4px", lineHeight: "1.4",
            }}>⚠ {w}</div>
          ))}
        </Sec>
      )}

      {/* Konum */}
      <Sec title="KONUM" last>
        <Row l="Kat" v={element.ifc_story || "-"} />
        <Row l="X" v={element.x != null ? `${element.x.toFixed(2)} m` : "-"} />
        <Row l="Y" v={element.y != null ? `${element.y.toFixed(2)} m` : "-"} />
        <Row l="Z" v={element.z != null ? `${element.z.toFixed(2)} m` : "-"} />
      </Sec>
    </div>
  );
}

// ─── Yardımcılar ───

const lblS = { fontSize: "10px", color: "#4a5c7a", letterSpacing: "1px", textTransform: "uppercase" };

function Sec({ title, children, last, borderless }) {
  return (
    <div style={{ padding: "10px 16px", borderBottom: last ? "none" : "1px solid #1e273840" }}>
      {title && <div style={{ fontSize: "10px", fontWeight: "700", color: "#5b9cf6", letterSpacing: "1.5px", textTransform: "uppercase", marginBottom: "6px", fontFamily: "monospace" }}>{title}</div>}
      {children}
    </div>
  );
}

function Row({ l, v, hi, ok }) {
  let c = "#d8e4f8";
  if (hi) c = "#ef4444";
  else if (ok) c = "#22c55e";
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "4px 0" }}>
      <span style={{ fontSize: "11px", color: "#4a5c7a" }}>{l}</span>
      <span style={{ fontSize: "11px", color: c, fontFamily: "monospace", fontWeight: (hi||ok) ? "700" : "400", maxWidth: "170px", textAlign: "right", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{v ?? "-"}</span>
    </div>
  );
}

function Tag({ status, ok, warn, fail }) {
  if (!status || status === "OK" && !ok) return null;
  const isOk = status === "OK", isFail = status === "FAIL" || status === "CRITICAL" || status === "MIN_FAIL" || status === "MAX_FAIL";
  const text = isFail ? fail : isOk ? ok : (warn || "");
  if (!text) return null;
  return (
    <div style={{
      marginTop: "4px", padding: "4px 8px", borderRadius: "4px", fontSize: "10px", fontWeight: "600",
      background: isFail ? "#ef444415" : isOk ? "#22c55e15" : "#eab30815",
      color: isFail ? "#ef4444" : isOk ? "#22c55e" : "#eab308",
      border: `1px solid ${isFail ? "#ef444433" : isOk ? "#22c55e33" : "#eab30833"}`,
    }}>{text}</div>
  );
}
