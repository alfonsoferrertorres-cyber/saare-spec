# -*- coding: utf-8 -*-
# ==============================================================================
# S.A.A.R.E. v7.0 PRO - Stripe Webhook License Issuer (/api/webhook)
# Automated Payment-to-License Delivery Engine
# ==============================================================================

import json
import base64
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from http.server import BaseHTTPRequestHandler
from datetime import datetime, timedelta, timezone
import stripe
from nacl.signing import SigningKey

# Claves y Secretos desde Variables de Entorno de Vercel
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
PRIVATE_KEY_HEX = os.environ.get("SAARE_PRIVATE_KEY", "83367892821e25d770f1fba0c47c11ff4b813e54162ece9eb839e076231ab600")

# Credenciales SMTP para envío del email corporativo
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.ionos.es")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER", "licencias@saare.es")
SMTP_PASS = os.environ.get("SMTP_PASS", "")

# Mapeo de precios de Stripe a Módulos S.A.A.R.E.
TIER_MODULES_MAP = {
    "AUDITOR_SUITE": [
        "SAARE_DISCOVER", "SAARE_GOVERN", "SAARE_ASSURE", "AUDITOR_SUITE"
    ],
    "ENTERPRISE_PLATFORM": [
        "SAARE_DISCOVER", "SAARE_GOVERN", "ACTIVE_SHIELD", "SAARE_ASSURE", "AUDITOR_SUITE"
    ]
}

class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        """Endpoint de salud/verificación para Vercel o pruebas de estado."""
        self._send_response({"status": "active", "service": "S.A.A.R.E. Webhook Engine"}, 200)

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        payload_body = self.rfile.read(content_length) if content_length > 0 else b""
        sig_header = self.headers.get('Stripe-Signature', '')

        # 1. Parsing del cuerpo y verificación de firma si viene de Stripe
        event = None
        if STRIPE_WEBHOOK_SECRET and sig_header:
            try:
                event = stripe.Webhook.construct_event(
                    payload_body, sig_header, STRIPE_WEBHOOK_SECRET
                )
            except Exception as e:
                self._send_response({"error": f"Firma Webhook inválida: {str(e)}"}, 400)
                return
        else:
            try:
                event = json.loads(payload_body.decode('utf-8')) if payload_body else {}
            except Exception as e:
                self._send_response({"error": f"JSON inválido: {str(e)}"}, 400)
                return

        # 2. Determinar tipo de evento e identificar los datos del cliente
        event_type = event.get('type') if isinstance(event, dict) else getattr(event, 'type', None)

        customer_email = ""
        customer_name = "Cliente"
        tier = "AUDITOR_SUITE"
        dias_validez = 30

        # CASO A: Petición de Prueba Manual / Trial Directo
        if event_type == 'trial' or (isinstance(event, dict) and 'email' in event):
            customer_email = event.get('email', '')
            customer_name = event.get('name', 'Cliente Trial')
            tier = event.get('tier', 'AUDITOR_SUITE')
            dias_validez = int(event.get('days', 30))

        # CASO B: Webhook Oficial de Checkout de Stripe
        elif event_type == 'checkout.session.completed':
            session = event.get('data', {}).get('object', {})
            customer_details = session.get('customer_details') or {}
            customer_email = customer_details.get('email') or session.get('customer_email') or ""
            customer_name = customer_details.get('name') or 'Empresa Cliente'
            amount_total = (session.get('amount_total') or 0) / 100.0  # Convertir céntimos a Euros

            if amount_total >= 400:
                tier = "ENTERPRISE_PLATFORM"
                dias_validez = 365
            else:
                tier = "AUDITOR_SUITE"
                dias_validez = 30
        else:
            # Evento no reconocido o no procesable (responde 200 para no reintentar en bucle)
            self._send_response({"status": "ignored", "event_type": event_type}, 200)
            return

        if not customer_email:
            self._send_response({"error": "No se proporcionó un email válido"}, 400)
            return

        # 3. Generar la Licencia Ed25519
        try:
            lic_bytes, filename = self._generar_licencia(customer_email, customer_name, tier, dias_validez)
        except Exception as e:
            self._send_response({"error": f"Error al generar licencia: {str(e)}"}, 500)
            return

        # 4. Enviar Correo con la licencia adjunta
        email_sent = False
        if SMTP_PASS and customer_email:
            try:
                self._enviar_email_licencia(customer_email, customer_name, tier, lic_bytes, filename)
                email_sent = True
            except Exception as e:
                print(f"⚠️ Error en envío de correo SMTP a {customer_email}: {str(e)}")

        self._send_response({
            "status": "success",
            "email": customer_email,
            "tier": tier,
            "email_sent": email_sent
        }, 200)

    def _generar_licencia(self, email, empresa, tier, dias):
        issued_dt = datetime.now(timezone.utc)
        expires_dt = issued_dt + timedelta(days=dias)

        payload = {
            "client_id": empresa,
            "email": email,
            "tier": tier,
            "modules": TIER_MODULES_MAP.get(tier, TIER_MODULES_MAP["AUDITOR_SUITE"]),
            "expires_at": expires_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "issued_at": issued_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        }

        signing_key = SigningKey(bytes.fromhex(PRIVATE_KEY_HEX))
        canonical_payload = json.dumps(payload, separators=(',', ':'), sort_keys=True).encode('utf-8')
        signed = signing_key.sign(canonical_payload)
        sig_b64 = base64.b64encode(signed.signature).decode('utf-8')

        lic_structure = {
            "payload": payload,
            "signature": sig_b64
        }
        
        lic_content = json.dumps(lic_structure, indent=2, ensure_ascii=False).encode('utf-8')
        return lic_content, "saare.lic"

    def _enviar_email_licencia(self, email_destino, empresa, tier, lic_bytes, filename):
        msg = MIMEMultipart()
        msg['From'] = f"S.A.A.R.E. Licensing <{SMTP_USER}>"
        msg['To'] = email_destino
        msg['Subject'] = f"🔑 Tu Licencia Oficial S.A.A.R.E. v7.0 PRO ({tier})"

        cuerpo = f"""Hola {empresa},

Gracias por activar tu suscripción corporativa a MS3V S.A.A.R.E. v7.0 PRO.

Adjunto a este correo encontrarás tu archivo criptográfico de licencia oficial: '{filename}'.

PASOS PARA ACTIVAR TU NODO:
1. Copia el archivo adjunto 'saare.lic' a la ruta de tu sistema:
   C:\\ProgramData\\SAARE\\config\\saare.lic
2. Abre la consola corporativa 'dashboard_ui.exe' o reinicia el servicio PEP Daemon L7.
3. El sistema reconocerá automáticamente los módulos asignados a tu plan ({tier}).

Para soporte técnico prioritario o consultas normativas, responde directamente a este correo.

Atentamente,
El Equipo de Soporte Criptográfico & GRC
MS3V S.A.A.R.E. SL
https://saare.es/
"""
        msg.attach(MIMEText(cuerpo, 'plain', 'utf-8'))

        # Adjuntar archivo saare.lic
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(lic_bytes)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
        msg.attach(part)

        # Envío vía SMTP con Timeout prudencial para Vercel
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()

    def _send_response(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
