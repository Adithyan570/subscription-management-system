"""A tiny local mail server for testing. It receives emails sent by the app and shows them here
and in backend/mailbox/ as .eml files. Nothing is delivered to real inboxes.

    python dev_mail_server.py                      # listens on 127.0.0.1:1025

Then, in backend/.env:   SMTP_HOST=127.0.0.1   SMTP_PORT=1025   SMTP_SECURITY=none
"""
import asyncio
import email
from datetime import datetime
from email import policy
from pathlib import Path

from aiosmtpd.controller import Controller

BOX = Path(__file__).resolve().parent / "mailbox"
BOX.mkdir(exist_ok=True)


class Handler:
    async def handle_DATA(self, server, session, envelope):
        msg = email.message_from_bytes(envelope.content, policy=policy.default)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        (BOX / f"{stamp}-{envelope.rcpt_tos[0]}.eml").write_bytes(envelope.content)
        body = msg.get_body(preferencelist=("plain",))
        print(f"\n=== MAIL RECEIVED ===\nTo: {', '.join(envelope.rcpt_tos)}\nSubject: {msg['subject']}\n\n"
              f"{body.get_content() if body else '(no text part)'}\n=====================", flush=True)
        return "250 Message accepted"


if __name__ == "__main__":
    controller = Controller(Handler(), hostname="127.0.0.1", port=1025)
    controller.start()
    print("Dev mail server listening on 127.0.0.1:1025. Emails appear here. Press Ctrl+C to stop.")
    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        controller.stop()
