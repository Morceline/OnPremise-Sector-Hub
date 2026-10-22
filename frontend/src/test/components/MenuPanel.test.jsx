import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MenuPanel } from "../../components/MenuPanel";

describe("MenuPanel", () => {
  it("chama cada callback no botão correto, sem cruzar ações", async () => {
    const onOpenPreferences = vi.fn();
    const onOpenAdminGate = vi.fn();
    const onRequestQuit = vi.fn();
    const onBack = vi.fn();
    const user = userEvent.setup();

    render(
      <MenuPanel
        onOpenPreferences={onOpenPreferences}
        onOpenAdminGate={onOpenAdminGate}
        onRequestQuit={onRequestQuit}
        onBack={onBack}
      />
    );

    await user.click(screen.getByText("Sair do assistente"));
    expect(onRequestQuit).toHaveBeenCalledTimes(1);
    expect(onOpenPreferences).not.toHaveBeenCalled();
    expect(onOpenAdminGate).not.toHaveBeenCalled();

    await user.click(screen.getByText("Preferências"));
    expect(onOpenPreferences).toHaveBeenCalledTimes(1);

    await user.click(screen.getByText("Configurar setor (gestor)"));
    expect(onOpenAdminGate).toHaveBeenCalledTimes(1);

    await user.click(screen.getByText("Voltar ao chat"));
    expect(onBack).toHaveBeenCalledTimes(1);
  });
});