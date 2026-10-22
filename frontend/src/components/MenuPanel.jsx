/**
 * MenuPanel
 * -----------
 * Fica atrás do ícone de engrenagem no cabeçalho. Reúne três ações de
 * naturezas bem diferentes, por isso cada uma tem seu próprio fluxo:
 * - "Preferências": qualquer um pode mexer, é só desta máquina.
 * - "Configurar setor": exige a chave do gestor (vai para o AdminGate).
 * - "Sair do assistente": fica aqui dentro (não solto no cabeçalho) de
 *   propósito — a empresa geralmente quer esse assistente sempre
 *   disponível, então um botão de fechar visível demais convida a
 *   fechamentos acidentais.
 */
export function MenuPanel({ onOpenPreferences, onOpenAdminGate, onRequestQuit, onBack }) {
  return (
    <div className="admin-gate">
      <button className="secondary-button" onClick={onOpenPreferences}>
        Preferências
      </button>
      <button className="secondary-button" onClick={onOpenAdminGate}>
        Configurar setor (gestor)
      </button>
      <button className="secondary-button" onClick={onRequestQuit}>
        Sair do assistente
      </button>
      <button className="secondary-button" onClick={onBack}>
        Voltar ao chat
      </button>
    </div>
  );
}