import * as XLSX from "xlsx";

export function parseExcel(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target.result);
        const workbook = XLSX.read(data, { type: "array" });
        const sheetName = workbook.SheetNames[0];
        const sheet = workbook.Sheets[sheetName];
        const rows = XLSX.utils.sheet_to_json(sheet);
        resolve(rows);
      } catch (err) {
        reject(err);
      }
    };

    reader.onerror = () => reject(new Error("Dosya okunamadı"));
    reader.readAsArrayBuffer(file);
  });
}

export function validateColumns(rows) {
  if (!rows || rows.length === 0) {
    return ["Dosya boş"];
  }

  const required = ["ElementLabel", "UnityCheck"];
  const cols = Object.keys(rows[0]);
  const missing = required.filter((r) => !cols.includes(r));
  return missing;
}