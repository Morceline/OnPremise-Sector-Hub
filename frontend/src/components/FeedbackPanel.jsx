import { useState } from "react";
import { api } from "../api/client";
import { useAppState } from "../state/AppContext";

export function FeedbackPanel({ sessionId, onDone }) {
  const { sectorConfig } = useAppState();
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [status, setStatus] = useState("idle"); // idle | sending | sent

  const submit = async () => {
    if (rating === 0) return;
    setStatus("sending");
    try {
      await api.submitFeedback({
        rating,
        comment: comment.trim() || undefined,
        session_id: sessionId,
        sector_name: sectorConfig?.sector_name,
      });
    } catch {
      // Falha de envio não deve travar o colaborador aqui — o backend já
      // guarda uma cópia local do feedback mesmo se o e-mail falhar.
    }
    setStatus("sent");
    setTimeout(onDone, 900);
  };

  if (status === "sent") {
    return (
      <div className="feedback-panel">
        <p>Obrigado pelo seu feedback!</p>
      </div>
    );
  }

  return (
    <div className="feedback-panel">
      <p className="widget-header__title" style={{ fontSize: "15px" }}>
        Como foi o atendimento?
      </p>
      <div className="star-row">
        {[1, 2, 3, 4, 5].map((value) => (
          <button
            key={value}
            className={`star-button ${value <= rating ? "star-button--filled" : ""}`}
            onClick={() => setRating(value)}
            aria-label={`${value} estrela${value > 1 ? "s" : ""}`}
          >
            ★
          </button>
        ))}
      </div>
      <textarea
        placeholder="Comentário opcional…"
        value={comment}
        onChange={(event) => setComment(event.target.value)}
      />
      <div style={{ display: "flex", gap: "8px" }}>
        <button className="secondary-button" onClick={onDone}>
          Pular
        </button>
        <button className="primary-button" onClick={submit} disabled={rating === 0 || status === "sending"}>
          Enviar
        </button>
      </div>
    </div>
  );
}
