import { create } from "zustand";

const DEFAULT_STATUS_COLORS = {
  OK:        "#22c55e",
  WARNING:   "#eab308",
  FAIL:      "#ef4444",
  BRITTLE:   "#f97316",
  UNMATCHED: "#64748b",
};

const useAppStore = create((set) => ({
  // Dosyalar
  ifcFile: null,
  excelFile: null,
  ifcVersion: null,

  // Analiz
  matchResult: null,
  elements: [],
  summary: null,

  // Viewer
  selectedElement: null,
  activeStory: "ALL",
  statusFilter: ["OK", "WARNING", "FAIL", "BRITTLE", "UNMATCHED"],

  // Görünüm
  bgColor: "#080b10",
  statusColors: { ...DEFAULT_STATUS_COLORS },

  // UI
  step: 1,
  loading: false,
  error: null,
  enrichedIFC: null,

  // Actions
  setFiles: (ifcFile, excelFile) => set({
    ifcFile,
    excelFile,
    step: excelFile ? 3 : 1,
  }),
  setIfcVersion: (ifcVersion) => set({ ifcVersion }),
  setMatchResult: (matchResult) => set({ matchResult }),
  setElements: (elements) => set({ elements }),
  setSummary: (summary) => set({ summary }),
  setSelectedElement: (selectedElement) => set({ selectedElement }),
  setActiveStory: (activeStory) => set({ activeStory }),
  setStatusFilter: (statusFilter) => set({ statusFilter }),
  setStep: (step) => set({ step }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  setEnrichedIFC: (enrichedIFC) => set({ enrichedIFC }),
  setBgColor: (bgColor) => set({ bgColor }),
  setStatusColor: (status, color) => set((state) => ({
    statusColors: { ...state.statusColors, [status]: color },
  })),
  resetStatusColors: () => set({ statusColors: { ...DEFAULT_STATUS_COLORS } }),

  reset: () => set({
    ifcFile: null,
    excelFile: null,
    ifcVersion: null,
    matchResult: null,
    elements: [],
    summary: null,
    selectedElement: null,
    activeStory: "ALL",
    statusFilter: ["OK", "WARNING", "FAIL", "BRITTLE", "UNMATCHED"],
    bgColor: "#080b10",
    statusColors: { ...DEFAULT_STATUS_COLORS },
    step: 1,
    loading: false,
    error: null,
    enrichedIFC: null,
  }),
}));

export default useAppStore;
