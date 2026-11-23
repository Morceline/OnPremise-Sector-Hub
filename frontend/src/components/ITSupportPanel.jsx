import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { ChatInput } from "./ChatInput";

/**
 * ITSupportPanel
 * ----------------
 * Atendimento guiado de TI. O assistente faz uma pergunta por vez, com botões
 * de resposta, descobre o problema e só então sugere um teste simples.
 * Na opção "Outro problema", a pessoa descreve com as próprias palavras e o
 * assistente identifica o tema.
 */
export function ITSupportPanel({ onBack }) {
  const [messages, setMessages] = useState([]); // { id, role: 'bot'|'user', text, steps }
  const [node, setNode] = useState(null);       // último nó recebido (define os botões)
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);

  const addBot = (payload) => {
    setNode(payload);
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: "bot", text: payload.text, steps: payload.steps || [] },
    ]);
  };

  const run = async (action) => {
    setBusy(true);
    try {
      addBot(await action());
    } catch (error) {
      addBot({ text: error.message || "Não consegui continuar agora. Tente de novo.", steps: [], kind: "escalate", options: [] });
    } finally {
      setBusy(false);
    }
  };

  const started = useRef(false);
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    run(() => api.itMenu());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ behavior: "smooth", block: "end" });
  }, [messages]);

  const choose = (index, label) => {
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "user", text: label }]);
    run(() => api.itStep(node.node_id, index));
  };

  // Texto digitado: se a tela pede uma mensagem, o bot interpreta essa resposta;
  // caso contrário, é uma dúvida nova e o bot identifica o tema.
  const describe = (text) => {
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "user", text }]);
    if (node) {
      run(() => api.itAnswer(node.node_id, text));
    } else {
      run(() => api.itTriage(text));
    }
  };

  const askingText = node?.kind === "ask_text";

  return (
    <>
      <div className="quick-categories">
        <button className="chip" onClick={onBack}>
          ← Voltar ao chat do setor
        </button>
      </div>

      <div className="message-list">
        {messages.map((m) => (
          <div key={m.id} className={`message-row message-row--${m.role === "bot" ? "ai" : "user"}`}>
            <div className={`message-bubble message-bubble--${m.role === "bot" ? "ai" : "user"}`}>
              {m.text}
              {m.steps?.length === 1 && <div style={{ marginTop: "6px" }}>{m.steps[0]}</div>}
              {m.steps?.length > 1 && (
                <ul style={{ margin: "6px 0 0", paddingLeft: "18px" }}>
                  {m.steps.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        ))}
        {busy && (
          <div className="message-row message-row--ai">
            <div className="message-bubble message-bubble--ai message-bubble--pending">Um momento…</div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {!busy && node?.options?.length > 0 && !askingText && (
        <div className="quick-categories" style={{ paddingBottom: "8px" }}>
          {node.options.map((label, index) => (
            <button key={label} className="chip" onClick={() => choose(index, label)}>
              {label}
            </button>
          ))}
        </div>
      )}

      <ChatInput onSend={describe} disabled={busy} placeholder={askingText ? "Descreva o problema…" : "Ou descreva o problema…"} />
    </>
  );
}
