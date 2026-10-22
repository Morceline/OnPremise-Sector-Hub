import { useState } from "react";
import { useItSupport } from "../hooks/useItSupport";
import { MessageList } from "./MessageList";
import { ChatInput } from "./ChatInput";

const CATEGORY_OPTIONS = [
  { value: "", label: "Selecione o tipo (opcional)" },
  { value: "rede", label: "Rede / internet" },
  { value: "periferico", label: "Periférico (mouse, teclado, impressora...)" },
  { value: "sistema_lento", label: "Sistema lento" },
  { value: "servidor", label: "Servidor / arquivos compartilhados" },
  { value: "documentos_planilhas", label: "Documentos / planilhas" },
  { value: "outro", label: "Outro" },
];

/**
 * ITSupportPanel
 * ----------------
 * Independente do RAG do setor: qualquer bot, em qualquer instalação,
 * sabe orientar essas dúvidas básicas. O banner "não entendi" só aparece
 * depois que a IA já respondeu alguma coisa (canSimplify).
 */
export function ITSupportPanel({ onBack }) {
  const { messages, isSending, ask, simplify, canSimplify } = useItSupport();
  const [category, setCategory] = useState("");

  return (
    <>
      <div className="quick-categories">
        <button className="chip" onClick={onBack}>
          ← Voltar ao chat do setor
        </button>
      </div>

      <div className="admin-form__group" style={{ padding: "0 16px 8px" }}>
        <select value={category} onChange={(event) => setCategory(event.target.value)}>
          {CATEGORY_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <MessageList
        messages={messages}
        isSending={isSending}
        emptyState={
          <p style={{ color: "var(--color-text-muted)", fontSize: "13px" }}>
            Descreva o problema (ex: "meu mouse parou de funcionar") e receba passos simples para testar
            antes de abrir um chamado.
          </p>
        }
      />

      {canSimplify && (
        <div className="simplify-banner">
          <span>Não entendi o que é para fazer.</span>
          <button onClick={simplify} disabled={isSending}>
            Explique mais simples
          </button>
        </div>
      )}

      <ChatInput
        onSend={(text) => ask({ problem_description: text, category: category || undefined })}
        disabled={isSending}
        placeholder="Descreva o problema…"
      />
    </>
  );
}
