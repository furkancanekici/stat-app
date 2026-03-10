import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import useAppStore from "../store/useAppStore";
import IFCScene from "../components/viewer/IFCScene";
import DetailPanel from "../components/viewer/DetailPanel";
import { getSummary, enrichIFC } from "../services/api";
import { STATUS_COLORS, STATUS_LABELS } from "../utils/colorPalette";

export default function ViewerPage() {
  const navigate = useNavigate();
  const {
    ifcFile, excelFile, elements, setElements,
    selectedElement, setSelectedElement,
    activeStory, setActiveStory,
    statusFilter, setStatusFilter,
    setSummary, setEnrichedIFC,
    loading, setLoading, setError,
  } = useAppStore();

  const [stories, setStories] = useState([]);
  const [enriching, setEnriching] = useState(false);

  useEffect(() => {
    if (!ifcFile || !excelFile) return;
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const summary = await getSummary(ifcFile, excelFile);
      setSummary(summary);

      // Story listesi
      const storyList = summary.by_story.map((s) => s.story);
      setStories(storyList);

      // Elements mock — gerçek IFC parse sonrası buraya gelecek
      // Şimdilik summary'den türetiyoruz
      setElements(summary.by_story.flatMap((s) =>
        Array.from({ length: s.total }, (_, i) => ({
          ifc_global_id: `${s.story}_${i}`,
          ifc_name: `Eleman ${i + 1}`,
          ifc_type: "IfcBeam",
          ifc_story: s.story,
          status: i < s.fail ? "FAIL" : i < s.fail + s.warning ? "WARNING" : "OK",
          match_score: 0.9,
          unity_check: i < s.fail ? 1.2 : 0.7,
        }))
      ));
    } catch (err) {
      setError("Veri yüklenemedi.");
    } finally {
      setLoading(false);
    }
  };

  const handleEnrich = async () => {
    setEnriching(true);
    try {
      const blob = await enrichIFC(ifcFile, excelFile);
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

        {/* Status filtreler */}
        <div style={{ display: "flex", gap: "6px" }}>
          {Object.entries(STATUS_COLORS).map(([status, color]) => (
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
              {STATUS_LABELS[status]}
            </button>
          ))}
        </div>

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
      </div>
    </div>
  );
}