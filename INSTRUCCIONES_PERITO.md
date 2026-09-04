# GUÍA RÁPIDA DE VALIDACIÓN PARA PERITOS E INFORMÁTICOS FORENSES
**Protocolo SAARE v7 PRO**

Estimado perito o auditor técnico:
Este documento le orienta en los pasos óptimos para verificar de forma independiente la integridad criptográfica del nodo de SAARE v7 PRO contenido en este repositorio.

## Pasos para la Auditoría Local:

1. **Inspección Documental:**
   * Revise el `README.md` y el `INFORME_VALIDACION_TECNICA.md` para contextualizar los parámetros de titularidad (NIF: 48553065L) y el hito de desacople del 26 de febrero de 2026.

2. **Verificación Automatizada del Certificado:**
   * Abra su terminal en la carpeta contenedora y ejecute el script de validación provisto:
     ```bash
     bash verify_node.sh
     ```
   * Este script comprobará de forma desatendida el formato PEM del archivo `certificado_raiz.pem`, sus fechas de vigencia y su huella digital SHA-256 (`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991678526855`).

3. **Inspección de Arquitectura:**
   * Consulte el archivo `architecture.mmd` mediante cualquier visor compatible con Mermaid para analizar gráficamente el flujo de filtrado perimetral en Capa 7[cite: 2, 3, 8].