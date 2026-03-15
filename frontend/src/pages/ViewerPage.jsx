import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import useAppStore from "../store/useAppStore";
import IFCScene from "../components/viewer/IFCScene";
import DetailPanel from "../components/viewer/DetailPanel";
import { getSummary, enrichIFC } from "../services/api";
import { STATUS_LABELS } from "../utils/colorPalette";

export default function ViewerPage() {
  const navigate = useNavigate();
  const {
    excelFile, elements, setElements,
    selectedElement, setSelectedElement,
    activeStory, setActiveStory,
    statusFilter, setStatusFilter,
    setSummary, setEnrichedIFC,
    loading, setLoading, setError,
    bgColor, setBgColor,
    statusColors, setStatusColor, resetStatusColors,
  } = useAppStore();

  const [stories, setStories] = useState([]);
  const [enriching, setEnriching] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  useEffect(() => {
    if (!excelFile) return;
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const summary = await getSummary(null, excelFile);
      setSummary(summary);
      const storyList = summary.by_story.map((s) => s.story);
      setStories(storyList);
      setElements(summary.elements || []);
    } catch (err) {
      setError("Veri yüklenemedi.");
    } finally {
      setLoading(false);
    }
  };

  const handleEnrich = async () => {
    setEnriching(true);
    try {
      const blob = await enrichIFC(null, excelFile);
      setEnrichedIFC(blob);
      navigate("/report");
    } catch (err) {
      setError("Enrichment başarısız.");
    } finally {
      setEnriching(false);
    }
  };

  const selectedEl = elements.find((e) => e.ifc_global_id === selectedElement);

  const toggleStatus = (status) => {
    if (statusFilter.includes(status)) {
      setStatusFilter(statusFilter.filter((s) => s !== status));
    } else {
      setStatusFilter([...statusFilter, status]);
    }
  };

  return (
    <div style={{
      height: "100vh",
      background: "#080b10",
      display: "flex",
      flexDirection: "column",
      paddingTop: "52px",
    }}>
      {/* Toolbar */}
      <div style={{
        height: "48px",
        background: "#0c1018",
        borderBottom: "1px solid #1e2738",
        display: "flex",
        alignItems: "center",
        padding: "0 16px",
        gap: "12px",
        flexShrink: 0,
      }}>
        {/* Story filtre */}
        <select
          value={activeStory}
          onChange={(e) => setActiveStory(e.target.value)}
          style={{
            background: "#111620",
            border: "1px solid #2a3650",
            borderRadius: "6px",
            color: "#d8e4f8",
            padding: "4px 10px",
            fontSize: "12px",
          }}
        >
          <option value="ALL">Tüm Katlar</option>
          {stories.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        {/* Status filtreler — store'daki renklerle */}
        <div style={{ display: "flex", gap: "6px" }}>
          {Object.entries(statusColors).map(([status, color]) => (
            <button
              key={status}
              onClick={() => toggleStatus(status)}
              style={{
                padding: "3px 10px",
                borderRadius: "4px",
                border: `1px solid ${color}55`,
                background: statusFilter.includes(status) ? color + "22" : "transparent",
                color: statusFilter.includes(status) ? color : "#2a3650",
                fontSize: "11px",
                fontWeight: "700",
                cursor: "pointer",
                letterSpacing: "1px",
              }}
            >
              {STATUS_LABELS[status] || status}
            </button>
          ))}
        </div>

        {/* Ayarlar butonu */}
        <button
          onClick={() => setShowSettings(!showSettings)}
          style={{
            padding: "5px 12px",
            background: showSettings ? "#1e2738" : "transparent",
            border: "1px solid #2a3650",
            borderRadius: "6px",
            color: "#7090b8",
            fontSize: "14px",
            cursor: "pointer",
          }}
          title="Görünüm Ayarları"
        >
          ⚙
        </button>

        {/* Enrich butonu */}
        <button
          onClick={handleEnrich}
          disabled={enriching}
          style={{
            marginLeft: "auto",
            padding: "6px 18px",
            background: enriching ? "#1e2738" : "#5b9cf6",
            border: "none",
            borderRadius: "6px",
            color: enriching ? "#4a5c7a" : "#fff",
            fontSize: "12px",
            fontWeight: "700",
            cursor: enriching ? "not-allowed" : "pointer",
            letterSpacing: "1px",
          }}
        >
          {enriching ? "İşleniyor..." : "IFC Zenginleştir →"}
        </button>
      </div>

      {/* 3D Sahne */}
      <div style={{ flex: 1, position: "relative" }}>
        <IFCScene onElementClick={setSelectedElement} />

        {selectedEl && (
          <DetailPanel
            element={selectedEl}
            onClose={() => setSelectedElement(null)}
          />
        )}

        {/* Ayarlar Paneli */}
        {showSettings && (
          <div style={{
            position: "absolute",
            top: "12px",
            left: "12px",
            width: "240px",
            background: "#0c1018ee",
            border: "1px solid #1e2738",
            borderRadius: "10px",
            zIndex: 100,
            overflow: "hidden",
          }}>
            {/* Panel Başlık */}
            <div style={{
              padding: "10px 14px",
              borderBottom: "1px solid #1e2738",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}>
              <span style={{ fontSize: "12px", fontWeight: "700", color: "#5b9cf6", letterSpacing: "1px" }}>
                GÖRÜNÜM
              </span>
              <button
                onClick={() => setShowSettings(false)}
                style={{ background: "none", border: "none", color: "#4a5c7a", fontSize: "16px", cursor: "pointer" }}
              >
                ×
              </button>
            </div>

            <div style={{ padding: "12px 14px" }}>
              {/* Arka plan rengi */}
              <div style={{ marginBottom: "14px" }}>
                <label style={{ fontSize: "10px", color: "#4a5c7a", letterSpacing: "1px", textTransform: "uppercase", display: "block", marginBottom: "6px" }}>
                  Arka Plan
                </label>
                <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                  {["#080b10", "#0d1117", "#1a1a2e", "#16213e", "#1b1b1b", "#ffffff", "#f0f0f0", "#2d3436"].map((c) => (
                    <div
                      key={c}
                      onClick={() => setBgColor(c)}
                      style={{
                        width: "26px",
                        height: "26px",
                        borderRadius: "4px",
                        background: c,
                        border: bgColor === c ? "2px solid #5b9cf6" : "1px solid #2a3650",
                        cursor: "pointer",
                      }}
                    />
                  ))}
                  <input
                    type="color"
                    value={bgColor}
                    onChange={(e) => setBgColor(e.target.value)}
                    style={{ width: "26px", height: "26px", border: "none", padding: 0, cursor: "pointer", borderRadius: "4px" }}
                    title="Özel renk"
                  />
                </div>
              </div>

              {/* Status renkleri */}
              <div style={{ marginBottom: "10px" }}>
                <label style={{ fontSize: "10px", color: "#4a5c7a", letterSpacing: "1px", textTransform: "uppercase", display: "block", marginBottom: "6px" }}>
                  Durum Renkleri
                </label>
                {Object.entries(statusColors).map(([status, color]) => (
                  <div key={status} style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "5px" }}>
                    <input
                      type="color"
                      value={color}
                      onChange={(e) => setStatusColor(status, e.target.value)}
                      style={{ width: "22px", height: "22px", border: "none", padding: 0, cursor: "pointer", borderRadius: "3px" }}
                    />
                    <span style={{ fontSize: "11px", color: "#d8e4f8", flex: 1 }}>
                      {STATUS_LABELS[status] || status}
                    </span>
                    <span style={{ fontSize: "9px", color: "#4a5c7a", fontFamily: "monospace" }}>
                      {color}
                    </span>
                  </div>
                ))}
              </div>

              {/* Sıfırla butonu */}
              <button
                onClick={resetStatusColors}
                style={{
                  width: "100%",
                  padding: "6px",
                  background: "transparent",
                  border: "1px solid #2a3650",
                  borderRadius: "5px",
                  color: "#4a5c7a",
                  fontSize: "10px",
                  cursor: "pointer",
                  letterSpacing: "1px",
                }}
              >
                Renkleri Sıfırla
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
