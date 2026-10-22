import { useState } from "react";
import { api } from "../../api/client";
import { ListEditor } from "./ListEditor";

const SECTOR_TYPES = [
  { value: "juridico", label: "Jurídico" },
  { value: "saude", label: "Saúde" },
  { value: "recursos_humanos", label: "Recursos Humanos" },
  { value: "militar", label: "Militar" },
  { value: "alimenticio", label: "Alimentício" },
  { value: "financeiro", label: "Financeiro" },
  { value: "operacional", label: "Operacional" },
  { value: "outro", label: "Outro" },
];

async function pickFolderNative() {
  // Só existe dentro do Tauri; em `vite dev` no navegador, pedimos que a
  // pessoa digite o caminho manualmente (fallback simples via prompt).
  try {
    const { open } = await import("@tauri-apps/plugin-dialog");
    const selected = await open({ directory: true, multiple: false });
    return typeof selected === "string" ? selected : null;
  } catch {
    return window.prompt("Digite o caminho completo da pasta:");
  }
}

const EMPTY_FORM = {
  sector_name: "",
  sector_type: "outro",
  niche_persona: "",
  allowed_local_paths: [],
  blocked_local_paths: [],
  allowed_web_urls: [],
  tacit_knowledge: "",
  feedback_email_enabled: true,
  feedback_email_to: "",
};

export function ConfigForm({ managerKey, initialConfig, onSaved, onExit }) {
  const [form, setForm] = useState({ ...EMPTY_FORM, ...initialConfig });
  const [status, setStatus] = useState(null); // { type: 'success' | 'error', message }
  const [isSaving, setIsSaving] = useState(false);

  const update = (field, value) => setForm((prev) => ({ ...prev, [field]: value }));

  const handleSubmit = async (event) => {
    event.preventDefault();
    setIsSaving(true);
    setStatus(null);

    try {
      await api.saveConfig(form, managerKey);
      setStatus({ type: "success", message: "Configuração salva. A indexação começou em segundo plano." });
      onSaved?.();
    } catch (error) {
      setStatus({ type: "error", message: error.message });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <form className="admin-form" onSubmit={handleSubmit}>
      <div className="admin-form__group">
        <label htmlFor="sector_name">Nome do setor</label>
        <input
          id="sector_name"
          type="text"
          required
          value={form.sector_name}
          onChange={(event) => update("sector_name", event.target.value)}
        />
      </div>

      <div className="admin-form__group">
        <label htmlFor="sector_type">Tipo de setor</label>
        <select id="sector_type" value={form.sector_type} onChange={(event) => update("sector_type", event.target.value)}>
          {SECTOR_TYPES.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <span className="admin-form__hint">Ajusta o tom de voz padrão e as cores do widget.</span>
      </div>

      <div className="admin-form__group">
        <label htmlFor="niche_persona">Persona / tom de voz</label>
        <textarea
          id="niche_persona"
          required
          placeholder="Ex: assistente formal, direto, evita gírias..."
          value={form.niche_persona}
          onChange={(event) => update("niche_persona", event.target.value)}
        />
      </div>

      <div className="admin-form__group">
        <label>Pastas permitidas</label>
        <span className="admin-form__hint">Só o que estiver aqui dentro pode ser lido pelo assistente.</span>
        <ListEditor
          items={form.allowed_local_paths}
          onChange={(items) => update("allowed_local_paths", items)}
          placeholder="C:\Servidor\Manuais"
          onPickFolder={pickFolderNative}
        />
      </div>

      <div className="admin-form__group">
        <label>Pastas bloqueadas</label>
        <span className="admin-form__hint">Tem prioridade sobre a lista acima — nunca é lido, mesmo se estiver dentro de uma pasta permitida.</span>
        <ListEditor
          items={form.blocked_local_paths}
          onChange={(items) => update("blocked_local_paths", items)}
          placeholder="C:\Servidor\Manuais\Diretoria"
          onPickFolder={pickFolderNative}
        />
      </div>

      <div className="admin-form__group">
        <label>Links autorizados (web)</label>
        <span className="admin-form__hint">O assistente só consulta exatamente estes links — nunca navega livre.</span>
        <ListEditor
          items={form.allowed_web_urls}
          onChange={(items) => update("allowed_web_urls", items)}
          placeholder="https://intranet.empresa.com/manual"
        />
      </div>

      <div className="admin-form__group">
        <label htmlFor="tacit_knowledge">Regras e conhecimento tácito</label>
        <span className="admin-form__hint">
          O que normalmente só passa de boca a boca: jargões, exceções, "como a rotina realmente funciona".
        </span>
        <textarea
          id="tacit_knowledge"
          rows={4}
          value={form.tacit_knowledge}
          onChange={(event) => update("tacit_knowledge", event.target.value)}
        />
      </div>

      <div className="admin-form__group">
        <label>
          <input
            type="checkbox"
            checked={form.feedback_email_enabled}
            onChange={(event) => update("feedback_email_enabled", event.target.checked)}
            style={{ marginRight: "8px" }}
          />
          Enviar feedback dos colaboradores por e-mail
        </label>
        {form.feedback_email_enabled && (
          <input
            type="text"
            placeholder="seu-email@empresa.com"
            value={form.feedback_email_to}
            onChange={(event) => update("feedback_email_to", event.target.value)}
          />
        )}
      </div>

      {status && <div className={`form-status form-status--${status.type}`}>{status.message}</div>}

      <div style={{ display: "flex", gap: "8px" }}>
        <button type="button" className="secondary-button" onClick={onExit}>
          Fechar
        </button>
        <button type="submit" className="primary-button" disabled={isSaving}>
          {isSaving ? "Salvando…" : "Salvar configuração"}
        </button>
      </div>
    </form>
  );
}
