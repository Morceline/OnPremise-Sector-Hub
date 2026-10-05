import { useState } from "react";
import { ApiError } from "../../api/client";

/**
 * AdminGate
 * -----------
 * Tela que pede a chave do gestor (RF04) antes de mostrar o formulário de
 * configuração. A validação de verdade acontece no backend (`/config/save`
 * exige o cabeçalho `X-Manager-Key`) — este componente só evita mostrar o
 * formulário para quem claramente não tem a chave, poupando um vai-e-volta
 * desnecessário. Em máquinas de colaboradores comuns, a pessoa não tem a
 * chave, então nunca passa daqui — exatamente o comportamento pedido
 * ("nas outras máquinas o bot não pode ser reconfigurado").
 */
export function AdminGate({ onUnlock, onCancel }) {
  const [key, setKey] = useState("");
  const [error, setError] = useState(null);

  const tryUnlock = async () => {
    setError(null);
    if (!key.trim()) return;
    onUnlock(key.trim(), (apiError) => {
      if (apiError instanceof ApiError && (apiError.status === 401 || apiError.status === 403)) {
        setError("Chave inválida. Confira com a TI do setor.");
      } else {
        setError("Não foi possível validar a chave agora.");
      }
    });
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
        autoFocus
      />

      {error && <div className="form-status form-status--error">{error}</div>}

      <div style={{ display: "flex", gap: "8px" }}>
        <button className="secondary-button" onClick={onCancel}>
          Cancelar
        </button>
        <button className="primary-button" onClick={tryUnlock} disabled={!key.trim()}>
          Entrar
        </button>
      </div>
    </div>
  );
}
