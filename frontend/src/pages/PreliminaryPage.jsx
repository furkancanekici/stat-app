import { useState } from "react";
import { useNavigate } from "react-router-dom";
import useAppStore from "../store/useAppStore";
import { designPreliminary, designPreliminaryFast } from "../services/api";

/**
 * PreliminaryPage — STAT Ön Tasarım
 * Rule-based preliminary design: TBDY 2018 + TS 500 + asmolen döşeme
 */
export default function PreliminaryPage() {
  const navigate = useNavigate();
  const { setElements } = useAppStore();

  const [form, setForm] = useState({
    Lx: 18, Ly: 24, story_count: 8, story_height_m: 3.0,
    il: "Istanbul", ilce: "Kadikoy",
    soil_class: "ZC", usage: "residential",
    core_required: true, material_auto: true,
    fck: 30, fyk: 420,
  });
  const [fastMode, setFastMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const update = (key, val) => setForm((f) => ({ ...f, [key]: val }));

  const handleSubmit = async () => {
    setLoading(true); setError(""); setResult(null);
    const payload = {
      Lx: form.Lx, Ly: form.Ly,
      story_count: form.story_count,
      story_height_m: form.story_height_m,
      location: { il: form.il, ilce: form.ilce },
      soil_class: form.soil_class,
      usage: form.usage,
      core: { required: form.core_required },
    };
    if (!form.material_auto) {
      payload.material = { fck: form.fck, fyk: form.fyk };
    }
    try {
      const fn = fastMode ? designPreliminaryFast : designPreliminary;
      const data = await fn(payload);
      setResult(data);
      if (data.elements && data.elements.length > 0) {
        setElements(data.elements);
      }
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || "Bilinmeyen hata.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: "100vh", background: "#080b10",
      display: "flex", flexDirection: "column", alignItems: "center",
      padding: "80px 24px 48px", color: "#d8e4f8",
    }}>
      <div style={{ width: "100%", maxWidth: "720px" }}>
        <div style={{
          fontFamily: "monospace", fontSize: "11px", color: "#5b9cf6",
          letterSpacing: "3px", textTransform: "uppercase", marginBottom: "8px"
        }}>
          Ön Tasarım
        </div>
        <h1 style={{ fontSize: "24px", fontWeight: "800", margin: "0 0 6px 0" }}>
          Rule-Based Preliminary Design
        </h1>
        <p style={{ fontSize: "13px", color: "#7090b8", marginBottom: "24px" }}>
          TBDY 2018 + TS 500 + asmolen döşeme. Kat sayısına göre otomatik kesit ve malzeme.
        </p>

        <Section title="Geometri">
          <Row>
            <Field label="Lx (m)" value={form.Lx} onChange={(v) => update("Lx", parseFloat(v))} type="number" step="1" min="8" max="60" />
            <Field label="Ly (m)" value={form.Ly} onChange={(v) => update("Ly", parseFloat(v))} type="number" step="1" min="8" max="60" />
          </Row>
          <Row>
            <Field label="Kat Sayısı" value={form.story_count} onChange={(v) => update("story_count", parseInt(v))} type="number" step="1" min="1" max="30" />
            <Field label="Kat Yüksekliği (m)" value={form.story_height_m} onChange={(v) => update("story_height_m", parseFloat(v))} type="number" step="0.1" min="2.5" max="5" />
          </Row>
        </Section>

        <Section title="Konum & Zemin">
          <Row>
            <Field label="İl" value={form.il} onChange={(v) => update("il", v)} />
            <Field label="İlçe" value={form.ilce} onChange={(v) => update("ilce", v)} />
          </Row>
          <Row>
            <Select label="Zemin Sınıfı" value={form.soil_class} onChange={(v) => update("soil_class", v)}
              options={["ZA", "ZB", "ZC", "ZD", "ZE"]} />
            <Select label="Kullanım" value={form.usage} onChange={(v) => update("usage", v)}
              options={[{ v: "residential", l: "Konut" }, { v: "storage", l: "Depo" }]} />
          </Row>
        </Section>

        <Section title="Malzeme">
          <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", color: "#d8e4f8", marginBottom: "12px", cursor: "pointer" }}>
            <input type="checkbox" checked={form.material_auto} onChange={(e) => update("material_auto", e.target.checked)} style={{ accentColor: "#5b9cf6" }} />
            <span>Kat sayısına göre otomatik seç</span>
          </label>
          {form.material_auto ? (
            <div style={{ padding: "12px 14px", background: "#111620", borderRadius: "6px", borderLeft: "3px solid #5b9cf6" }}>
              <div style={{ fontSize: "10px", color: "#5b9cf6", fontWeight: "700", letterSpacing: "1px", marginBottom: "6px" }}>
                OTOMATİK SEÇİM
              </div>
              <div style={{ fontSize: "12px", color: "#d8e4f8" }}>
                {autoMaterialLabel(form.story_count)}
              </div>
            </div>
          ) : (
            <Row>
              <Field label="fck (MPa)" value={form.fck} onChange={(v) => update("fck", parseFloat(v))} type="number" step="5" min="25" max="50" />
              <Field label="fyk (MPa)" value={form.fyk} onChange={(v) => update("fyk", parseFloat(v))} type="number" step="10" min="400" max="500" />
            </Row>
          )}
        </Section>

        <Section title="Çekirdek">
          <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", color: "#d8e4f8", cursor: "pointer" }}>
            <input type="checkbox" checked={form.core_required} onChange={(e) => update("core_required", e.target.checked)} style={{ accentColor: "#5b9cf6" }} />
            <span>Asansör çekirdeği otomatik yerleştir (U-perde, merkez civarı)</span>
          </label>
        </Section>

        <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12px", color: "#7090b8", marginBottom: "16px", cursor: "pointer" }}>
          <input type="checkbox" checked={fastMode} onChange={(e) => setFastMode(e.target.checked)} style={{ accentColor: "#5b9cf6" }} />
          <span>Hızlı mod (modal analizi atla — sadece geometrik optimizasyon)</span>
        </label>

        <button onClick={handleSubmit} disabled={loading} style={btnStyle(loading)}>
          {loading ? "Tasarlanıyor..." : "Ön Tasarımı Üret →"}
        </button>

        {error && (
          <div style={{
            marginTop: "16px", padding: "10px 14px", background: "#300a0a",
            border: "1px solid #f0606033", borderRadius: "8px", color: "#f06060", fontSize: "13px"
          }}>
            ⚠ {error}
          </div>
        )}

        {result && <ResultPanel result={result} onView3D={() => navigate("/viewer")} elementCount={result.elements?.length || 0} />}
      </div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div style={{ marginBottom: "20px" }}>
      <div style={{ fontSize: "11px", fontWeight: "700", color: "#5b9cf6", letterSpacing: "2px", textTransform: "uppercase", marginBottom: "10px" }}>
        {title}
      </div>
      <div style={{ padding: "16px", background: "#0c1018", border: "1px solid #1e2738", borderRadius: "10px" }}>
        {children}
      </div>
    </div>
  );
}

function Row({ children }) {
  return <div style={{ display: "flex", gap: "12px", marginBottom: "10px" }}>{children}</div>;
}

function Field({ label, value, onChange, type = "text", step, min, max }) {
  return (
    <div style={{ flex: 1 }}>
      <label style={{ display: "block", fontSize: "10px", color: "#7090b8", letterSpacing: "1px", textTransform: "uppercase", marginBottom: "4px", fontWeight: "700" }}>
        {label}
      </label>
      <input type={type} value={value} step={step} min={min} max={max}
        onChange={(e) => onChange(e.target.value)}
        style={{
          width: "100%", padding: "8px 10px", background: "#080b10",
          border: "1px solid #2a3650", borderRadius: "6px",
          color: "#d8e4f8", fontSize: "13px",
          fontFamily: type === "number" ? "monospace" : "inherit",
          outline: "none", boxSizing: "border-box",
        }} />
    </div>
  );
}

function Select({ label, value, onChange, options }) {
  return (
    <div style={{ flex: 1 }}>
      <label style={{ display: "block", fontSize: "10px", color: "#7090b8", letterSpacing: "1px", textTransform: "uppercase", marginBottom: "4px", fontWeight: "700" }}>
        {label}
      </label>
      <select value={value} onChange={(e) => onChange(e.target.value)}
        style={{
          width: "100%", padding: "8px 10px", background: "#080b10",
          border: "1px solid #2a3650", borderRadius: "6px",
          color: "#d8e4f8", fontSize: "13px", outline: "none", boxSizing: "border-box", cursor: "pointer",
        }}>
        {options.map((o) =>
          typeof o === "string"
            ? <option key={o} value={o}>{o}</option>
            : <option key={o.v} value={o.v}>{o.l}</option>
        )}
      </select>
    </div>
  );
}

function btnStyle(disabled) {
  return {
    width: "100%", padding: "14px",
    background: disabled ? "#1e2738" : "#5b9cf6",
    border: "none", borderRadius: "10px",
    color: disabled ? "#4a5c7a" : "#fff",
    fontSize: "14px", fontWeight: "800",
    cursor: disabled ? "not-allowed" : "pointer",
    letterSpacing: "2px", textTransform: "uppercase",
  };
}

function autoMaterialLabel(story_count) {
  if (story_count <= 5) return "≤ 5 kat → C25 beton, B420C donatı";
  if (story_count <= 10) return "6-10 kat → C30 beton, B420C donatı";
  if (story_count <= 15) return "11-15 kat → C35 beton, B420C donatı";
  return "15+ kat → C40 beton, B500C donatı";
}

function ResultPanel({ result, onView3D, elementCount }) {
  const design = result.design;
  const m = design.modal_result;
  const Afloor = design.input.Lx * design.input.Ly;
  return (
    <div style={{ marginTop: "24px" }}>
      <div style={{ fontSize: "11px", fontWeight: "700", color: "#5b9cf6", letterSpacing: "2px", textTransform: "uppercase", marginBottom: "10px" }}>
        Sonuç
      </div>
      <div style={{
        padding: "12px 16px", borderRadius: "10px", marginBottom: "16px",
        background: design.success ? "#0a2a15" : "#3a2a0a",
        border: `1px solid ${design.success ? "#22c55e33" : "#f59e0b33"}`,
        color: design.success ? "#22c55e" : "#f59e0b",
        fontSize: "13px", fontWeight: "700",
      }}>
        {design.success ? "✓ Tasarım başarılı" : "⚠ Tasarım üretildi (uyarılar var)"}
      </div>

      <button onClick={onView3D} style={{
        width: "100%", padding: "12px",
        background: "#22c55e",
        border: "none", borderRadius: "10px",
        color: "#fff",
        fontSize: "13px", fontWeight: "800",
        cursor: "pointer",
        letterSpacing: "2px", textTransform: "uppercase",
        marginBottom: "16px",
      }}>
        🧊 3D Görselleştiricide Aç ({elementCount} eleman) →
      </button>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "10px", marginBottom: "16px" }}>
        <Metric label="Grid" value={`${design.grid.x_axes.length}×${design.grid.y_axes.length} aks`} />
        <Metric label="Plan Alanı" value={`${Afloor.toFixed(0)} m²`} />
        <Metric label="Kolon" value={design.columns.length} />
        <Metric label="Kiriş" value={design.beams.length} />
        <Metric label="Perde" value={design.walls.length} />
        <Metric label="Döşeme" value={`${design.slabs[0]?.total_thickness_cm || "-"} cm asmolen`} />
        <Metric label="Çekirdek" value={design.core ? `${design.core.width_m}×${design.core.length_m} m` : "Yok"} />
        <Metric label="Beton Hacmi" value={`${design.total_concrete_volume_m3.toFixed(0)} m³`} />
        <Metric label="Perde %X" value={`${(design.total_wall_area_ratio_x * 100).toFixed(2)} %`}
          highlight={design.total_wall_area_ratio_x < 0.02} />
        <Metric label="Perde %Y" value={`${(design.total_wall_area_ratio_y * 100).toFixed(2)} %`}
          highlight={design.total_wall_area_ratio_y < 0.02} />
      </div>

      {m && (
        <div style={{ marginBottom: "16px" }}>
          <div style={{ fontSize: "11px", fontWeight: "700", color: "#5b9cf6", letterSpacing: "2px", textTransform: "uppercase", marginBottom: "10px" }}>
            Modal Analiz (OpenSeesPy)
          </div>
          <div style={{ padding: "16px", background: "#0c1018", border: "1px solid #1e2738", borderRadius: "10px" }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "10px", marginBottom: "12px" }}>
              <MiniStat label="T1" value={`${m.period_1_s.toFixed(3)} s`} />
              <MiniStat label="T2" value={`${m.period_2_s.toFixed(3)} s`} />
              <MiniStat label="T3" value={`${m.period_3_s.toFixed(3)} s`} />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "10px" }}>
              <MiniStat label="ηbi X" value={m.eta_bi_x.toFixed(3)} highlight={m.eta_bi_x >= 1.2} />
              <MiniStat label="ηbi Y" value={m.eta_bi_y.toFixed(3)} highlight={m.eta_bi_y >= 1.2} />
              <MiniStat label="Burulma" value={m.passes_torsion_check ? "✓ Geçti" : "✗ Kaldı"}
                highlight={!m.passes_torsion_check} />
            </div>
          </div>
        </div>
      )}

      {design.warnings.length > 0 && (
        <div>
          <div style={{ fontSize: "11px", fontWeight: "700", color: "#5b9cf6", letterSpacing: "2px", textTransform: "uppercase", marginBottom: "10px" }}>
            Uyarılar ({design.warnings.length})
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            {design.warnings.map((w, i) => <WarningCard key={i} w={w} />)}
          </div>
        </div>
      )}
    </div>
  );
}

function Metric({ label, value, highlight }) {
  return (
    <div style={{
      padding: "12px 14px", background: "#0c1018",
      border: `1px solid ${highlight ? "#f0606033" : "#1e2738"}`, borderRadius: "8px",
    }}>
      <div style={{ fontSize: "10px", color: "#4a5c7a", letterSpacing: "1px", textTransform: "uppercase", marginBottom: "4px" }}>
        {label}
      </div>
      <div style={{ fontSize: "15px", fontWeight: "700", color: highlight ? "#f06060" : "#d8e4f8" }}>
        {value}
      </div>
    </div>
  );
}

function MiniStat({ label, value, highlight }) {
  return (
    <div style={{ textAlign: "center" }}>
      <div style={{ fontSize: "9px", color: "#4a5c7a", letterSpacing: "1px", textTransform: "uppercase", marginBottom: "4px" }}>
        {label}
      </div>
      <div style={{ fontSize: "16px", fontWeight: "800", color: highlight ? "#f06060" : "#5b9cf6", fontFamily: "monospace" }}>
        {value}
      </div>
    </div>
  );
}

function WarningCard({ w }) {
  const palette = {
    error: { bg: "#300a0a", border: "#f0606033", color: "#f06060" },
    warning: { bg: "#3a2a0a", border: "#f59e0b33", color: "#f59e0b" },
    info: { bg: "#0c1820", border: "#5b9cf633", color: "#5b9cf6" },
  };
  const p = palette[w.severity] || palette.info;
  return (
    <div style={{
      padding: "10px 14px", background: p.bg, border: `1px solid ${p.border}`,
      borderRadius: "8px", fontSize: "12px",
    }}>
      <div style={{ fontWeight: "700", fontSize: "10px", letterSpacing: "1px", textTransform: "uppercase", marginBottom: "2px", color: p.color, opacity: 0.9 }}>
        {w.rule}
      </div>
      <div style={{ color: "#d8e4f8", fontSize: "12px" }}>
        {w.message}
      </div>
    </div>
  );
}
