export const STATUS_COLORS = {
  OK:        "#22c55e",
  WARNING:   "#eab308",
  FAIL:      "#ef4444",
  BRITTLE:   "#f97316",
  UNMATCHED: "#64748b",
};

export const STATUS_LABELS = {
  OK:        "Yeterli",
  WARNING:   "Sınırda",
  FAIL:      "Yetersiz",
  BRITTLE:   "Gevrek",
  UNMATCHED: "Eşleşmedi",
};

export function getColor(status) {
  return STATUS_COLORS[status] ?? STATUS_COLORS.UNMATCHED;
}

export function getLabel(status) {
  return STATUS_LABELS[status] ?? "Bilinmiyor";
}

export function hexToRgb(hex) {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? {
    r: parseInt(result[1], 16) / 255,
    g: parseInt(result[2], 16) / 255,
    b: parseInt(result[3], 16) / 255,
  } : { r: 0.4, g: 0.4, b: 0.4 };
}
