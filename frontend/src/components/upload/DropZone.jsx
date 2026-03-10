import { useRef, useState } from "react";

export default function DropZone({ label, accept, file, onFile, color = "#5b9cf6" }) {
  const inputRef = useRef();
  const [dragging, setDragging] = useState(false);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) onFile(dropped);
  };

  return (
    <div
      onClick={() => inputRef.current.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      style={{
        border: `2px dashed ${dragging ? color : file ? color + "88" : "#2a3650"}`,
        borderRadius: "12px",
        padding: "32px 24px",
        textAlign: "center",
        cursor: "pointer",
        background: dragging ? color + "11" : file ? color + "08" : "#0c1018",
        transition: "all 0.2s",
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        style={{ display: "none" }}
        onChange={(e) => e.target.files[0] && onFile(e.target.files[0])}
      />

      <div style={{ fontSize: "28px", marginBottom: "10px" }}>
        {file ? "✅" : "📁"}
      </div>

      <div style={{
        fontSize: "13px",
        fontWeight: "700",
        color: file ? color : "#7090b8",
        marginBottom: "4px",
      }}>
        {file ? file.name : label}
      </div>

      <div style={{ fontSize: "11px", color: "#4a5c7a" }}>
        {file
          ? `${(file.size / 1024).toFixed(1)} KB`
          : "Tıkla veya sürükle bırak"}
      </div>
    </div>
  );
}