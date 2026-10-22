import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QuickCategories } from "../../components/QuickCategories";

describe("QuickCategories", () => {
  it("abre o fluxo de TI ao clicar em 'Dúvidas de TI', sem chamar onSelectPrompt", async () => {
    const onSelectPrompt = vi.fn();
    const onOpenItSupport = vi.fn();
    const user = userEvent.setup();

    render(<QuickCategories onSelectPrompt={onSelectPrompt} onOpenItSupport={onOpenItSupport} />);
    await user.click(screen.getByText("Dúvidas de TI"));

    expect(onOpenItSupport).toHaveBeenCalledTimes(1);
    expect(onSelectPrompt).not.toHaveBeenCalled();
  });

  it("chama onSelectPrompt com o texto correto para 'Primeiros passos'", async () => {
    const onSelectPrompt = vi.fn();
    const user = userEvent.setup();

    render(<QuickCategories onSelectPrompt={onSelectPrompt} onOpenItSupport={vi.fn()} />);
    await user.click(screen.getByText("Primeiros passos"));

    expect(onSelectPrompt).toHaveBeenCalledWith("Quais são os primeiros passos no meu setor?");
  });
});
