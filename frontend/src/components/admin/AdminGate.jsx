import { useState } from "react";
import { api } from "../../api/client";

/**
 * AdminGate
 * -----------
 * Tela de entrada do gestor. A chave é conferida NO SERVIDOR antes de o
 * formulário abrir: se estiver errada, a pessoa vê o erro aqui e nada da
 * configuração chega a aparecer. A rota usada é a da configuração completa,
 * que só responde com a chave certa.
 */
function messageFor(error) {
  switch (error?.status) {
    case 401:
    case 403:
      return "Chave incorreta.";
    case 503:
      return "O servidor ainda não tem uma chave de gestor configurada.";
    case 0:
      return "Não foi possível falar com o servidor. Confira se ele está ligado.";
    default:
      return "Não foi possível validar a chave agora.";
  }
}

export function AdminGate({ onUnlock, onCancel }) {
  const [key, setKey] = useState("");
  const [error, setError] = useState(null);
  const [isChecking, setIsChecking] = useState(false);

  const tryUnlock = async () => {
    const typed = key.trim();
    if (!typed || isChecking) return;

    setError(null);
    setIsChecking(true);
    try {
      await api.getManagerConfig(typed); // confere a chave no servidor
      onUnlock(typed);
    } catch (checkError) {
      setError(messageFor(checkError));
    } finally {
      setIsChecking(false);
    }
  };

  return (
    <div className="admin-gate">
      <div>
        <div className="admin-gate__title">Configuração do setor</div>
        <div className="admin-gate__subtitle">
          Só quem tem a chave do gestor pode alterar as regras, arquivos e persona do assistente.
        </div>
      </div>

      <input
        type="password"
        className="admin-key-input"
        placeholder="Chave do gestor"
        value={key}
        onChange={(event) => setKey(event.target.value)}
        onKeyDown={(event) => event.key === "Enter" && tryUnlock()}
        disabled={isChecking}
        autoFocus
      />

      {error && (
        <div className="form-status form-status--error" role="alert">
          {error}
        </div>
      )}

      <div style={{ display: "flex", gap: "8px" }}>
        <button className="secondary-button" onClick={onCancel} disabled={isChecking}>
          Cancelar
        </button>
        <button className="primary-button" onClick={tryUnlock} disabled={!key.trim() || isChecking}>
          {isChecking ? "Verificando…" : "Entrar"}
        </button>
      </div>
    </div>
  );
}
