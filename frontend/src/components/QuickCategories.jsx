/**
 * QuickCategories
 * -----------------
 * Atalhos mostrados quando a conversa está vazia.
 * - Primeiros passos e Regras: preenchem uma pergunta padrão.
 * - Dúvidas de TI: abre o painel de suporte de TI.
 * - Outros: posiciona o cursor no campo de digitação para a pessoa escrever a própria dúvida.
 */

const CATEGORIES = [
  { id: "primeiros-passos", label: "Primeiros passos", prompt: "Quais são os primeiros passos no meu setor?" },
  { id: "regras", label: "Regras, guias e boas práticas", prompt: "Quais são as regras e boas práticas do setor?" },
  { id: "ti", label: "Dúvidas de TI", action: "ti" },
  { id: "outros", label: "Outros", action: "focus" },
];

export function QuickCategories({ onSelectPrompt, onOpenItSupport, onFocusInput }) {
  const handleClick = (category) => {
    if (category.action === "ti") return onOpenItSupport();
    if (category.action === "focus") return onFocusInput();
    return onSelectPrompt(category.prompt);
  };

  return (
    <div className="quick-categories">
      {CATEGORIES.map((category) => (
        <button key={category.id} className="chip" onClick={() => handleClick(category)}>
          {category.label}
        </button>
      ))}
    </div>
  );
}
