import { useState } from "react";

export function ChatInput({ onSend, disabled, placeholder = "Digite sua dúvida…" }) {
  const [value, setValue] = useState("");

  const handleSend = () => {
    if (!value.trim()) return;
    onSend(value);
    setValue("");
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-input">
      <textarea
        className="chat-input__field"
        rows={1}
        value={value}
        placeholder={placeholder}
        disabled={disabled}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={handleKeyDown}
      />
      <button
        className="send-button"
        onClick={handleSend}
        disabled={disabled || !value.trim()}
        aria-label="Enviar mensagem"
      >
        ➤
      </button>
    </div>
  );
}
