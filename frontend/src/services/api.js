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