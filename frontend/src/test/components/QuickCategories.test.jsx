import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QuickCategories } from "../../components/QuickCategories";

const handlers = () => ({
  onSelectPrompt: vi.fn(),
  onOpenItSupport: vi.fn(),
  onFocusInput: vi.fn(),
});

describe("QuickCategories", () => {
  it("abre o fluxo de TI ao clicar em Dúvidas de TI, sem preencher pergunta", async () => {
    const h = handlers();
    const user = userEvent.setup();
    render(<QuickCategories {...h} />);

    await user.click(screen.getByText("Dúvidas de TI"));

    expect(h.onOpenItSupport).toHaveBeenCalledTimes(1);
    expect(h.onSelectPrompt).not.toHaveBeenCalled();
  });

  it("preenche a pergunta padrão de Primeiros passos", async () => {
    const h = handlers();
    const user = userEvent.setup();
    render(<QuickCategories {...h} />);

    await user.click(screen.getByText("Primeiros passos"));

    expect(h.onSelectPrompt).toHaveBeenCalledWith("Quais são os primeiros passos no meu setor?");
  });

  it("Outros posiciona o cursor no campo de digitação (não fica sem resposta)", async () => {
    const h = handlers();
    const user = userEvent.setup();
    render(<QuickCategories {...h} />);

    await user.click(screen.getByText("Outros"));

    expect(h.onFocusInput).toHaveBeenCalledTimes(1);
    expect(h.onSelectPrompt).not.toHaveBeenCalled();
  });
});
