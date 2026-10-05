import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatInput } from "../../components/ChatInput";

describe("ChatInput", () => {
  it("envia o texto digitado ao clicar no botão e limpa o campo", async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    render(<ChatInput onSend={onSend} disabled={false} />);

    const field = screen.getByPlaceholderText("Digite sua dúvida…");
    await user.type(field, "Como funciona o pedido de férias?");
    await user.click(screen.getByLabelText("Enviar mensagem"));

    expect(onSend).toHaveBeenCalledWith("Como funciona o pedido de férias?");
    expect(field).toHaveValue("");
  });

  it("envia ao pressionar Enter, mas não ao pressionar Shift+Enter", async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    render(<ChatInput onSend={onSend} disabled={false} />);

    const field = screen.getByPlaceholderText("Digite sua dúvida…");
    await user.type(field, "linha 1{Shift>}{Enter}{/Shift}linha 2");
    expect(onSend).not.toHaveBeenCalled();

    await user.type(field, "{Enter}");
    expect(onSend).toHaveBeenCalledTimes(1);
  });

  it("não envia texto vazio e o botão de enviar fica desabilitado", () => {
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} disabled={false} />);

    expect(screen.getByLabelText("Enviar mensagem")).toBeDisabled();
  });

  it("desabilita o campo quando `disabled` é true (aguardando resposta)", () => {
    render(<ChatInput onSend={vi.fn()} disabled={true} />);
    expect(screen.getByPlaceholderText("Digite sua dúvida…")).toBeDisabled();
  });
});
