import { describe, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { useChat } from "../../hooks/useChat";
import { api } from "../../api/client";

vi.mock("../../api/client", () => ({
  api: { sendChatMessage: vi.fn() },
}));

describe("useChat", () => {
  it("adiciona a mensagem do usuário e a resposta da IA com as fontes", async () => {
    api.sendChatMessage.mockResolvedValueOnce({
      response: "Você tem direito a 30 dias de férias.",
      sources: ["manual_rh.pdf"],
    });

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("Como funcionam as férias?");
    });

    await waitFor(() => expect(result.current.messages).toHaveLength(2));
    expect(result.current.messages[0]).toMatchObject({ role: "user", text: "Como funcionam as férias?" });
    expect(result.current.messages[1]).toMatchObject({
      role: "ai",
      text: "Você tem direito a 30 dias de férias.",
      sources: ["manual_rh.pdf"],
    });
    expect(result.current.isSending).toBe(false);
  });

  it("mostra uma mensagem de erro amigável quando a API falha", async () => {
    api.sendChatMessage.mockRejectedValueOnce(new Error("Não foi possível falar com o assistente."));

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("oi");
    });

    await waitFor(() => expect(result.current.messages).toHaveLength(2));
    expect(result.current.messages[1].isError).toBe(true);
  });

  it("ignora envio de mensagem em branco", async () => {
    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("   ");
    });

    expect(result.current.messages).toHaveLength(0);
    expect(api.sendChatMessage).not.toHaveBeenCalled();
  });
});
