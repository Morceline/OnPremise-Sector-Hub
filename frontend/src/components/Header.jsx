import { useAppState } from "../state/AppContext";

/**
 * Header
 * --------
 * Área de arraste da janela (via `data-tauri-drag-region`, o atributo que
 * o Tauri realmente usa para permitir mover uma janela sem borda nativa —
 * diferente de `-webkit-app-region`, que não funciona no WebView2 do
 * Windows). Os botões dentro do header precisam ficar FORA da área de
 * arraste, senão o clique nunca chega a eles.
 */
export function Header({ onMinimize, onOpenAdmin }) {
  const { sectorConfig, health } = useAppState();

  const title = sectorConfig?.configured ? sectorConfig.sector_name : "Assistente de Setor";
  const isDegraded = health.status !== "online";

  return (
    <div className="widget-header" data-tauri-drag-region>
      <span
        className={`widget-header__status ${isDegraded ? "widget-header__status--degraded" : ""}`}
        title={isDegraded ? "Algum serviço local está indisponível" : "Tudo funcionando"}
      />
      <span className="widget-header__title">{title}</span>
      <div className="widget-header__actions">
        <button className="icon-button" onClick={onOpenAdmin} aria-label="Configurações">
          ⚙
        </button>
        <button className="icon-button" onClick={onMinimize} aria-label="Minimizar">
          –
        </button>
      </div>
    </div>
  );
}
