import { useCallback, useRef, useState } from "react";
import { api } from "../api/client";

function makeSessionId() {
  return `sess-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

/**
 * useChat
 * --------
 * Estado do fio de conversa do setor (não confundir com o fluxo de TI,
 * que tem seu próprio hook mais simples por não manter histórico longo).
 */
export function useChat() {
  const [messages, setMessages] = useState([]);
  const [isSending, setIsSending] = useState(false);
  const sessionIdRef = useRef(makeSessionId());

  const sendMessage = useCallback(async (text) => {
    const trimmed = text.trim();
    if (!trimmed || isSending) return;

    const userMessage = { id: crypto.randomUUID(), role: "user", text: trimmed };
    setMessages((prev) => [...prev, userMessage]);
    setIsSending(true);

    try {
      const result = await api.sendChatMessage(trimmed, sessionIdRef.current);
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "ai",
          text: result.response,
          sources: result.sources || [],
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "ai",
          text: error.message || "Não consegui responder agora. Tente novamente em instantes.",
          isError: true,
        },
      ]);
    } finally {
      setIsSending(false);
    }
  }, [isSending]);

  const resetConversation = useCallback(() => {
    setMessages([]);
    sessionIdRef.current = makeSessionId();
  }, []);

  return { messages, isSending, sendMessage, resetConversation, sessionId: sessionIdRef.current };
}
