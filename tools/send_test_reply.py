"""Inyecta un reply de prueba en MailHog para ejercitar el listener.

El listener procesa mensajes dirigidos a RECIPIENT que contienen numeros en el
cuerpo, descarga esos PDFs del ultimo digest y responde con los adjuntos.
Este helper simula ese reply sin necesidad de la UI de MailHog.

Uso:

  Desde el host (el puerto 1025 esta publicado por docker-compose):
    Windows:        python tools\\send_test_reply.py "1 3 5"
    macOS / Linux:  python3 tools/send_test_reply.py "1 3 5"

  Dentro del contenedor listener (si no hay Python en el host):
    docker compose cp tools/send_test_reply.py listener:/tmp/send_test_reply.py
    docker compose exec listener python /tmp/send_test_reply.py "1 3 5"

El argumento son los numeros de paper a pedir; por defecto "1 3 5".
SMTP_HOST / SMTP_PORT / RECIPIENT se leen del entorno (dentro del contenedor
listener ya vienen seteados a mailhog); en el host usan los defaults de abajo.
"""

import os
import smtplib
import sys
from email.message import EmailMessage

SMTP_HOST = os.environ.get("SMTP_HOST", "localhost")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "1025"))
RECIPIENT = os.environ.get("RECIPIENT", "fer@local")


def main() -> None:
    """Envia un email tipo reply con los numeros pedidos al buzon del usuario."""
    numbers = sys.argv[1] if len(sys.argv) > 1 else "1 3 5"
    msg = EmailMessage()
    msg["From"] = RECIPIENT
    msg["To"] = RECIPIENT
    msg["Subject"] = "Re: arxiv digest"
    msg.set_content(f"Por favor enviame los papers {numbers}")
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.send_message(msg)
    print(f"reply de prueba enviado a {SMTP_HOST}:{SMTP_PORT} (numeros: {numbers})")


if __name__ == "__main__":
    main()
