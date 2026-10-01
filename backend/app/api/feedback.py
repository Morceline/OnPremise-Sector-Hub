"""
api/feedback.py
------------------
Recebe a avaliação (1 a 5 estrelas + comentário opcional) que o colaborador
dá ao final da conversa e dispara o envio por e-mail em segundo plano —
sem bloquear a resposta ao usuário nem travar o chat caso o SMTP esteja
fora do ar (ver services/mailer.py, que sempre grava um log local primeiro).
"""

from fastapi import APIRouter, BackgroundTasks, Depends

from app.core.config import Settings, get_settings
from app.models.feedback import FeedbackPayload
from app.services.mailer import send_feedback_email

router = APIRouter()


@router.post("/submit")
async def submit_feedback(
    payload: FeedbackPayload,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
):
    background_tasks.add_task(send_feedback_email, payload, settings)
    return {"status": "received", "message": "Obrigado pelo seu feedback!"}
