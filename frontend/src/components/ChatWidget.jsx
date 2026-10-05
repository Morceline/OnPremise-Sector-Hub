import { useEffect, useState } from "react";
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
import { AdminGate } from "./admin/AdminGate";
import { ConfigForm } from "./admin/ConfigForm";

/**
 * ChatWidget
 * ------------
 * Máquina de estados simples entre as telas do widget:
 * conectar ao servidor -> chat do setor -> dúvidas de TI -> encerrar (feedback) -> admin (gate -> form)
 *
 * Fica minimizado por padrão (useWindowChrome) para não atrapalhar o
 * colaborador — só expande com um clique na bolha. A ÚNICA exceção é
 * quando o backend está inalcançável: aí forçamos a tela expandida, porque
 * uma bolha minimizada que não leva a lugar nenhum só confundiria a pessoa.
 */
export function ChatWidget() {
  const { view, setView, refreshConfig, health } = useAppState();
  const { isMinimized, minimize, expand } = useWindowChrome();
  const chat = useChat();
  const [managerKey, setManagerKey] = useState(null);
  const [hasUnread, setHasUnread] = useState(false);

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

  const renderBody = () => {
    if (needsServerSetup) {
      return <ServerSetup />;
    }

    if (view === "admin-gate") {
      return <AdminGate onUnlock={handleUnlockAdmin} onCancel={() => setView("chat")} />;
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
      return (
        <FeedbackPanel
          sessionId={chat.sessionId}
          onDone={() => {
            chat.resetConversation();
            setView("chat");
          }}
        />
      );
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
            <button className="chip" onClick={() => setView("feedback")}>
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
      <Header onMinimize={minimize} onOpenAdmin={() => setView("admin-gate")} />
      {renderBody()}
    </div>
  );
}
