#!/bin/bash
# Script automatizado de validación criptográfica para SAARE v7 PRO
# Autor: Alfonso Ferrer Torres (Gabinete Técnico Comercial MS3V)

echo "===================================================="
echo " INICIANDO VALIDACIÓN CRIPTOGRÁFICA DE NODO SAARE"
echo "===================================================="

CERT="certificado_raiz.pem"

if [ ! -f "$CERT" ]; then
    echo "[!] Error: No se encuentra el archivo $CERT en el directorio."
    exit 1
fi

echo "[*] 1. Comprobando sintaxis y formato del certificado..."
openssl x509 -in "$CERT" -inform PEM -noout && echo "[+] Formato PEM correcto."

echo -e "\n[*] 2. Extrayendo fechas de validez:"
openssl x509 -in "$CERT" -dates -noout

echo -e "\n[*] 3. Calculando huella digital SHA-256:"
openssl x509 -in "$CERT" -sha256 -noout -fingerprint

echo -e "\n===================================================="
echo " VERIFICACIÓN FINALIZADA - MODO LOCAL_LOOPBACK_BIND"
echo "===================================================="