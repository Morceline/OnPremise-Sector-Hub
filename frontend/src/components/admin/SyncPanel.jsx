import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../api/client";

function formatMoment(iso) {
  if (!iso) return null;
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? null : date.toLocaleString("pt-BR");
}

/**
 * SyncPanel
 * -----------
 * Mostra ao gestor quando o assistente conferiu as fontes pela última vez e
 * oferece o botão "Sincronizar agora". A sincronização automática roda a
 * cada alguns minutos no servidor; o botão serve para quando o gestor acabou
 * de colocar um documento e não quer esperar.
 *
 * O status é público e não traz caminhos de arquivo — só contagens.
 */
export function SyncPanel({ managerKey, pollMs = 3000, maxPolls = 40 }) {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const [isStarting, setIsStarting] = useState(false);
  const timerRef = useRef(null);

  const load = useCallback(async () => {
    try {
      const current = await api.getSyncStatus();
      setStatus(current);
      return current;
    } catch (loadError) {
      setError(loadError.message);
      return null;
    }
  }, []);

  useEffect(() => {
    load();
    return () => clearTimeout(timerRef.current);
  }, [load]);

  // Depois de pedir a sincronização, confere o status de tempos em tempos
  // enquanto estiver rodando (com teto, para nunca ficar consultando para sempre).
  const pollUntilDone = useCallback(
    (attempt = 0) => {
      timerRef.current = setTimeout(async () => {
        const current = await load();
        if (current?.running && attempt < maxPolls) pollUntilDone(attempt + 1);
      }, pollMs);
    },
    [load, pollMs, maxPolls]
  );

  const handleRun = async () => {
    setError(null);
    setIsStarting(true);
    try {
      await api.runSync(managerKey);
      await load();
      pollUntilDone();
    } catch (runError) {
      setError(runError.message);
    } finally {
      setIsStarting(false);
    }
  };

  const items = status?.items;
  const lastCheck = formatMoment(status?.last_finished);
  const isRunning = Boolean(status?.running);

  return (
    <div className="admin-form__group">
      <label>Sincronização das fontes</label>
      <span className="admin-form__hint">
        {status
          ? `A cada ${status.interval_minutes} min o assistente confere as pastas e links autorizados e atualiza só o que mudou.`
          : "O assistente confere periodicamente as pastas e links autorizados."}
      </span>

      <p role="status" style={{ margin: "4px 0", fontSize: "13px" }}>
        Última conferência: {lastCheck ?? "ainda não houve"}
        {items && ` · ${items.files} arquivo(s), ${items.web} página(s), ${items.chunks} trecho(s)`}
      </p>

      {items?.without_text > 0 && (
        <span className="admin-form__hint">
          {items.without_text} arquivo(s) sem texto legível (ex.: PDF escaneado) — não entram nas respostas.
        </span>
      )}
      {items?.errors > 0 && (
        <span className="admin-form__hint">{items.errors} fonte(s) com erro na última leitura.</span>
      )}
      {status?.last_error && <div className="form-status form-status--error">{status.last_error}</div>}
      {error && <div className="form-status form-status--error">{error}</div>}

      <div>
        <button type="button" className="secondary-button" onClick={handleRun} disabled={isRunning || isStarting}>
          {isRunning ? "Sincronizando…" : "Sincronizar agora"}
        </button>
      </div>
    </div>
  );
}
