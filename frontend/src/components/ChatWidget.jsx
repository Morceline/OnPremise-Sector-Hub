import { useEffect, useRef, useState } from "react";
import { useAppState } from "../state/AppContext";
import { useChat } from "../hooks/useChat";
import { useWindowChrome } from "../hooks/useWindowChrome";
import { Header } from "./Header";
import { MinimizedChip } from "./MinimizedChip";
import { MessageList } from "./MessageList";
import { QuickCategories } from "./QuickCategories";
import { ChatInput } from "./ChatInput";
import { ITSupportPanel } from "./ITSupportPanel";
import { FeedbackPanel } from "./FeedbackPanel";
import { ServerSetup } from "./ServerSetup";
import { MenuPanel } from "./MenuPanel";
import { PreferencesPanel } from "./PreferencesPanel";
import { AdminGate } from "./admin/AdminGate";
import { ConfigForm } from "./admin/ConfigForm";

/**
 * ChatWidget
 * ------------
 * Máquina de estados simples entre as telas do widget:
 * conectar ao servidor -> chat do setor -> dúvidas de TI -> menu
 * (preferências | configurar setor | sair) -> encerrar/sair (feedback)
 *
 * Fica minimizado por padrão (useWindowChrome) para não atrapalhar o
 * colaborador — só expande com um clique na bolha. A ÚNICA exceção é
 * quando o backend está inalcançável: aí forçamos a tela expandida, porque
 * uma bolha minimizada que não leva a lugar nenhum só confundiria a pessoa.
 *
 * Feedback ao final da conversa: não existe um botão nativo de "fechar
 * janela" neste widget (de propósito — é para ficar sempre disponível).
 * Por isso o gatilho de feedback é ligado às duas formas reais de
 * "terminar" que a pessoa tem: clicar em "Encerrar atendimento" (volta a
 * minimizar) ou "Sair do assistente" no menu (fecha o processo de fato).
 * Guardamos qual das duas foi pedida em `pendingAction` para o
 * FeedbackPanel saber o que fazer depois que a pessoa avalia (ou pula).
 */
export function ChatWidget() {
  const { view, setView, refreshConfig, health } = useAppState();
  const { isMinimized, minimize, expand, quit } = useWindowChrome();
  const chat = useChat();
  const [managerKey, setManagerKey] = useState(null);
  const [hasUnread, setHasUnread] = useState(false);
  const pendingActionRef = useRef(null); // 'end' | 'quit' | null

  const needsServerSetup = health.status === "offline";

  useEffect(() => {
    if (needsServerSetup && isMinimized) {
      expand();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [needsServerSetup, isMinimized]);

  if (isMinimized && !needsServerSetup) {
    return (
      <MinimizedChip
        hasUnread={hasUnread}
        onExpand={() => {
          setHasUnread(false);
          expand();
        }}
      />
    );
  }

  const handleUnlockAdmin = (key, onError) => {
    setManagerKey(key);
    setView("admin-form");
    // A validação de verdade só acontece quando o formulário é salvo (o
    // backend responde 401/403 se a chave estiver errada); aqui só
    // guardamos a chave para usar na chamada de salvar.
    void onError;
  };

  // Ponto único de decisão: só mostra a tela de feedback se houver uma
  // conversa com conteúdo; do contrário, executa a ação direto.
  const requestEndConversation = () => {
    if (chat.messages.length > 0) {
      pendingActionRef.current = "end";
      setView("feedback");
    } else {
      setView("chat");
      minimize();
    }
  };

  const requestQuit = () => {
    if (chat.messages.length > 0) {
      pendingActionRef.current = "quit";
      setView("feedback");
    } else {
      quit();
    }
  };

  const handleFeedbackDone = () => {
    const action = pendingActionRef.current;
    pendingActionRef.current = null;
    chat.resetConversation();

    if (action === "quit") {
      quit();
    } else {
      setView("chat");
      minimize();
    }
  };

  const renderBody = () => {
    if (needsServerSetup) {
      return <ServerSetup />;
    }

    if (view === "menu") {
      return (
        <MenuPanel
          onOpenPreferences={() => setView("preferences")}
          onOpenAdminGate={() => setView("admin-gate")}
          onRequestQuit={requestQuit}
          onBack={() => setView("chat")}
        />
      );
    }

    if (view === "preferences") {
      return <PreferencesPanel onBack={() => setView("menu")} />;
    }

    if (view === "admin-gate") {
      return <AdminGate onUnlock={handleUnlockAdmin} onCancel={() => setView("menu")} />;
    }

    if (view === "admin-form") {
      return (
        <ConfigForm
          managerKey={managerKey}
          initialConfig={{}}
          onSaved={refreshConfig}
          onExit={() => setView("chat")}
        />
      );
    }

    if (view === "it-support") {
      return <ITSupportPanel onBack={() => setView("chat")} />;
    }

    if (view === "feedback") {
      return <FeedbackPanel sessionId={chat.sessionId} onDone={handleFeedbackDone} />;
    }

    return (
      <>
        <MessageList
          messages={chat.messages}
          isSending={chat.isSending}
          emptyState={
            <QuickCategories
              onSelectPrompt={(prompt) => prompt && chat.sendMessage(prompt)}
              onOpenItSupport={() => setView("it-support")}
            />
          }
        />
        {chat.messages.length > 0 && (
          <div className="quick-categories">
            <button className="chip" onClick={requestEndConversation}>
              Encerrar atendimento
            </button>
          </div>
        )}
        <ChatInput onSend={chat.sendMessage} disabled={chat.isSending} />
      </>
    );
  };

  return (
    <div className="widget-panel">
      <Header onMinimize={minimize} onOpenMenu={() => setView("menu")} />
      {renderBody()}
    </div>
  );
}