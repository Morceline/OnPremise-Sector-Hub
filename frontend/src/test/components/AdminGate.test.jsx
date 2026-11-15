import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AdminGate } from "../../components/admin/AdminGate";
import { api } from "../../api/client";

vi.mock("../../api/client", () => ({ api: { getManagerConfig: vi.fn() } }));

// Erro no formato que o cliente real lança: traz o status HTTP.
const httpError = (status) => Object.assign(new Error("erro"), { status });

let onUnlock;
let onCancel;

async function digitarEEntrar(texto) {
  const user = userEvent.setup();
  render(<AdminGate onUnlock={onUnlock} onCancel={onCancel} />);
  await user.type(screen.getByPlaceholderText("Chave do gestor"), texto);
  await user.click(screen.getByText("Entrar"));
}

describe("AdminGate", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    onUnlock = vi.fn();
    onCancel = vi.fn();
  });

  it("não permite entrar com o campo de chave vazio", () => {
    render(<AdminGate onUnlock={onUnlock} onCancel={onCancel} />);
    expect(screen.getByText("Entrar")).toBeDisabled();
  });

  it("com a chave certa, confere no servidor e libera o formulário", async () => {
    api.getManagerConfig.mockResolvedValue({ configured: false });
    await digitarEEntrar("  minha-chave  ");
    await waitFor(() => expect(onUnlock).toHaveBeenCalledWith("minha-chave"));
    expect(api.getManagerConfig).toHaveBeenCalledWith("minha-chave");
  });

  it("com a chave errada, NÃO libera e mostra o erro na própria tela", async () => {
    api.getManagerConfig.mockRejectedValue(httpError(403));
    await digitarEEntrar("errada");
    expect(await screen.findByRole("alert")).toHaveTextContent("Chave incorreta.");
    expect(onUnlock).not.toHaveBeenCalled();
  });

  it("servidor sem chave configurada (503) explica o motivo", async () => {
    api.getManagerConfig.mockRejectedValue(httpError(503));
    await digitarEEntrar("qualquer");
    expect(await screen.findByRole("alert")).toHaveTextContent("ainda não tem uma chave de gestor");
    expect(onUnlock).not.toHaveBeenCalled();
  });

  it("servidor fora do ar explica que não conectou", async () => {
    api.getManagerConfig.mockRejectedValue(httpError(0));
    await digitarEEntrar("qualquer");
    expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível falar com o servidor");
    expect(onUnlock).not.toHaveBeenCalled();
  });

  it("cancelar chama onCancel", async () => {
    const user = userEvent.setup();
    render(<AdminGate onUnlock={onUnlock} onCancel={onCancel} />);
    await user.click(screen.getByText("Cancelar"));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});