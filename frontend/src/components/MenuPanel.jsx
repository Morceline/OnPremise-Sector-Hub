/**
 * MenuPanel
 * -----------
 * Fica atrás do ícone de engrenagem no cabeçalho.
 * - "Preferências": qualquer um pode mexer, é só desta máquina.
 * - "Configurar setor": exige a chave do gestor.
 * - "Sair do assistente": apaga a conversa desta sessão e deixa o widget na
 *   bandeja do Windows (ícone perto do relógio), de onde volta ao clicar.
 */
export function MenuPanel({ onOpenPreferences, onOpenAdminGate, onRequestQuit, onBack, notice }) {
  return (
    <div className="admin-gate">
      {notice && (
        <div className="form-status form-status--success" role="status">
          {notice}
        </div>
      )}
      <button className="secondary-button" onClick={onOpenPreferences}>
        Preferências
      </button>
      <button className="secondary-button" onClick={onOpenAdminGate}>
        Configurar setor (gestor)
      </button>
      <button className="secondary-button" onClick={onRequestQuit}>
        Sair do assistente
      </button>
      <span className="admin-form__hint">Sair apaga a conversa; o assistente continua na bandeja.</span>
      <button className="secondary-button" onClick={onBack}>
        Voltar ao chat
      </button>
    </div>
  );
}
