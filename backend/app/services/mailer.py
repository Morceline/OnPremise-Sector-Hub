"""
services/mailer.py
---------------------
Envia o feedback (estrelas + comentário) do colaborador para o e-mail do
responsável, ao final da conversa — com opção de desativar (feedback_enabled / feedback_email_enabled).

Usa smtplib da biblioteca padrão (sem dependências extras) para manter o
projeto leve. Se as credenciais SMTP não estiverem configuradas, a função
apenas loga um aviso e grava um registro local em JSONL — o restante da
aplicação continua funcionando normalmente (o e-mail é um "extra", nunca
deve derrubar o chat).
"""

import json
import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path

from app.core.config import Settings
from app.models.feedback import FeedbackPayload

logger = logging.getLogger(__name__)


def _append_local_log(feedback: FeedbackPayload, log_path: str) -> None:
    """Guarda uma cópia local do feedback, independente do envio de e-mail
    ter funcionado ou não — garante que o dado não se perde."""
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(feedback.model_dump(), ensure_ascii=False) + "\n")


def send_feedback_email(feedback: FeedbackPayload, settings: Settings) -> bool:
    """
    Retorna True se o e-mail foi (ou tentou ser) processado sem exceção
    fatal. Sempre grava o log local primeiro, para nunca perder o dado.
    """
    _append_local_log(feedback, settings.feedback_log_path)

    if not settings.feedback_enabled:
        logger.info("Envio de feedback por e-mail está desativado nesta instalação.")
        return True

    if not settings.feedback_email_to:
        logger.warning("feedback_email_to não configurado; feedback ficou apenas no log local.")
        return True

    if not settings.smtp_host:
        logger.warning("SMTP não configurado; feedback ficou apenas no log local.")
        return True

    message = EmailMessage()
    message["Subject"] = f"[Assistente de Setor] Novo feedback ({feedback.rating}/5)"
    message["From"] = settings.smtp_user or "assistente-setor@local"
    message["To"] = settings.feedback_email_to
    message.set_content(
        f"Setor: {feedback.sector_name or 'não informado'}\n"
        f"Sessão: {feedback.session_id or 'não informado'}\n"
        f"Avaliação: {feedback.rating}/5\n\n"
        f"Comentário:\n{feedback.comment or '(sem comentário)'}"
    )

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_user and settings.smtp_password:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)
        return True
    except Exception:
        logger.exception("Falha ao enviar e-mail de feedback (o registro local foi mantido).")
        return False
