import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AdminGate } from "../../components/admin/AdminGate";

describe("AdminGate", () => {
  it("não permite entrar com o campo de chave vazio", () => {
    render(<AdminGate onUnlock={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByText("Entrar")).toBeDisabled();
  });

  it("chama onUnlock com a chave digitada (sem espaços extras)", async () => {
    const onUnlock = vi.fn();
    const user = userEvent.setup();

    render(<AdminGate onUnlock={onUnlock} onCancel={vi.fn()} />);
    await user.type(screen.getByPlaceholderText("Chave do gestor"), "  minha-chave  ");
    await user.click(screen.getByText("Entrar"));

    expect(onUnlock).toHaveBeenCalledWith("minha-chave", expect.any(Function));
  });

  it("chama onCancel ao clicar em Cancelar", async () => {
    const onCancel = vi.fn();
    const user = userEvent.setup();

    render(<AdminGate onUnlock={vi.fn()} onCancel={onCancel} />);
    await user.click(screen.getByText("Cancelar"));

    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
