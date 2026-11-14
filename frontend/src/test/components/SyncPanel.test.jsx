import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SyncPanel } from "../../components/admin/SyncPanel";
import { api } from "../../api/client";

vi.mock("../../api/client", () => ({
  api: { getSyncStatus: vi.fn(), runSync: vi.fn() },
}));

const statusBase = {
  running: false,
  interval_minutes: 15,
  last_finished: "2026-10-10T15:20:00+00:00",
  last_error: null,
  items: { files: 12, web: 2, tacit: 1, chunks: 80, errors: 0, without_text: 0 },
};

describe("SyncPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("mostra a última conferência, as contagens e o intervalo automático", async () => {
    api.getSyncStatus.mockResolvedValue(statusBase);
    render(<SyncPanel managerKey="chave" />);

    expect(await screen.findByText(/12 arquivo\(s\), 2 página\(s\), 80 trecho\(s\)/)).toBeInTheDocument();
    expect(screen.getByText(/A cada 15 min/)).toBeInTheDocument();
    expect(screen.queryByText(/ainda não houve/)).not.toBeInTheDocument();
  });

  it("diz que ainda não houve conferência quando nunca sincronizou", async () => {
    api.getSyncStatus.mockResolvedValue({ ...statusBase, last_finished: null });
    render(<SyncPanel managerKey="chave" />);

    expect(await screen.findByText(/ainda não houve/)).toBeInTheDocument();
  });

  it("avisa sobre arquivos sem texto legível e fontes com erro", async () => {
    api.getSyncStatus.mockResolvedValue({
      ...statusBase,
      items: { ...statusBase.items, without_text: 3, errors: 2 },
      last_error: "Não foi possível gerar embeddings.",
    });
    render(<SyncPanel managerKey="chave" />);

    expect(await screen.findByText(/3 arquivo\(s\) sem texto legível/)).toBeInTheDocument();
    expect(screen.getByText(/2 fonte\(s\) com erro/)).toBeInTheDocument();
    expect(screen.getByText("Não foi possível gerar embeddings.")).toBeInTheDocument();
  });

  it("'Sincronizar agora' chama a API com a chave do gestor", async () => {
    api.getSyncStatus.mockResolvedValue(statusBase);
    api.runSync.mockResolvedValue({ status: "started" });
    const user = userEvent.setup();
    render(<SyncPanel managerKey="minha-chave" pollMs={10} />);

    await user.click(await screen.findByText("Sincronizar agora"));

    expect(api.runSync).toHaveBeenCalledWith("minha-chave");
  });

  it("enquanto sincroniza, o botão fica desabilitado", async () => {
    // Estado "rodando" fixo: o teste não depende de tempo de consulta.
    api.getSyncStatus
      .mockResolvedValueOnce(statusBase) // ao abrir
      .mockResolvedValue({ ...statusBase, running: true }); // depois de pedir
    api.runSync.mockResolvedValue({ status: "started" });
    const user = userEvent.setup();
    render(<SyncPanel managerKey="chave" pollMs={60000} />);

    await user.click(await screen.findByText("Sincronizar agora"));

    expect(await screen.findByText("Sincronizando…")).toBeDisabled();
  });

  it("mostra a mensagem de erro quando a chave é recusada", async () => {
    api.getSyncStatus.mockResolvedValue(statusBase);
    api.runSync.mockRejectedValue(new Error("Chave de gestor inválida."));
    const user = userEvent.setup();
    render(<SyncPanel managerKey="errada" />);

    await user.click(await screen.findByText("Sincronizar agora"));

    expect(await screen.findByText("Chave de gestor inválida.")).toBeInTheDocument();
  });
});
