# Guía de Deployment - VibeVoice TTS Backend

Esta guía te ayudará a deployar el backend de VibeVoice TTS a **Google Cloud Run**, que está integrado con Firebase.

## Arquitectura de Deployment

```
Cliente (React Native)
    ↓ WebSocket
Google Cloud Run (Backend FastAPI + VibeVoice)
    ↓
HuggingFace Hub (Modelo VibeVoice)
```

## Requisitos Previos

### 1. Cuenta de Google Cloud Platform (GCP)

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea una cuenta si no tienes una (incluye $300 USD de crédito gratis)
3. Crea un nuevo proyecto o selecciona uno existente

### 2. Instalar Google Cloud SDK

**Windows:**
```bash
# Descarga e instala desde:
https://cloud.google.com/sdk/docs/install
```

**macOS:**
```bash
brew install google-cloud-sdk
```

**Linux:**
```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

### 3. Configurar gcloud CLI

```bash
# Autenticarte
gcloud auth login

# Configurar proyecto
gcloud config set project YOUR_PROJECT_ID

# Habilitar APIs necesarias
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

## Opción 1: Deployment Manual (Recomendado para primera vez)

### Paso 1: Preparar el código

1. Asegúrate de que todos los archivos de voces estén en `voices/streaming_model/`
2. Verifica que el `.env.production` tenga las configuraciones correctas

### Paso 2: Build local (opcional, para testing)

```bash
# Build la imagen Docker localmente
docker build -t vibevoice-tts .

# Probar localmente
docker run -p 8080:8080 vibevoice-tts

# Testear en otra terminal
curl http://localhost:8080/health
```

### Paso 3: Deploy a Cloud Run

```bash
# Establecer variables
export PROJECT_ID=mytranslatevoice
export REGION=us-central1  # Cambia según tu preferencia

# Build y deploy en un solo comando
gcloud run deploy vibevoice-tts \
  --source . \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --memory=8Gi \
  --cpu=4 \
  --timeout=300 \
  --max-instances=10 \
  --min-instances=0 \
  --port=8080 \
  --set-env-vars="HOST=0.0.0.0,PORT=8080,DEVICE=cpu,MODEL_PATH=microsoft/VibeVoice-Realtime-0.5B,DEFAULT_VOICE=en-Carter_man,INFERENCE_STEPS=5,CFG_SCALE=1.5"
```

Este comando:
- Sube el código a Cloud Build
- Crea la imagen Docker
- Deploya a Cloud Run
- Configura las variables de entorno

### Paso 4: Obtener la URL del servicio

```bash
gcloud run services describe vibevoice-tts --region=$REGION --format='value(status.url)'
```

Ejemplo de URL: `https://vibevoice-tts-abc123-uc.a.run.app`

### Paso 5: Actualizar el cliente

Actualiza la URL del WebSocket en tu cliente React Native:

```typescript
// En client/mytranslatevoice/app/(tabs)/index.tsx
const [wsUrl, setWsUrl] = useState('wss://vibevoice-tts-abc123-uc.a.run.app/tts/ws');
```

**Importante:** Cambia `https://` por `wss://` para WebSockets.

## Opción 2: Deployment Automatizado con Cloud Build

### Paso 1: Configurar trigger de Cloud Build

```bash
# Conectar tu repositorio GitHub
gcloud builds submit --config cloudbuild.yaml .
```

### Paso 2: (Opcional) Configurar CI/CD automático

1. Ve a Cloud Build en GCP Console
2. Conecta tu repositorio de GitHub
3. Crea un trigger para deployar automáticamente en cada push a `main`

## Configuración Avanzada

### Usar GPU (más rápido pero más caro)

Si necesitas mejor rendimiento, puedes habilitar GPU:

```bash
gcloud run deploy vibevoice-tts \
  --source . \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --memory=16Gi \
  --cpu=8 \
  --gpu=1 \
  --gpu-type=nvidia-l4 \
  --set-env-vars="DEVICE=cuda,..."
```

**Nota:** GPU aumenta significativamente el costo.

### Optimizar costos

Para reducir costos:

1. **Scale to Zero**: Usa `--min-instances=0` para que no haya instancias corriendo cuando no hay tráfico
2. **Reducir recursos**: Prueba con `--memory=4Gi --cpu=2` primero
3. **Limitar concurrencia**: Usa `--concurrency=10` para limitar peticiones simultáneas

### Monitoreo y Logs

Ver logs en tiempo real:
```bash
gcloud run services logs tail vibevoice-tts --region=$REGION
```

Ver métricas:
```bash
# Ve a Cloud Console > Cloud Run > vibevoice-tts > Metrics
```

## Estimación de Costos

Con Cloud Run:
- **Sin tráfico**: $0 (con min-instances=0)
- **Con tráfico moderado** (1000 req/día, 2s promedio):
  - CPU time: ~$5-10/mes
  - RAM: ~$3-5/mes
  - Network: ~$1-2/mes
  - **Total**: ~$10-20/mes

**Nota:** Los primeros 2 millones de requests/mes son gratis en el free tier.

## Consideraciones Importantes

### 1. Tamaño de Imagen

La imagen Docker será grande (~5-7 GB) debido a:
- PyTorch y dependencias ML
- Archivos de voces (.pt files)

**Solución:** Cloud Run soporta imágenes hasta 32GB.

### 2. Cold Start

La primera petición después de un período de inactividad puede tardar 30-60 segundos porque:
- Cloud Run necesita iniciar el container
- El modelo necesita cargarse en memoria

**Soluciones:**
- Usar `--min-instances=1` para mantener una instancia siempre caliente (más caro)
- Implementar un "ping" periódico desde el cliente
- Usar Cloud Scheduler para hacer requests periódicos

### 3. WebSocket Timeout

Cloud Run tiene un timeout de 60 minutos para WebSocket connections.

### 4. Almacenamiento de Voces

Actualmente las voces se incluyen en la imagen Docker. Para optimizar:

**Opción A: Google Cloud Storage** (más eficiente)
```python
# Descargar voces bajo demanda desde GCS
from google.cloud import storage
```

**Opción B: Incluir en imagen** (más simple, actual)
- Ya está implementado
- Funciona bien para comenzar

## Troubleshooting

### Error: "Insufficient memory"

Aumenta la memoria:
```bash
gcloud run services update vibevoice-tts --memory=16Gi --region=$REGION
```

### Error: "Build timeout"

Aumenta el timeout en `cloudbuild.yaml`:
```yaml
timeout: '3600s'  # 1 hora
```

### Error: "WebSocket connection failed"

1. Verifica que estés usando `wss://` (no `ws://`)
2. Verifica que Cloud Run esté configurado con `--allow-unauthenticated`

### Logs para debugging

```bash
# Ver logs detallados
gcloud run services logs read vibevoice-tts --region=$REGION --limit=50
```

## Actualizar el Servicio

Para actualizar el código:

```bash
# Re-deploy
gcloud run deploy vibevoice-tts \
  --source . \
  --region=$REGION
```

Cloud Run automáticamente:
1. Crea una nueva versión
2. Migra el tráfico gradualmente
3. Mantiene la versión anterior por si necesitas rollback

## Rollback

Si algo sale mal:

```bash
# Ver revisiones
gcloud run revisions list --service=vibevoice-tts --region=$REGION

# Hacer rollback a una revisión anterior
gcloud run services update-traffic vibevoice-tts \
  --to-revisions=REVISION_NAME=100 \
  --region=$REGION
```

## Integración con Firebase

Para integrar con Firebase:

1. **Firebase Hosting** (para web client):
```bash
firebase init hosting
firebase deploy
```

2. **Firebase Authentication** (opcional):
```python
# En el backend, validar tokens de Firebase
from firebase_admin import auth
```

3. **Firestore** (para almacenar historial):
```python
from firebase_admin import firestore
```

## Próximos Pasos

1. **Implementar autenticación**: Proteger el endpoint con Firebase Auth
2. **Agregar rate limiting**: Limitar requests por usuario
3. **Implementar caching**: Cachear resultados frecuentes
4. **Métricas personalizadas**: Agregar Google Cloud Monitoring
5. **Multi-región**: Deployar en múltiples regiones para menor latencia

## Recursos Adicionales

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud Build Documentation](https://cloud.google.com/build/docs)
- [Firebase Documentation](https://firebase.google.com/docs)
- [VibeVoice GitHub](https://github.com/microsoft/VibeVoice)

## Soporte

Si encuentras problemas:

1. Revisa los logs: `gcloud run services logs read vibevoice-tts`
2. Verifica la configuración: `gcloud run services describe vibevoice-tts`
3. Consulta la documentación de Cloud Run
4. Abre un issue en el repositorio

---

Última actualización: Diciembre 2024
