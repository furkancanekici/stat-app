import { useState } from "react";
import { useNavigate } from "react-router-dom";
import useAppStore from "../store/useAppStore";
import DropZone from "../components/upload/DropZone";
import { validateFiles, matchPreview } from "../services/api";

export default function UploadPage() {
  const navigate = useNavigate();
  const {
    ifcFile, excelFile,
    setFiles, setMatchResult, setElements,
    setStep, setLoading, setError,
    loading, error,
  } = useAppStore();

  const [validationResult, setValidationResult] = useState(null);

  const handleAnalyze = async () => {
    if (!ifcFile || !excelFile) {
      setError("Lütfen her iki dosyayı da yükleyin.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Validate
      const validation = await validateFiles(ifcFile, excelFile);
      setValidationResult(validation);

      // Match preview
      const match = await matchPreview(ifcFile, excelFile);
      setMatchResult(match);
      setStep(2);
    } catch (err) {
      setError(err.response?.data?.detail || "Bir hata oluştu.");
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = () => {
    setStep(3);
    navigate("/viewer");
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: "#080b10",
      padding: "80px 32px 32px",
      color: "#d8e4f8",
    }}>
      <div style={{ maxWidth: "640px", margin: "0 auto" }}>

        {/* Başlık */}
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
        <h1 style={{ fontSize: "24px", fontWeight: "800", marginBottom: "6px" }}>
          Dosyaları Yükle
        </h1>
        <p style={{ fontSize: "13px", color: "#7090b8", marginBottom: "32px" }}>
          ETABS / SAP2000'den alınan IFC ve Excel çıktılarını yükleyin.
        </p>

        {/* Drop zones */}
        <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginBottom: "24px" }}>
          <DropZone
            label="IFC Dosyası (.ifc)"
            accept=".ifc"
            file={ifcFile}
            onFile={(f) => setFiles(f, excelFile)}
            color="#5b9cf6"
          />
          <DropZone
            label="Excel Sonuç Dosyası (.xlsx)"
            accept=".xlsx,.xls"
            file={excelFile}
            onFile={(f) => setFiles(ifcFile, f)}
            color="#34d474"
          />
        </div>

        {/* Hata */}
        {error && (
          <div style={{
            background: "#300a0a",
            border: "1px solid #f06060",
            borderRadius: "8px",
            padding: "12px 16px",
            fontSize: "13px",
            color: "#f06060",
            marginBottom: "16px",
          }}>
            ⚠ {error}
          </div>
        )}

        {/* Validasyon sonucu */}
        {validationResult && !error && (
          <div style={{
            background: "#0a2818",
            border: "1px solid #34d474",
            borderRadius: "8px",
            padding: "16px",
            marginBottom: "16px",
            fontSize: "13px",
          }}>
            <div style={{ color: "#34d474", fontWeight: "700", marginBottom: "10px" }}>
              ✓ Dosyalar okundu
            </div>
            <div style={{ color: "#7090b8", display: "flex", gap: "24px" }}>
              <span>IFC Eleman: <strong style={{ color: "#d8e4f8" }}>{validationResult.ifc_elements}</strong></span>
              <span>Excel Satır: <strong style={{ color: "#d8e4f8" }}>{validationResult.excel_rows}</strong></span>
              <span>Versiyon: <strong style={{ color: "#d8e4f8" }}>{validationResult.ifc_version}</strong></span>
            </div>
          </div>
        )}

        {/* Match preview sonucu */}
        {useAppStore.getState().matchResult && !error && (
          <div style={{
            background: "#0f1a2e",
            border: "1px solid #2a3650",
            borderRadius: "8px",
            padding: "16px",
            marginBottom: "24px",
            fontSize: "13px",
          }}>
            <div style={{ color: "#5b9cf6", fontWeight: "700", marginBottom: "10px" }}>
              Eşleştirme Önizlemesi
            </div>
            <div style={{ color: "#7090b8", display: "flex", gap: "24px" }}>
              <span>Eşleşen: <strong style={{ color: "#34d474" }}>{useAppStore.getState().matchResult.matched}</strong></span>
              <span>Eşleşmeyen: <strong style={{ color: "#f06060" }}>{useAppStore.getState().matchResult.unmatched}</strong></span>
              <span>Düşük güven: <strong style={{ color: "#f0c040" }}>{useAppStore.getState().matchResult.low_confidence?.length}</strong></span>
            </div>
          </div>
        )}

        {/* Butonlar */}
        {!useAppStore.getState().matchResult ? (
          <button
            onClick={handleAnalyze}
            disabled={loading || !ifcFile || !excelFile}
            style={{
              width: "100%",
              padding: "14px",
              background: loading ? "#1e2738" : "#5b9cf6",
              border: "none",
              borderRadius: "8px",
              fontSize: "14px",
              fontWeight: "700",
              color: loading ? "#4a5c7a" : "#fff",
              cursor: loading || !ifcFile || !excelFile ? "not-allowed" : "pointer",
              letterSpacing: "1px",
            }}
          >
            {loading ? "Analiz ediliyor..." : "Analiz Et"}
          </button>
        ) : (
          <button
            onClick={handleConfirm}
            style={{
              width: "100%",
              padding: "14px",
              background: "#34d474",
              border: "none",
              borderRadius: "8px",
              fontSize: "14px",
              fontWeight: "700",
              color: "#080b10",
              cursor: "pointer",
              letterSpacing: "1px",
            }}
          >
            Viewer'a Geç →
          </button>
        )}
      </div>
    </div>
  );
}