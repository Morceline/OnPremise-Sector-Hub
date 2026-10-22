import { useAppState } from "../state/AppContext";

/**
 * PreferencesPanel
 * ------------------
 * Diferente do ConfigForm (que exige a chave do gestor e muda o
 * comportamento do assistente para TODO MUNDO), isto aqui é preferência
 * LOCAL da própria máquina — qualquer colaborador pode mudar, e não
 * precisa de chave nenhuma. Fica salvo em localStorage (ver
 * state/AppContext.jsx), então sobrevive a reiniciar o app, mas nunca sai
 * daquela máquina.
 */

const THEME_OPTIONS = [
  { value: "system", label: "Automático (segue o sistema)" },
  { value: "light", label: "Claro" },
  { value: "dark", label: "Escuro" },
];

export function PreferencesPanel({ onBack }) {
  const { theme, setTheme } = useAppState();

  return (
    <div className="admin-form">
      <div className="admin-gate__title" style={{ marginBottom: "4px" }}>
        Preferências
      </div>
      <span className="admin-form__hint">
        Essas opções valem só para este computador — não mudam nada para os outros colaboradores.
      </span>

      <div className="admin-form__group">
        <label>Aparência</label>
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          {THEME_OPTIONS.map((option) => (
            <label key={option.value} style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 400 }}>
              <input
                type="radio"
                name="theme"
                value={option.value}
                checked={theme === option.value}
                onChange={() => setTheme(option.value)}
              />
              {option.label}
            </label>
          ))}
        </div>
      </div>

      <button className="secondary-button" onClick={onBack}>
        Voltar
      </button>
    </div>
  );
}