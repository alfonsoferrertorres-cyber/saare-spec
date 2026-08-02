# -*- coding: utf-8 -*-
# ==============================================================================
# S.A.A.R.E. v7.0 PRO - Emisor Criptográfico Serverless (/api/trial)
# ISO 42001 & EU AI Act Hardened Licensing Engine
# ==============================================================================

import json
import base64
import os
from http.server import BaseHTTPRequestHandler
from datetime import datetime, timedelta, timezone
from nacl.signing import SigningKey

# CLAVE PRIVADA ED25519 OFICIAL (Sincronizada con generar_licencias.py local)
DEFAULT_PRIVATE_KEY_HEX = "83367892821e25d770f1fba0c47c11ff4b813e54162ece9eb839e076231ab600"
PRIVATE_KEY_HEX = os.environ.get("SAARE_PRIVATE_KEY", DEFAULT_PRIVATE_KEY_HEX)

# Mapeo Oficial de Módulos Activos
TIER_MODULES_MAP = {
    "SAARE_DISCOVERY": [
        "SAARE_DISCOVER",
        "SAARE_GOVERN",
        "ACTIVE_SHIELD",
        "SAARE_ASSURE",
        "AUDITOR_SUITE"
    ],
    "AUDITOR_SUITE": [
        "SAARE_DISCOVER",
        "SAARE_GOVERN",
        "SAARE_ASSURE",
        "AUDITOR_SUITE"
    ],
    "ENTERPRISE_PLATFORM": [
        "SAARE_DISCOVER",
        "SAARE_GOVERN",
        "ACTIVE_SHIELD",
        "SAARE_ASSURE",
        "AUDITOR_SUITE"
    ],
    "PLATFORM_OEM": [
        "SAARE_DISCOVER",
        "SAARE_GOVERN",
        "ACTIVE_SHIELD",
        "SAARE_ASSURE",
        "AUDITOR_SUITE",
        "OEM_MULTI_TENANT"
    ]
}

class handler(BaseHTTPRequestHandler):

    # Preflight CORS para llamadas desde saare.es
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

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

            # Configuración para Licencias Trial (7 días)
            tier = "SAARE_DISCOVERY"
            dias = 7
            modules = TIER_MODULES_MAP[tier]

            issued_dt = datetime.now(timezone.utc)
            expires_dt = issued_dt + timedelta(days=dias)
            
            issued_at = issued_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            expires_at = expires_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

            payload = {
                "client_id": empresa,
                "email": email,
                "tier": tier,
                "modules": modules,
                "expires_at": expires_at,
                "issued_at": issued_at
            }

            # 1. Generar la firma Ed25519 del saare.lic
            signing_key = SigningKey(bytes.fromhex(PRIVATE_KEY_HEX))
            canonical_payload = json.dumps(payload, separators=(',', ':'), sort_keys=True).encode('utf-8')
            signed = signing_key.sign(canonical_payload)
            sig_b64 = base64.b64encode(signed.signature).decode('utf-8')

            lic_structure = {
                "payload": payload,
                "signature": sig_b64
            }
            lic_bytes = json.dumps(lic_structure, indent=2, ensure_ascii=False).encode('utf-8')

            # 2. Responder directamente con el JSON puro del saare.lic
            # Devolvemos Content-Type 'application/json' para que el frontend lo capture 
            # y cree el archivo descargable saare.lic en el navegador del cliente.
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            self.end_headers()
            self.wfile.write(lic_bytes)

        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _send_json(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
