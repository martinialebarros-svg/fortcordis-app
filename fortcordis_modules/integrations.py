"""
Módulo de Integrações - Fort Cordis
Google Calendar (export .ics) e WhatsApp (link para confirmação)
"""

from datetime import datetime
from pathlib import Path
from urllib.parse import quote
import re


def whatsapp_link(numero: str, mensagem: str = "") -> str:
    """
    Gera link para abrir conversa no WhatsApp.
    numero: telefone só números (ex: 85987654321) ou com formatação (ex: (85) 98765-4321)
    mensagem: texto opcional pré-preenchido (ex: "Confirmar agendamento para amanhã...")
    """
    if not numero:
        return ""
    # Remove tudo que não é dígito
    digits = re.sub(r"\D", "", str(numero))
    if len(digits) < 10:
        return ""
    # Brasil: 55 + DDD + número
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 10:  # DDD + 8 ou 9 dígitos
        digits = "55" + digits
    elif len(digits) == 11 and digits.startswith("55"):
        pass
    elif len(digits) == 11:
        digits = "55" + digits
    url = f"https://wa.me/{digits}"
    if mensagem:
        url += f"?text={quote(mensagem)}"
    return url


def mensagem_confirmacao_agendamento(data: str, hora: str, paciente: str, clinica: str) -> str:
    """Texto sugerido para enviar ao confirmar agendamento (24h antes)."""
    return (
        f"Olá! Confirmando agendamento para *{data}* às *{hora}* – "
        f"Paciente: *{paciente}* – Clínica *{clinica}*. "
        "Podem confirmar?"
    )


def exportar_agendamento_ics(data: str, hora: str, titulo: str, descricao: str = "", duracao_minutos: int = 60) -> str:
    """
    Gera conteúdo de arquivo .ics para um agendamento (importar no Google Calendar).
    Retorna string do conteúdo .ics.
    """
    try:
        dt = datetime.strptime(f"{data} {hora}", "%Y-%m-%d %H:%M")
    except Exception:
        try:
            dt = datetime.strptime(f"{data} {hora}", "%Y-%m-%d %H:%M:%S")
        except Exception:
            dt = datetime.now()
    start = dt.strftime("%Y%m%dT%H%M00")
    from datetime import timedelta
    end_dt = dt + timedelta(minutes=duracao_minutos)
    end = end_dt.strftime("%Y%m%dT%H%M00")
    uid = f"fortcordis-{data}-{hora}-{hash(titulo) % 10**8}@fortcordis"
    ics = (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//Fort Cordis//Agendamento//PT\r\n"
        "BEGIN:VEVENT\r\n"
        f"UID:{uid}\r\n"
        f"DTSTART:{start}\r\n"
        f"DTEND:{end}\r\n"
        f"SUMMARY:{titulo}\r\n"
    )
    if descricao:
        ics += f"DESCRIPTION:{descricao.replace(chr(10), '\\\\n')}\r\n"
    ics += "END:VEVENT\r\nEND:VCALENDAR\r\n"
    return ics


# Para listar "Confirmar amanhã", use no app:
# listar_agendamentos(data_inicio=amanha, data_fim=amanha, status='Agendado')
# onde amanha = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
