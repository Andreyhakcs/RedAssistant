# Red Assistant — Voice MVP (from scratch)

- Старт в **трей**, левый **красно‑неоновый эквалайзер** (Idle/Listening/Speaking).
- **Push‑to‑Talk**: удерживаешь кнопку «🎤 Hold to Talk» — запись; отпускаешь — распознаётся и отправляется в LLM.
- **STT**: по умолчанию OpenAI (`OPENAI_TRANSCRIBE_MODEL=whisper-1`). Можно включить **Vosk** оффлайн (см. `.env`).
- **TTS**: локально через `pyttsx3` (Windows SAPI5).

## Установка (Windows)
```bash
pip install -r requirements.txt
copy .env.template .env
# впиши OPENAI_API_KEY в .env
```
Рекомендуем Python 3.10–3.12.

## Запуск
```bash
python run.py
# или
python -m red2
```

## Настройки
- `prompts/system_prompt.txt` — стиль Red.
- `.env` — ключи и модели (`OPENAI_MODEL`, `OPENAI_TRANSCRIBE_MODEL`).
- Для оффлайн STT скачай модель Vosk (например, ru-small), укажи путь в `VOSK_MODEL_PATH`, и поставь `pip install vosk`.

## Дальше
Смотри `prompts/SCALING.md` — там готовые промты для развития проекта.
