import { useEffect, useRef } from "react";

export function MessageList({ messages, isSending, emptyState }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isSending]);

  if (messages.length === 0 && emptyState) {
    return <div className="message-list">{emptyState}</div>;
  }

  return (
    <div className="message-list">
      {messages.map((message) => (
        <div key={message.id} className={`message-row message-row--${message.role}`}>
          <div className={`message-bubble message-bubble--${message.role}`}>
            {message.text}
            {message.sources?.length > 0 && (
              <div className="message-sources">Fonte: {message.sources.join(", ")}</div>
            )}
          </div>
        </div>
      ))}
      {isSending && (
        <div className="message-row message-row--ai">
          <div className="message-bubble message-bubble--ai message-bubble--pending">Digitando…</div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
