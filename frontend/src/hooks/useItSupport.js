import { useCallback, useState } from "react";
import { api } from "../api/client";

/**
 * useItSupport
 * --------------
 * Fluxo do suporte de TI. Guarda a pergunta original e a última resposta, para
 * o botão "Explique mais simples" reenviar a PERGUNTA (nunca vazia) junto com a
 * resposta anterior. Antes ele mandava texto vazio e o servidor recusava.
 */
export function useItSupport() {
  const [messages, setMessages] = useState([]);
  const [isSending, setIsSending] = useState(false);
  const [lastQuestion, setLastQuestion] = useState(null);
  const [lastAnswer, setLastAnswer] = useState(null);

  const ask = useCallback(async ({ problem_description, category }) => {
    if (!problem_description.trim() || isSending) return;

    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "user", text: problem_description }]);
    setIsSending(true);

    try {
      const result = await api.queryItSupport({ problem_description, category });
      setLastQuestion(problem_description);
      setLastAnswer(result.response);
      setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "ai", text: result.response }]);
    } catch (error) {
      setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "ai", text: error.message, isError: true }]);
    } finally {
      setIsSending(false);
    }
  }, [isSending]);

  const simplify = useCallback(async () => {
    if (!lastAnswer || !lastQuestion || isSending) return;

    setIsSending(true);
    try {
      const result = await api.queryItSupport({
        problem_description: lastQuestion,
        simplify: true,
        previous_answer: lastAnswer,
      });
      setLastAnswer(result.response);
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: "ai", text: result.response, isSimplified: true },
      ]);
    } catch (error) {
      setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "ai", text: error.message, isError: true }]);
    } finally {
      setIsSending(false);
    }
  }, [lastAnswer, lastQuestion, isSending]);

  return { messages, isSending, ask, simplify, canSimplify: Boolean(lastAnswer && lastQuestion) };
}
