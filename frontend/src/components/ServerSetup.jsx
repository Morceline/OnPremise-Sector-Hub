import { useState } from "react";
import { api, setApiBaseUrl } from "../api/client";
import { useAppState } from "../state/AppContext";

/**
 * ServerSetup
 * -------------
 * Aparece só quando o widget não consegue falar com o backend no endereço
 * atual — o caso normal na PRIMEIRA vez que o app roda em uma máquina de
 * colaborador (que não tem backend local, diferente da máquina do
 * servidor). A pessoa digita o endereço uma vez; fica salvo naquela
 * máquina (ver api/client.js) e essa tela nunca mais aparece ali.
 *
 * Deliberadamente NÃO exige a chave do gestor: apontar para o servidor
 * certo é configuração de rede, não uma alteração no comportamento do
 * assistente — qualquer colaborador pode (e precisa poder) fazer isso
 * sozinho, sem depender da TI para cada máquina nova.
 */
export function ServerSetup() {
  const { refreshHealthNow } = useAppState();
  const [address, setAddress] = useState("");
  const [status, setStatus] = useState("idle"); // idle | testing | error
  const [errorMessage, setErrorMessage] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!address.trim()) return;

    setStatus("testing");
    setErrorMessage(null);
    const normalized = setApiBaseUrl(address);

    try {
      await api.health();
      await refreshHealthNow();
    } catch {
      setStatus("error");
      setErrorMessage(`Não consegui conectar em ${normalized}. Confira o endereço com a TI do setor.`);
    }
  };

  return (
    <div className="admin-gate">
      <div>
        <div className="admin-gate__title">Conectar ao servidor</div>
        <div className="admin-gate__subtitle">
          Este computador ainda não sabe onde encontrar o Assistente de Setor na rede. Peça o endereço
          para a TI (algo como <code>192.168.1.10:8000</code>) e digite abaixo.
        </div>
      </div>

      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        <input
          type="text"
          className="admin-key-input"
          placeholder="Endereço do servidor (ex: 192.168.1.10:8000)"
          value={address}
          onChange={(event) => setAddress(event.target.value)}
          autoFocus
        />

        {status === "error" && <div className="form-status form-status--error">{errorMessage}</div>}

        <button className="primary-button" type="submit" disabled={!address.trim() || status === "testing"}>
          {status === "testing" ? "Testando conexão…" : "Conectar"}
        </button>
      </form>
    </div>
  );
}
