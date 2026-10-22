/**
 * MinimizedChip
 * ---------------
 * Estado padrão do widget: uma bolha pequena ancorada no canto, sem
 * atrapalhar o trabalho do colaborador. `hasUnread` liga um selo por um
 * instante — a única "animação de chamar atenção" do sistema, e mesmo
 * essa só dispara em resposta a um evento real (mensagem nova), nunca em
 * loop.
 */
export function MinimizedChip({ onExpand, hasUnread }) {
  return (
    <button
      className="minimized-chip"
      onClick={onExpand}
      aria-label="Abrir assistente de setor"
      data-tauri-drag-region={false}
    >
      💬
      {hasUnread && <span className="minimized-chip__badge" aria-hidden="true" />}
    </button>
  );
}
