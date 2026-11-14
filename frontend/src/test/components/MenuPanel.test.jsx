import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MenuPanel } from "../../components/MenuPanel";

const callbacks = () => ({
  onOpenPreferences: vi.fn(),
  onOpenAdminGate: vi.fn(),
  onRequestQuit: vi.fn(),
  onBack: vi.fn(),
});

describe("MenuPanel", () => {
  it("chama cada callback no botão correto, sem cruzar ações", async () => {
    const cb = callbacks();
    const user = userEvent.setup();
    render(<MenuPanel {...cb} />);

    await user.click(screen.getByText("Sair do assistente"));
    expect(cb.onRequestQuit).toHaveBeenCalledTimes(1);
    expect(cb.onOpenPreferences).not.toHaveBeenCalled();
    expect(cb.onOpenAdminGate).not.toHaveBeenCalled();

    await user.click(screen.getByText("Preferências"));
    expect(cb.onOpenPreferences).toHaveBeenCalledTimes(1);

    await user.click(screen.getByText("Configurar setor (gestor)"));
    expect(cb.onOpenAdminGate).toHaveBeenCalledTimes(1);

    await user.click(screen.getByText("Voltar ao chat"));
    expect(cb.onBack).toHaveBeenCalledTimes(1);
  });

  it("mostra o aviso quando existe e não mostra nada quando não existe", () => {
    const cb = callbacks();
    const { rerender } = render(<MenuPanel {...cb} />);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();

    rerender(<MenuPanel {...cb} notice="Sair só funciona no aplicativo desktop." />);
    expect(screen.getByRole("status")).toHaveTextContent("Sair só funciona no aplicativo desktop.");
  });
});
