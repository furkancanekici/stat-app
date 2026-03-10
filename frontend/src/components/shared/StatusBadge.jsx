import { getColor, getLabel } from "../../utils/colorPalette";

export default function StatusBadge({ status }) {
  const color = getColor(status);
  const label = getLabel(status);

  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 10px",
        borderRadius: "4px",
        fontSize: "11px",
        fontWeight: "700",
        letterSpacing: "1px",
        backgroundColor: color + "22",
        color: color,
        border: `1px solid ${color}55`,
      }}
    >
      {label}
    </span>
  );
}