import { useState } from "react";

/**
 * ListEditor
 * ------------
 * Componente pequeno e reutilizável para editar listas de texto (caminhos
 * de pasta, URLs). Evita duplicar a mesma lógica de adicionar/remover item
 * três vezes dentro do ConfigForm.
 */
export function ListEditor({ items, onChange, placeholder, addLabel = "Adicionar", onPickFolder }) {
  const [draft, setDraft] = useState("");

  const addItem = () => {
    const trimmed = draft.trim();
    if (!trimmed || items.includes(trimmed)) return;
    onChange([...items, trimmed]);
    setDraft("");
  };

  const removeItem = (item) => onChange(items.filter((existing) => existing !== item));

  const pickFolder = async () => {
    const picked = await onPickFolder();
    if (picked && !items.includes(picked)) onChange([...items, picked]);
  };

  return (
    <div>
      <div style={{ display: "flex", gap: "8px" }}>
        <input
          type="text"
          value={draft}
          placeholder={placeholder}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => event.key === "Enter" && (event.preventDefault(), addItem())}
        />
        {onPickFolder && (
          <button type="button" className="secondary-button" onClick={pickFolder}>
            Escolher pasta
          </button>
        )}
        <button type="button" className="secondary-button" onClick={addItem}>
          {addLabel}
        </button>
      </div>

      {items.length > 0 && (
        <ul style={{ listStyle: "none", padding: 0, margin: "8px 0 0", display: "flex", flexDirection: "column", gap: "4px" }}>
          {items.map((item) => (
            <li
              key={item}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                fontSize: "13px",
                background: "var(--color-surface-sunken)",
                borderRadius: "var(--radius-control)",
                padding: "4px 8px",
              }}
            >
              <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{item}</span>
              <button
                type="button"
                className="icon-button"
                onClick={() => removeItem(item)}
                aria-label={`Remover ${item}`}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
