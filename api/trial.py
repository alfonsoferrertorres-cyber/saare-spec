import json
import base64
import os
from http.server import BaseHTTPRequestHandler
from datetime import datetime, timedelta, timezone
from nacl.signing import SigningKey

# Clave privada maestra Ed25519 de SAARE (Cargada desde Variable de Entorno o Fallback Oficial)
DEFAULT_PRIVATE_KEY_HEX = "b3986ec67e58a25c11bc32c1c38096f9cf5c6eeebf35e9aaae65f49437ee9df8"
PRIVATE_KEY_HEX = os.environ.get("SAARE_PRIVATE_KEY", DEFAULT_PRIVATE_KEY_HEX)

PAQUETE_TRIAL = {
    "dias": 7,
    "tier": "SAARE_TRIAL_7D",
    "modules": ["ACTIVE_SHIELD", "AUDITOR_SUITE", "SAARE_GOVERN", "SAARE_ASSURE"]
}

class handler(BaseHTTPRequestHandler):

    # 1. Manejo de Preflight CORS (Necesario para peticiones Cross-Origin desde saare.es)
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    # 2. Generación y firma criptográfica Ed25519 de saare.lic
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            
            if not body:
                self._send_json({"error": "Cuerpo de petición vacío"}, 400)
                return

            try:
                data = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                self._send_json({"error": "Formato JSON inválido"}, 400)
                return

            email = data.get("email", "").strip()
            empresa = data.get("empresa", "").strip()

            if not email or not empresa:
                self._send_json({"error": "Email y Empresa son requeridos"}, 400)
                return

            now = datetime.now(timezone.utc)
            exp_date = now + timedelta(days=PAQUETE_TRIAL["dias"])

            # Estructura del Payload homológada con la suite ejecutables
            payload = {
                "client_id": empresa,
                "email": email,
                "expires_at": exp_date.strftime("%Y-%m-%dT23:59:59Z"),
                "issued_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "modules": PAQUETE_TRIAL["modules"],
                "tier": PAQUETE_TRIAL["tier"],
                "type": PAQUETE_TRIAL["tier"]
            }

            # Validación de la Semilla Hexadecimal Ed25519 (32 Bytes)
            key_bytes = bytes.fromhex(PRIVATE_KEY_HEX)
            if len(key_bytes) != 32:
                raise ValueError("La clave privada Ed25519 debe ser exactamente de 32 bytes (64 caracteres hex).")

            # Firma canónica determinista (sin espacios y con claves ordenadas alfabéticamente)
            signing_key = SigningKey(key_bytes)
            canonical_payload = json.dumps(payload, separators=(',', ':'), sort_keys=True).encode("utf-8")
            signed = signing_key.sign(canonical_payload)
            signature_b64 = base64.b64encode(signed.signature).decode("utf-8")

            lic_data = {
                "payload": payload,
                "signature": signature_b64
            }

            self._send_json(lic_data, 200)

        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _send_json(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
