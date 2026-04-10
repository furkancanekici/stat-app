import axios from "axios";

const BASE_URL = "http://127.0.0.1:8000/api";

const api = axios.create({ baseURL: BASE_URL });

export async function checkHealth() {
  const res = await api.get("/health");
  return res.data;
}

export async function validateFiles(ifcFile, excelFile) {
  const form = new FormData();
  form.append("excel_file", excelFile);
  const res = await api.post("/validate", form);
  return res.data;
}

export async function enrichIFC(ifcFile, excelFile) {
  const form = new FormData();
  form.append("excel_file", excelFile);
  const res = await api.post("/enrich", form, {
    responseType: "blob",
  });
  return res.data;
}

export async function getSummary(ifcFile, excelFile) {
  const form = new FormData();
  form.append("excel_file", excelFile);
  const res = await api.post("/summary", form);
  return res.data;
}

export async function compareRevisions(oldFile, newFile) {
  const form = new FormData();
  form.append("old_file", oldFile);
  form.append("new_file", newFile);
  const res = await api.post("/compare", form);
  return res.data;
}

// ─── ETABS API ───

export async function checkEtabsStatus() {
  const res = await api.get("/etabs/status");
  return res.data;
}

export async function analyzeFromEtabs(modelPath = null, skipAnalysis = false, skipDesign = false) {
  const params = new URLSearchParams();
  if (modelPath) params.append("model_path", modelPath);
  if (skipAnalysis) params.append("skip_analysis", "true");
  if (skipDesign) params.append("skip_design", "true");
  const res = await api.post(`/etabs/analyze?${params.toString()}`);
  return res.data;
}

export async function exportEtabsExcel(modelPath = null, skipAnalysis = false, skipDesign = false) {
  const params = new URLSearchParams();
  if (modelPath) params.append("model_path", modelPath);
  if (skipAnalysis) params.append("skip_analysis", "true");
  if (skipDesign) params.append("skip_design", "true");
  const res = await api.post(`/etabs/export?${params.toString()}`, null, {
    responseType: "blob",
  });
  return res.data;
}
