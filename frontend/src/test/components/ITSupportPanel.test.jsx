import { describe, expect, it, vi, beforeEach } from "vitest";
import { StrictMode } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ITSupportPanel } from "../../components/ITSupportPanel";
import { api } from "../../api/client";

// jsdom não implementa scrollIntoView
Element.prototype.scrollIntoView = vi.fn();

vi.mock("../../api/client", () => ({
  api: { itMenu: vi.fn(), itStart: vi.fn(), itStep: vi.fn(), itTriage: vi.fn(), itAnswer: vi.fn() },
}));

const menu = {
  node_id: "menu",
  kind: "menu",
  text: "Qual é o problema?",
  steps: [],
  options: ["Impressora", "Internet ou Wi-Fi", "Teclado, mouse ou monitor", "Computador lento ou travado", "Outro problema"],
};

describe("ITSupportPanel — atendimento guiado", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.itMenu.mockResolvedValue(menu);
  });

  it("abre com a saudação e mostra os temas como botões", async () => {
    render(<ITSupportPanel onBack={vi.fn()} />);

    expect(await screen.findByText("Qual é o problema?")).toBeInTheDocument();
    expect(screen.getByText("Impressora")).toBeInTheDocument();
    expect(screen.getByText("Outro problema")).toBeInTheDocument();
  });

  it("escolher uma opção envia a escolha e mostra a próxima pergunta", async () => {
    api.itStep.mockResolvedValue({
      node_id: "imp_0",
      kind: "question",
      text: "Ela está ligada, com a luz acesa?",
      steps: [],
      options: ["Não está ligada", "Está ligada"],
    });
    const user = userEvent.setup();
    render(<ITSupportPanel onBack={vi.fn()} />);

    await user.click(await screen.findByText("Impressora"));

    await waitFor(() => expect(api.itStep).toHaveBeenCalledWith("menu", 0));
    expect(await screen.findByText("Ela está ligada, com a luz acesa?")).toBeInTheDocument();
    expect(screen.getByText("Está ligada")).toBeInTheDocument();
  });

  it("'Outro problema' abre o campo para descrever e envia para identificação", async () => {
    api.itStep.mockResolvedValue({ node_id: "outro", kind: "ask_text", text: "Descreva o problema.", steps: [], options: [] });
    api.itAnswer.mockResolvedValue({ node_id: "imp_0", kind: "question", text: "Aparece alguma mensagem?", steps: [], options: ["Sim"] });
    const user = userEvent.setup();
    render(<ITSupportPanel onBack={vi.fn()} />);

    await user.click(await screen.findByText("Outro problema"));
    const campo = await screen.findByPlaceholderText("Descreva o problema…");
    await user.type(campo, "minha impressora não imprime{Enter}");

    // Em "Outro problema", o backend identifica o tema a partir do texto livre.
    await waitFor(() => expect(api.itAnswer).toHaveBeenCalledWith("outro", "minha impressora não imprime"));
  });

  it("o campo de digitação fica sempre disponível, junto com os botões", async () => {
    render(<ITSupportPanel onBack={vi.fn()} />);

    expect(await screen.findByText("Impressora")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Ou descreva o problema…")).toBeInTheDocument();
  });

  it("mostra os passos de um teste simples quando a orientação chega", async () => {
    api.itStep.mockResolvedValue({
      node_id: "imp_liga",
      kind: "advice",
      text: "Vamos ligar a impressora.",
      steps: ["Espere a luz acender."],
      options: ["Resolveu", "Não resolveu"],
    });
    const user = userEvent.setup();
    render(<ITSupportPanel onBack={vi.fn()} />);

    await user.click(await screen.findByText("Impressora"));

    expect(await screen.findByText("Espere a luz acender.")).toBeInTheDocument();
    expect(screen.getByText("Resolveu")).toBeInTheDocument();
  });

  it("o menu aparece uma única vez, mesmo em modo de desenvolvimento (StrictMode)", async () => {
    render(
      <StrictMode>
        <ITSupportPanel onBack={vi.fn()} />
      </StrictMode>
    );

    await screen.findByText("Qual é o problema?");
    expect(api.itMenu).toHaveBeenCalledTimes(1);
    expect(screen.getAllByText("Qual é o problema?")).toHaveLength(1);
  });

  it("passo único aparece sem numeração", async () => {
    api.itStep.mockResolvedValue({
      node_id: "imp_visor_texto", kind: "ask_text", text: "Digite a mensagem.", steps: ["Desligue e ligue de novo."], options: [],
    });
    const user = userEvent.setup();
    render(<ITSupportPanel onBack={vi.fn()} />);

    await user.click(await screen.findByText("Impressora"));

    expect(await screen.findByText("Desligue e ligue de novo.")).toBeInTheDocument();
    expect(document.querySelector("ol")).toBeNull();
  });
});
