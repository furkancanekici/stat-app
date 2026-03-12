import { create } from "zustand";

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

  // UI
  step: 1,
  loading: false,
  error: null,
  enrichedIFC: null,

  // Actions
  setFiles: (ifcFile, excelFile) => set({
    ifcFile,
    excelFile,
    step: excelFile ? 3 : 1,   // Excel yüklendi → viewer açılabilir
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
    step: 1,
    loading: false,
    error: null,
    enrichedIFC: null,
  }),
}));

export default useAppStore;
