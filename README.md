# Sikiliza

Realtime captions for TikTok Live on Ubuntu — strong for Swahili/Sheng, with auto language detection fallbacks.

Phone speaker into a laptop mic is the wrong path. Join the **same live in Chrome on this laptop**, link that tab, and watch it inside Sikiliza with captions floating on the stage.

## What to do in the live

1. Put keys in `.env`:
   - `GEMINI_API_KEY` — default STT + translation
   - optional `INTRON_API_KEY` — Swahili streaming STT when `SIKILIZA_PROVIDER=intron`
   - optional `GROQ_API_KEY` / `OPENAI_API_KEY`
2. Run `./scripts/dev.sh` and open http://127.0.0.1:5273
3. In Chrome, open the TikTok live.
4. In Sikiliza, click **Link tab**. Choose that Chrome tab and tick **Share tab audio**.
5. Click **Start**. Captions float on the shared stage.

Use **Use mic instead** only if you cannot open the live on the laptop. Expect missed words.

## Providers

Default in `.env.example` is `SIKILIZA_PROVIDER=gemini`.

`SIKILIZA_PROVIDER=auto` prefers:

1. **Gemini** — multilingual STT + translation (most reliable today)
2. **Groq** / **OpenAI**
3. **Intron** — African / Swahili-English streaming STT (opt-in via `SIKILIZA_PROVIDER=intron`)
4. local Whisper

Intron needs a language code up front (`sw`, `fr`, `en`, …). See [supported languages](https://docs.voice.intron.io/docs/stt/supported-languages). Its gateway currently mis-handles compressed WebSockets; use Gemini unless you explicitly want Intron.

## Tests

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest --cov=app --cov-fail-under=80

cd web && npm install && npm test
```
