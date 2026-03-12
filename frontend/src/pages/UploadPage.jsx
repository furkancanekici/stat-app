import { useState } from "react";
import { useNavigate } from "react-router-dom";
import useAppStore from "../store/useAppStore";
import DropZone from "../components/upload/DropZone";
import { validateFiles, getSummary } from "../services/api";

export default function UploadPage() {
  const navigate = useNavigate();
  const { setFiles, setElements, setSummary, setError } = useAppStore();
  const [excelFile, setLocalExcel] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setLocalError] = useState("");

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

      // Summary al
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
        <h1 style={{ fontSize: "24px", fontWeight: "800", marginBottom: "6px" }}>
          Dosyayı Yükle
        </h1>
        <p style={{ fontSize: "13px", color: "#7090b8", marginBottom: "32px" }}>
          ETABS'tan alınan Excel çıktısını yükleyin.
        </p>

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