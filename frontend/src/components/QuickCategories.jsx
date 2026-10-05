/**
 * QuickCategories
 * -----------------
 * Atalhos mostrados só quando a conversa está vazia (estado inicial),
 * "primeiros passos; regras, guias e boas práticas;
 * dúvidas de TI; outros". Clicar em uma categoria pré-preenche a pergunta
 * ou muda de fluxo (dúvidas de TI abre o painel dedicado, que não usa RAG).
 */

const CATEGORIES = [
  { id: "primeiros-passos", label: "Primeiros passos", prompt: "Quais são os primeiros passos no meu setor?" },
  { id: "regras", label: "Regras, guias e boas práticas", prompt: "Quais são as regras e boas práticas do setor?" },
  { id: "ti", label: "Dúvidas de TI", isItSupport: true },
  { id: "outros", label: "Outros", prompt: "" },
];

export function QuickCategories({ onSelectPrompt, onOpenItSupport }) {
  return (
    <div className="quick-categories">
      {CATEGORIES.map((category) => (
        <button
          key={category.id}
          className="chip"
          onClick={() => (category.isItSupport ? onOpenItSupport() : onSelectPrompt(category.prompt))}
        >
          {category.label}
        </button>
      ))}
    </div>
  );
}
