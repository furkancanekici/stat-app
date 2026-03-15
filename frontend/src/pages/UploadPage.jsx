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
    if (!excelFile) {
      setLocalError("Excel dosyası seçiniz.");
      return;
    }
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
      minHeight: "100vh",
      background: "#080b10",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      padding: "80px 24px 48px",
      color: "#d8e4f8",
    }}>
      <div style={{ width: "100%", maxWidth: "560px" }}>
        <div style={{
          fontFamily: "monospace",
          fontSize: "11px",
          color: "#5b9cf6",
          letterSpacing: "3px",
          textTransform: "uppercase",
          marginBottom: "8px",
        }}>
          Adım 1
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
          <h1 style={{ fontSize: "24px", fontWeight: "800", margin: 0 }}>
            Dosyayı Yükle
          </h1>
          <button
            onClick={() => setShowGuide(!showGuide)}
            style={{
              width: "28px",
              height: "28px",
              borderRadius: "50%",
              background: showGuide ? "#5b9cf6" : "transparent",
              border: "2px solid #5b9cf6",
              color: showGuide ? "#fff" : "#5b9cf6",
              fontSize: "14px",
              fontWeight: "800",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
            title="ETABS'tan nasıl export alınır?"
          >
            ?
          </button>
        </div>

        <p style={{ fontSize: "13px", color: "#7090b8", marginBottom: showGuide ? "16px" : "32px" }}>
          ETABS'tan alınan Excel çıktısını yükleyin.
        </p>

        {/* ─── ETABS Yönergesi ─── */}
        {showGuide && (
          <div style={{
            marginBottom: "24px",
            background: "#0c1018",
            border: "1px solid #1e2738",
            borderRadius: "10px",
            overflow: "hidden",
          }}>
            <div style={{
              padding: "12px 16px",
              borderBottom: "1px solid #1e2738",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}>
              <span style={{
                fontSize: "12px",
                fontWeight: "700",
                color: "#5b9cf6",
                fontFamily: "monospace",
                letterSpacing: "1px",
              }}>
                ETABS EXPORT YÖNERGESİ
              </span>
              <button
                onClick={() => setShowGuide(false)}
                style={{ background: "none", border: "none", color: "#4a5c7a", fontSize: "18px", cursor: "pointer" }}
              >
                ×
              </button>
            </div>

            <div style={{ padding: "14px 16px" }}>
              {/* Adım 1 */}
              <div style={{ marginBottom: "16px" }}>
                <div style={stepTitleStyle}>1. Tabloları Aç</div>
                <div style={stepDescStyle}>
                  ETABS'ta üst menüden <Code>Display → Show Tables</Code> veya <Code>File → Export → Tables to Excel</Code> yolunu izleyin.
                </div>
              </div>

              {/* Adım 2 */}
              <div style={{ marginBottom: "16px" }}>
                <div style={stepTitleStyle}>2. Gerekli Tabloları Seç</div>
                <div style={stepDescStyle}>
                  Açılan pencerede aşağıdaki tabloları seçin:
                </div>
                <div style={{ marginTop: "8px", display: "flex", flexDirection: "column", gap: "4px" }}>
                  <TableTag label="Design" sub="Steel Frame Summary veya Concrete Column/Beam Summary" required />
                  <TableTag label="Connectivity" sub="Point Bays, Beam Bays, Column Bays" required />
                  <TableTag label="Sections" sub="Frame Section Property Definitions - Summary" recommended />
                </div>
              </div>

              {/* Adım 3 */}
              <div style={{ marginBottom: "16px" }}>
                <div style={stepTitleStyle}>3. Excel Olarak Export Et</div>
                <div style={stepDescStyle}>
                  Seçili tabloları <Code>Export to Excel</Code> butonuyla tek bir <Code>.xlsx</Code> dosyasına kaydedin. Her tablo ayrı bir sheet olarak oluşacaktır.
                </div>
              </div>

              {/* Adım 4 */}
              <div style={{ marginBottom: "8px" }}>
                <div style={stepTitleStyle}>4. Buraya Yükle</div>
                <div style={stepDescStyle}>
                  Kaydedilen Excel dosyasını aşağıdaki alana sürükleyip bırakın veya tıklayarak seçin.
                </div>
              </div>

              {/* Minimum gereksinim notu */}
              <div style={{
                marginTop: "12px",
                padding: "10px 12px",
                background: "#111620",
                borderRadius: "6px",
                borderLeft: "3px solid #eab308",
              }}>
                <div style={{ fontSize: "10px", color: "#eab308", fontWeight: "700", letterSpacing: "1px", marginBottom: "4px" }}>
                  MİNİMUM GEREKSİNİM
                </div>
                <div style={{ fontSize: "11px", color: "#7090b8", lineHeight: "1.5" }}>
                  Tasarım sonuçları (Steel/Concrete Summary) + Bağlantı verileri (Point, Beam, Column Bays) zorunludur.
                  Kesit özellikleri (Frame Section Properties) eklenirse 3D görselleştirmede gerçek boyutlar kullanılır.
                </div>
              </div>
            </div>
          </div>
        )}

        <DropZone
          label="Excel Dosyası (.xlsx)"
          accept=".xlsx"
          file={excelFile}
          onFile={setLocalExcel}
        />

        {error && (
          <div style={{
            marginTop: "12px",
            padding: "10px 14px",
            background: "#300a0a",
            border: "1px solid #f0606033",
            borderRadius: "8px",
            color: "#f06060",
            fontSize: "13px",
          }}>
            ⚠ {error}
          </div>
        )}

        {result && (
          <div style={{
            marginTop: "12px",
            padding: "10px 14px",
            background: "#0a1e0a",
            border: "1px solid #22c55e33",
            borderRadius: "8px",
            color: "#22c55e",
            fontSize: "12px",
            fontFamily: "monospace",
          }}>
            ✓ Dosya okundu — {result.beams} kiriş, {result.columns} kolon, {result.points} nokta
          </div>
        )}

        <button
          onClick={handleAnalyze}
          disabled={loading || !excelFile}
          style={{
            marginTop: "24px",
            width: "100%",
            padding: "14px",
            background: loading || !excelFile ? "#1e2738" : "#5b9cf6",
            border: "none",
            borderRadius: "10px",
            color: loading || !excelFile ? "#4a5c7a" : "#fff",
            fontSize: "14px",
            fontWeight: "800",
            cursor: loading || !excelFile ? "not-allowed" : "pointer",
            letterSpacing: "2px",
            textTransform: "uppercase",
          }}
        >
          {loading ? "Analiz ediliyor..." : "Analiz Et →"}
        </button>
      </div>
    </div>
  );
}

// ─── Yardımcı bileşenler ───

const stepTitleStyle = {
  fontSize: "12px",
  fontWeight: "700",
  color: "#d8e4f8",
  marginBottom: "4px",
};

const stepDescStyle = {
  fontSize: "11px",
  color: "#7090b8",
  lineHeight: "1.6",
};

function Code({ children }) {
  return (
    <span style={{
      fontFamily: "monospace",
      fontSize: "10px",
      background: "#1e2738",
      padding: "1px 6px",
      borderRadius: "3px",
      color: "#5b9cf6",
    }}>
      {children}
    </span>
  );
}

function TableTag({ label, sub, required, recommended }) {
  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      gap: "8px",
      padding: "6px 10px",
      background: "#111620",
      borderRadius: "5px",
      borderLeft: `3px solid ${required ? "#22c55e" : "#5b9cf6"}`,
    }}>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: "11px", fontWeight: "700", color: "#d8e4f8" }}>{label}</div>
        <div style={{ fontSize: "10px", color: "#4a5c7a" }}>{sub}</div>
      </div>
      <span style={{
        fontSize: "9px",
        padding: "2px 6px",
        borderRadius: "3px",
        background: required ? "#22c55e22" : "#5b9cf622",
        color: required ? "#22c55e" : "#5b9cf6",
        fontWeight: "700",
        letterSpacing: "0.5px",
      }}>
        {required ? "ZORUNLU" : "ÖNERİLEN"}
      </span>
    </div>
  );
}
