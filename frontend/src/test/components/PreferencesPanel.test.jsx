import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PreferencesPanel } from "../../components/PreferencesPanel";
import { AppProvider } from "../../state/AppContext";

vi.mock("../../api/client", () => ({
  api: {
    health: vi.fn().mockResolvedValue({ status: "online", dependencies: { qdrant: true, ollama: true } }),
    getActiveConfig: vi.fn().mockResolvedValue({ configured: false }),
  },
}));

async function renderWithProvider(ui) {
  const result = render(<AppProvider>{ui}</AppProvider>);
  // Deixa os efeitos assíncronos do AppProvider (health/config) resolverem
  // dentro de um act() do Testing Library antes de fazer asserções —
  // evita o aviso "not wrapped in act(...)" sem mudar nenhum componente.
  await screen.findByText("Voltar");
  return result;
}

describe("PreferencesPanel", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("marca 'Automático' como selecionado por padrão", async () => {
    await renderWithProvider(<PreferencesPanel onBack={vi.fn()} />);
    expect(screen.getByLabelText("Automático (segue o sistema)")).toBeChecked();
  });

  it("troca para o tema escuro e salva a escolha em localStorage", async () => {
    const user = userEvent.setup();
    await renderWithProvider(<PreferencesPanel onBack={vi.fn()} />);

    await user.click(screen.getByLabelText("Escuro"));

    expect(screen.getByLabelText("Escuro")).toBeChecked();
    expect(localStorage.getItem("assistente-setor:theme")).toBe("dark");
  });

  it("chama onBack ao clicar em Voltar", async () => {
    const onBack = vi.fn();
    const user = userEvent.setup();
    await renderWithProvider(<PreferencesPanel onBack={onBack} />);

    await user.click(screen.getByText("Voltar"));
    expect(onBack).toHaveBeenCalledTimes(1);
  });
});