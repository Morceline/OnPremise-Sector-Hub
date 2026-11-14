import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { ConfigForm } from "../../components/admin/ConfigForm";
import { api } from "../../api/client";

vi.mock("../../api/client", () => ({
  api: {
    getManagerConfig: vi.fn(),
    saveConfig: vi.fn(),
    getSyncStatus: vi.fn(),
    runSync: vi.fn(),
  },
}));

const statusVazio = {
  running: false,
  interval_minutes: 15,
  last_finished: null,
  last_error: null,
  items: { files: 0, web: 0, tacit: 0, chunks: 0, errors: 0, without_text: 0 },
};

describe("ConfigForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getSyncStatus.mockResolvedValue(statusVazio);
  });

  it("reabre preenchido com o que já foi salvo (pastas, links e regras)", async () => {
    api.getManagerConfig.mockResolvedValue({
      configured: true,
      sector_name: "Jurídico",
      sector_type: "juridico",
      niche_persona: "formal",
      allowed_local_paths: ["/dados/Manuais"],
      blocked_local_paths: [],
      allowed_web_urls: ["https://intranet.exemplo.com/manual"],
      tacit_knowledge: "Prazo de reembolso: 5 dias úteis.",
      feedback_email_enabled: true,
      feedback_email_to: null,
    });

    render(<ConfigForm managerKey="chave" initialConfig={{}} onExit={vi.fn()} />);

    expect(await screen.findByLabelText("Nome do setor")).toHaveValue("Jurídico");
    expect(screen.getByLabelText("Tipo de setor")).toHaveValue("juridico");
    expect(screen.getByLabelText("Regras e conhecimento tácito")).toHaveValue("Prazo de reembolso: 5 dias úteis.");
    expect(screen.getByText("/dados/Manuais")).toBeInTheDocument();
    expect(screen.getByText("https://intranet.exemplo.com/manual")).toBeInTheDocument();
    expect(api.getManagerConfig).toHaveBeenCalledWith("chave");
  });

  it("continua vazio quando ainda não há configuração salva", async () => {
    api.getManagerConfig.mockResolvedValue({ configured: false });

    render(<ConfigForm managerKey="chave" initialConfig={{}} onExit={vi.fn()} />);

    await waitFor(() => expect(api.getManagerConfig).toHaveBeenCalledWith("chave"));
    expect(screen.getByLabelText("Nome do setor")).toHaveValue("");
  });

  it("avisa quando não consegue carregar a configuração salva", async () => {
    api.getManagerConfig.mockRejectedValue(new Error("falha"));

    render(<ConfigForm managerKey="chave" initialConfig={{}} onExit={vi.fn()} />);

    expect(await screen.findByText("Não foi possível carregar a configuração salva.")).toBeInTheDocument();
  });
});
