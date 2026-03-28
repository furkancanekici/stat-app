import { useState } from "react";
import { useNavigate } from "react-router-dom";
import useAppStore from "../store/useAppStore";
import DropZone from "../components/upload/DropZone";
import { validateFiles } from "../services/api";

export default function UploadPage() {
  const navigate = useNavigate();
  const { setFiles, setElements, setSummary, setError } = useAppStore();
  const [excelFile, setLocalExcel] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setLocalError] = useState("");
  const [showGuide, setShowGuide] = useState(false);

  const handleAnalyze = async () => {
    if (!excelFile) { setLocalError("Excel dosyası seçiniz."); return; }
    setLoading(true);
    setLocalError("");
    try {
      const data = await validateFiles(null, excelFile);
      setResult(data);
      setFiles(null, excelFile);
      const { getSummary } = await import("../services/api");
      const summary = await getSummary(null, excelFile);
      setSummary(summary);
      setElements(summary.elements || []);
      navigate("/viewer");
    } catch (err) {
      const backendMsg = err.response?.data?.detail;
      setLocalError(backendMsg || err.message || "Bir hata oluştu.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: "100vh", background: "#080b10",
      display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
      padding: "80px 24px 48px", color: "#d8e4f8",
    }}>
      <div style={{ width: "100%", maxWidth: "560px" }}>
        <div style={{ fontFamily: "monospace", fontSize: "11px", color: "#5b9cf6", letterSpacing: "3px", textTransform: "uppercase", marginBottom: "8px" }}>
          Adım 1
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
          <h1 style={{ fontSize: "24px", fontWeight: "800", margin: 0 }}>Dosyayı Yükle</h1>
          <button onClick={() => setShowGuide(!showGuide)} style={{
            width: "28px", height: "28px", borderRadius: "50%",
            background: showGuide ? "#5b9cf6" : "transparent", border: "2px solid #5b9cf6",
            color: showGuide ? "#fff" : "#5b9cf6", fontSize: "14px", fontWeight: "800",
            cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
          }} title="ETABS'tan nasıl export alınır?">?</button>
        </div>
        <p style={{ fontSize: "13px", color: "#7090b8", marginBottom: showGuide ? "16px" : "32px" }}>
          ETABS'tan alınan Excel çıktısını yükleyin.
        </p>

        {showGuide && (
          <div style={{ marginBottom: "24px", background: "#0c1018", border: "1px solid #1e2738", borderRadius: "10px", overflow: "hidden" }}>
            <div style={{ padding: "12px 16px", borderBottom: "1px solid #1e2738", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "12px", fontWeight: "700", color: "#5b9cf6", fontFamily: "monospace", letterSpacing: "1px" }}>ETABS EXPORT YÖNERGESİ</span>
              <button onClick={() => setShowGuide(false)} style={{ background: "none", border: "none", color: "#4a5c7a", fontSize: "18px", cursor: "pointer" }}>×</button>
            </div>
            <div style={{ padding: "14px 16px" }}>
              <Step n="1" title="Tabloları Aç">
                ETABS'ta üst menüden <Code>Display → Show Tables</Code> veya <Code>File → Export → Tables to Excel</Code> yolunu izleyin.
              </Step>
              <Step n="2" title="Gerekli Tabloları Seç">
                <div style={{ fontSize: "11px", color: "#7090b8", marginBottom: "8px" }}>Açılan pencerede aşağıdaki tabloları seçin:</div>
                <TableTag label="Design — Concrete Col/Beam Sum" sub="Tasarım sonuçları, donatı miktarları" required />
                <TableTag label="Connectivity — Point/Beam/Column Bays" sub="3D geometri ve bağlantı verileri" required />
                <TableTag label="Frame Prop — Summary" sub="Gerçek kesit boyutları (R33, R22)" required />
                <TableTag label="Conc Jt Sum — TS 500" sub="Birleşim bölgesi kontrolü (BC/JS Ratio)" required />
                <TableTag label="Story Drifts" sub="Göreli kat ötelemesi (δi/hi)" recommended />
                <TableTag label="Diaphragm Max Over Avg Drifts" sub="Burulma düzensizliği kontrolü (ηbi)" recommended />
                <TableTag label="Element Forces — Beams/Columns" sub="Kesme kuvvetleri (Vd) — kesme kontrolü" recommended />
                <TableTag label="Material Property Definitions" sub="Beton (fck) ve donatı (fyk) dayanımları" recommended />
                <TableTag label="Auto Seismic — TSC 2018" sub="R, D, I katsayıları, deprem parametreleri" recommended />
                <TableTag label="Load Pattern Definitions" sub="Yük tanımları ve tipleri" optional />
              </Step>
              <Step n="3" title="Excel Olarak Export Et">
                Seçili tabloları <Code>Export to Excel</Code> butonuyla tek bir <Code>.xlsx</Code> dosyasına kaydedin.
              </Step>
              <Step n="4" title="Buraya Yükle">
                Kaydedilen Excel dosyasını aşağıdaki alana sürükleyip bırakın.
              </Step>
              <div style={{ marginTop: "12px", padding: "10px 12px", background: "#111620", borderRadius: "6px", borderLeft: "3px solid #eab308" }}>
                <div style={{ fontSize: "10px", color: "#eab308", fontWeight: "700", letterSpacing: "1px", marginBottom: "4px" }}>BİLGİ</div>
                <div style={{ fontSize: "11px", color: "#7090b8", lineHeight: "1.5" }}>
                  Zorunlu tablolar olmadan uygulama çalışmaz. Önerilen tablolar eklenirse kat ötelemesi, burulma düzensizliği, kesme kapasitesi ve gerçek malzeme dayanımları ile analiz yapılır. Opsiyonel tablolar ek bilgi sağlar.
                </div>
              </div>
            </div>
          </div>
        )}

        <DropZone label="Excel Dosyası (.xlsx)" accept=".xlsx" file={excelFile} onFile={setLocalExcel} />

        {error && (
          <div style={{ marginTop: "12px", padding: "10px 14px", background: "#300a0a", border: "1px solid #f0606033", borderRadius: "8px", color: "#f06060", fontSize: "13px" }}>
            ⚠ {error}
          </div>
        )}
        {result && (
          <div style={{ marginTop: "12px", padding: "10px 14px", background: "#0a1e0a", border: "1px solid #22c55e33", borderRadius: "8px", color: "#22c55e", fontSize: "12px", fontFamily: "monospace" }}>
            ✓ Dosya okundu — {result.beams} kiriş, {result.columns} kolon, {result.points} nokta
          </div>
        )}

        <button onClick={handleAnalyze} disabled={loading || !excelFile} style={{
          marginTop: "24px", width: "100%", padding: "14px",
          background: loading || !excelFile ? "#1e2738" : "#5b9cf6",
          border: "none", borderRadius: "10px",
          color: loading || !excelFile ? "#4a5c7a" : "#fff",
          fontSize: "14px", fontWeight: "800", cursor: loading || !excelFile ? "not-allowed" : "pointer",
          letterSpacing: "2px", textTransform: "uppercase",
        }}>
          {loading ? "Analiz ediliyor..." : "Analiz Et →"}
        </button>
      </div>
    </div>
  );
}

// ─── Yardımcılar ───

function Step({ n, title, children }) {
  return (
    <div style={{ marginBottom: "16px" }}>
      <div style={{ fontSize: "12px", fontWeight: "700", color: "#d8e4f8", marginBottom: "4px" }}>{n}. {title}</div>
      <div style={{ fontSize: "11px", color: "#7090b8", lineHeight: "1.6" }}>{children}</div>
    </div>
  );
}

function Code({ children }) {
  return <span style={{ fontFamily: "monospace", fontSize: "10px", background: "#1e2738", padding: "1px 6px", borderRadius: "3px", color: "#5b9cf6" }}>{children}</span>;
}

function TableTag({ label, sub, required, recommended, optional }) {
  const color = required ? "#22c55e" : recommended ? "#5b9cf6" : "#4a5c7a";
  const tag = required ? "ZORUNLU" : recommended ? "ÖNERİLEN" : "OPSİYONEL";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "8px", padding: "6px 10px", background: "#111620", borderRadius: "5px", borderLeft: `3px solid ${color}`, marginBottom: "4px" }}>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: "11px", fontWeight: "700", color: "#d8e4f8" }}>{label}</div>
        <div style={{ fontSize: "10px", color: "#4a5c7a" }}>{sub}</div>
      </div>
      <span style={{ fontSize: "9px", padding: "2px 6px", borderRadius: "3px", background: `${color}22`, color, fontWeight: "700", letterSpacing: "0.5px", flexShrink: 0 }}>{tag}</span>
    </div>
  );
}
