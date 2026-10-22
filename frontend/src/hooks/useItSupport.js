import { useCallback, useState } from "react";
import { api } from "../api/client";

/**
 * useItSupport
 * --------------
 * Fluxo separado do chat do setor: mantém a última pergunta/resposta para
 * viabilizar o botão "não entendi, explique mais simples" (RF pedido pelo
 * usuário), que reenvia com `simplify: true` + a resposta anterior.
 */
export function useItSupport() {
  const [messages, setMessages] = useState([]);
  const [isSending, setIsSending] = useState(false);
  const [lastAnswer, setLastAnswer] = useState(null);

  const ask = useCallback(async ({ problem_description, category }) => {
    if (!problem_description.trim() || isSending) return;

    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "user", text: problem_description }]);
    setIsSending(true);

    try {
      const result = await api.queryItSupport({ problem_description, category });
      setLastAnswer(result.response);
      setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "ai", text: result.response }]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: "ai", text: error.message, isError: true },
      ]);
    } finally {
      setIsSending(false);
    }
  }, [isSending]);

  const simplify = useCallback(async () => {
    if (!lastAnswer || isSending) return;

    setIsSending(true);
    try {
      const result = await api.queryItSupport({
        problem_description: "",
        simplify: true,
        previous_answer: lastAnswer,
      });
      setLastAnswer(result.response);
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: "ai", text: result.response, isSimplified: true },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: "ai", text: error.message, isError: true },
      ]);
    } finally {
      setIsSending(false);
    }
  }, [lastAnswer, isSending]);

  return { messages, isSending, ask, simplify, canSimplify: Boolean(lastAnswer) };
}
