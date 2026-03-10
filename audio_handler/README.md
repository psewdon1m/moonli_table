# audio_handler

Independent service for forwarding uploaded audio files to an n8n webhook.

## Run

```powershell
cd audio_handler
docker compose up -d --build
```

Service URL: `http://localhost:8091`

## Endpoints

- `GET /health`
- `POST /audio/forward` (multipart/form-data)
  - `file` (required, audio file)
  - `session_id` (optional)
  - `user_id` (optional)

## Notes

- Max payload is controlled by `MAX_PAYLOAD_BYTES` and defaults to `16777216` (16 MB).
- Files larger than limit return `413`.
