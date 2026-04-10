import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import useAppStore from "../store/useAppStore";
import DropZone from "../components/upload/DropZone";
import { validateFiles, checkEtabsStatus } from "../services/api";

export default function UploadPage() {
  const navigate = useNavigate();
  const { setFiles, setElements, setSummary } = useAppStore();
  const [excelFile, setLocalExcel] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setLocalError] = useState("");
  const [showGuide, setShowGuide] = useState(false);

  // ETABS state
  const [activeTab, setActiveTab] = useState("excel");
  const [etabsStatus, setEtabsStatus] = useState(null);
  const [etabsChecking, setEtabsChecking] = useState(false);
  const [modelPath, setModelPath] = useState("");
  const [skipAnalysis, setSkipAnalysis] = useState(false);
  const [skipDesign, setSkipDesign] = useState(false);
  const [etabsProgress, setEtabsProgress] = useState("");

  useEffect(() => { checkEtabs(); }, []);

  const checkEtabs = async () => {
    setEtabsChecking(true);
    try {
      const status = await checkEtabsStatus();
      setEtabsStatus(status);
    } catch {
      setEtabsStatus({ available: false, message: "Backend'e bağlanılamadı.", model_open: false, model_name: "" });
    } finally {
      setEtabsChecking(false);
    }
  };

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

  const handleEtabsAnalyze = async () => {
    setLoading(true);
    setLocalError("");
    setEtabsProgress("ETABS'a bağlanılıyor...");
    try {
      // 1) ETABS'tan Excel'i indir
      setEtabsProgress("Tablolar çekiliyor...");
      const { exportEtabsExcel } = await import("../services/api");
      const blob = await exportEtabsExcel(
        modelPath || null,
        skipAnalysis,
        skipDesign
      );

      // 2) Blob'u File nesnesine çevir
      const excelFile = new File([blob], "etabs_export.xlsx", {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      });

      // 3) Aynı mevcut pipeline'ı kullan (Excel yükle ile aynı)
      setEtabsProgress("Analiz ediliyor...");
      await validateFiles(null, excelFile);
      setFiles(null, excelFile);
      const { getSummary } = await import("../services/api");
      const summary = await getSummary(null, excelFile);
      setSummary(summary);
      setElements(summary.elements || []);

      // 4) Dosyayı bilgisayara da kaydet (opsiyonel)
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = modelPath
        ? modelPath.split("\\").pop().replace(".EDB", "_tables.xlsx")
        : "etabs_export.xlsx";
      a.click();
      URL.revokeObjectURL(url);

      navigate("/viewer");
    } catch (err) {
      const backendMsg = err.response?.data?.detail;
      setLocalError(backendMsg || err.message || "ETABS bağlantı hatası.");
    } finally {
      setLoading(false);
      setEtabsProgress("");
    }
  };

  const tabStyle = (tab) => ({
    flex: 1, padding: "12px", textAlign: "center", cursor: "pointer",
    fontSize: "13px", fontWeight: "700", letterSpacing: "1px",
    background: activeTab === tab ? "#111820" : "transparent",
    color: activeTab === tab ? "#5b9cf6" : "#4a5c7a",
    borderBottom: activeTab === tab ? "2px solid #5b9cf6" : "2px solid transparent",
    transition: "all 0.2s",
  });

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
        <h1 style={{ fontSize: "24px", fontWeight: "800", margin: "0 0 6px 0" }}>Veri Kaynağı</h1>
        <p style={{ fontSize: "13px", color: "#7090b8", marginBottom: "24px" }}>
          Excel dosyası yükleyin veya ETABS'tan doğrudan çekin.
        </p>

        {/* Tab Seçici */}
        <div style={{ display: "flex", borderBottom: "1px solid #1e2738", marginBottom: "24px" }}>
          <div style={tabStyle("excel")} onClick={() => setActiveTab("excel")}>
            📁 Excel Yükle
          </div>
          <div style={tabStyle("etabs")} onClick={() => setActiveTab("etabs")}>
            🔗 ETABS'tan Çek
            {etabsStatus?.available && (
              <span style={{ display: "inline-block", width: "6px", height: "6px", borderRadius: "50%", background: "#22c55e", marginLeft: "6px", verticalAlign: "middle" }} />
            )}
          </div>
        </div>

        {/* Excel Tab */}
        {activeTab === "excel" && (
          <>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "16px" }}>
              <span style={{ fontSize: "14px", fontWeight: "700" }}>Excel Dosyası</span>
              <button onClick={() => setShowGuide(!showGuide)} style={{
                width: "24px", height: "24px", borderRadius: "50%",
                background: showGuide ? "#5b9cf6" : "transparent", border: "2px solid #5b9cf6",
                color: showGuide ? "#fff" : "#5b9cf6", fontSize: "12px", fontWeight: "800",
                cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
              }} title="ETABS'tan nasıl export alınır?">?</button>
            </div>

            {showGuide && <ExportGuide onClose={() => setShowGuide(false)} />}

            <DropZone label="Excel Dosyası (.xlsx)" accept=".xlsx" file={excelFile} onFile={setLocalExcel} />

            {result && (
              <div style={{ marginTop: "12px", padding: "10px 14px", background: "#0a1e0a", border: "1px solid #22c55e33", borderRadius: "8px", color: "#22c55e", fontSize: "12px", fontFamily: "monospace" }}>
                ✓ Dosya okundu — {result.beams} kiriş, {result.columns} kolon, {result.points} nokta
              </div>
            )}

            <button onClick={handleAnalyze} disabled={loading || !excelFile} style={btnStyle(loading || !excelFile)}>
              {loading ? "Analiz ediliyor..." : "Analiz Et →"}
            </button>
          </>
        )}

        {/* ETABS Tab */}
        {activeTab === "etabs" && (
          <>
            <div style={{
              padding: "14px 16px", borderRadius: "10px", marginBottom: "20px",
              background: etabsStatus?.available ? "#0a1e0a" : "#1a0a0a",
              border: `1px solid ${etabsStatus?.available ? "#22c55e33" : "#f0606033"}`,
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
                <span style={{
                  width: "8px", height: "8px", borderRadius: "50%",
                  background: etabsChecking ? "#eab308" : etabsStatus?.available ? "#22c55e" : "#ef4444",
                }} />
                <span style={{ fontSize: "12px", fontWeight: "700", color: "#d8e4f8" }}>
                  {etabsChecking ? "Kontrol ediliyor..." : etabsStatus?.available ? "ETABS Bağlantısı Hazır" : "ETABS Erişilemiyor"}
                </span>
                <button onClick={checkEtabs} disabled={etabsChecking} style={{
                  marginLeft: "auto", background: "none", border: "1px solid #2a3650",
                  color: "#5b9cf6", fontSize: "10px", padding: "3px 8px", borderRadius: "4px", cursor: "pointer",
                }}>Yenile</button>
              </div>
              <div style={{ fontSize: "11px", color: "#7090b8" }}>
                {etabsStatus?.message || "Durum kontrol ediliyor..."}
              </div>
              {etabsStatus?.model_open && (
                <div style={{ marginTop: "6px", fontSize: "11px", color: "#22c55e", fontFamily: "monospace" }}>
                  Açık model: {etabsStatus.model_name}
                </div>
              )}
            </div>

            {etabsStatus?.available && (
              <>
                <div style={{ marginBottom: "16px" }}>
                  <label style={{ fontSize: "12px", fontWeight: "700", color: "#7090b8", display: "block", marginBottom: "6px" }}>
                    Model Yolu <span style={{ fontWeight: "400", color: "#4a5c7a" }}>(boş bırakırsan açık modele bağlanır)</span>
                  </label>
                  <input
                    type="text" value={modelPath} onChange={(e) => setModelPath(e.target.value)}
                    placeholder="C:\Projects\Bina1.EDB"
                    style={{
                      width: "100%", padding: "10px 12px", background: "#0c1018",
                      border: "1px solid #2a3650", borderRadius: "8px", color: "#d8e4f8",
                      fontSize: "13px", fontFamily: "monospace", outline: "none", boxSizing: "border-box",
                    }}
                  />
                </div>

                <div style={{ display: "flex", gap: "16px", marginBottom: "20px" }}>
                  <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "#7090b8", cursor: "pointer" }}>
                    <input type="checkbox" checked={skipAnalysis} onChange={(e) => setSkipAnalysis(e.target.checked)} style={{ accentColor: "#5b9cf6" }} />
                    Analizi atla
                  </label>
                  <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "#7090b8", cursor: "pointer" }}>
                    <input type="checkbox" checked={skipDesign} onChange={(e) => setSkipDesign(e.target.checked)} style={{ accentColor: "#5b9cf6" }} />
                    Design'ı atla
                  </label>
                </div>

                {etabsProgress && (
                  <div style={{
                    padding: "10px 14px", background: "#0c1018", border: "1px solid #5b9cf633",
                    borderRadius: "8px", marginBottom: "16px", display: "flex", alignItems: "center", gap: "10px",
                  }}>
                    <div style={{
                      width: "14px", height: "14px", border: "2px solid #5b9cf6",
                      borderTopColor: "transparent", borderRadius: "50%",
                      animation: "spin 0.8s linear infinite",
                    }} />
                    <span style={{ fontSize: "12px", color: "#5b9cf6", fontFamily: "monospace" }}>{etabsProgress}</span>
                    <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
                  </div>
                )}

                <button onClick={handleEtabsAnalyze} disabled={loading} style={btnStyle(loading)}>
                  {loading ? "ETABS'tan çekiliyor..." : "ETABS'tan Analiz Et →"}
                </button>

                <div style={{ marginTop: "12px", padding: "10px 12px", background: "#111620", borderRadius: "6px", borderLeft: "3px solid #5b9cf6" }}>
                  <div style={{ fontSize: "10px", color: "#5b9cf6", fontWeight: "700", letterSpacing: "1px", marginBottom: "4px" }}>BİLGİ</div>
                  <div style={{ fontSize: "11px", color: "#7090b8", lineHeight: "1.5" }}>
                    ETABS bu bilgisayarda kurulu ve çalışır durumda olmalıdır. Script otomatik olarak analizi çalıştırır, Concrete Frame Design yapar ve tüm tabloları çekip STAT analizinden geçirir.
                  </div>
                </div>
              </>
            )}

            {etabsStatus && !etabsStatus.available && (
              <div style={{ textAlign: "center", padding: "32px 16px" }}>
                <div style={{ fontSize: "36px", marginBottom: "12px" }}>🖥️</div>
                <div style={{ fontSize: "13px", color: "#7090b8", marginBottom: "8px" }}>ETABS bu makinede erişilemiyor.</div>
                <div style={{ fontSize: "12px", color: "#4a5c7a" }}>Excel sekmesinden manuel olarak yükleyebilirsiniz.</div>
              </div>
            )}
          </>
        )}

        {error && (
          <div style={{ marginTop: "12px", padding: "10px 14px", background: "#300a0a", border: "1px solid #f0606033", borderRadius: "8px", color: "#f06060", fontSize: "13px" }}>
            ⚠ {error}
          </div>
        )}
      </div>
    </div>
  );
}

function btnStyle(disabled) {
  return {
    marginTop: "24px", width: "100%", padding: "14px",
    background: disabled ? "#1e2738" : "#5b9cf6",
    border: "none", borderRadius: "10px",
    color: disabled ? "#4a5c7a" : "#fff",
    fontSize: "14px", fontWeight: "800", cursor: disabled ? "not-allowed" : "pointer",
    letterSpacing: "2px", textTransform: "uppercase",
  };
}

function ExportGuide({ onClose }) {
  return (
    <div style={{ marginBottom: "24px", background: "#0c1018", border: "1px solid #1e2738", borderRadius: "10px", overflow: "hidden" }}>
      <div style={{ padding: "12px 16px", borderBottom: "1px solid #1e2738", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: "12px", fontWeight: "700", color: "#5b9cf6", fontFamily: "monospace", letterSpacing: "1px" }}>ETABS EXPORT YÖNERGESİ</span>
        <button onClick={onClose} style={{ background: "none", border: "none", color: "#4a5c7a", fontSize: "18px", cursor: "pointer" }}>×</button>
      </div>
      <div style={{ padding: "14px 16px" }}>
        <Step n="1" title="Tabloları Aç">ETABS'ta üst menüden <Code>Display → Show Tables</Code> veya <Code>File → Export → Tables to Excel</Code> yolunu izleyin.</Step>
        <Step n="2" title="Gerekli Tabloları Seç">
          <div style={{ fontSize: "11px", color: "#7090b8", marginBottom: "8px" }}>Açılan pencerede aşağıdaki tabloları seçin:</div>
          <TableTag label="Design — Concrete Col/Beam Sum" sub="Tasarım sonuçları, donatı miktarları" required />
          <TableTag label="Connectivity — Point/Beam/Column Bays" sub="3D geometri ve bağlantı verileri" required />
          <TableTag label="Frame Prop — Summary" sub="Gerçek kesit boyutları (R33, R22)" required />
          <TableTag label="Conc Jt Sum — TS 500" sub="Birleşim bölgesi kontrolü (BC/JS Ratio)" required />
          <TableTag label="Story Drifts" sub="Göreli kat ötelemesi (δi/hi)" recommended />
          <TableTag label="Diaphragm Max Over Avg Drifts" sub="Burulma düzensizliği kontrolü (ηbi)" recommended />
          <TableTag label="Element Forces — Beams/Columns" sub="Kesme kuvvetleri (Vd)" recommended />
          <TableTag label="Material Property Definitions" sub="Beton (fck) ve donatı (fyk) dayanımları" recommended />
          <TableTag label="Auto Seismic — TSC 2018" sub="R, D, I katsayıları" recommended />
          <TableTag label="Load Pattern Definitions" sub="Yük tanımları ve tipleri" optional />
        </Step>
        <Step n="3" title="Excel Olarak Export Et">Seçili tabloları <Code>Export to Excel</Code> ile kaydedin.</Step>
        <Step n="4" title="Buraya Yükle">Excel dosyasını yukarıdaki alana sürükleyip bırakın.</Step>
      </div>
    </div>
  );
}

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

function TableTag({ label, sub, required, recommended }) {
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
