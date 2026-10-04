from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import get_settings
from app.models import AudioWindow
from app.pipeline import LivePipeline
from app.providers.factory import create_provider, is_configured, resolve_provider_name

logger = logging.getLogger(__name__)
router = APIRouter()

# Keep at most one backlog utterance so live captions stay near realtime.
_MAX_JOBS = 1


@router.websocket("/ws")
async def caption_stream(socket: WebSocket) -> None:
    await socket.accept()
    settings = get_settings()
    provider_name = resolve_provider_name(settings)
    target_language = settings.target_language

    if not is_configured(settings):
        await socket.send_json(
            {
                "type": "error",
                "code": "NOT_CONFIGURED",
                "message": (
                    "Add INTRON_API_KEY, GEMINI_API_KEY, GROQ_API_KEY, or OPENAI_API_KEY to .env, then restart."
                ),
            }
        )
        await socket.close(code=1008)
        return

    try:
        provider = create_provider(settings, target_language=target_language)
    except Exception as exc:
        logger.exception("Failed to create speech provider")
        await socket.send_json(
            {
                "type": "error",
                "code": "PROVIDER_INIT",
                "message": str(exc),
            }
        )
        await socket.close(code=1011)
        return

    pipeline = LivePipeline(provider=provider, mode=settings.mode)
    await socket.send_json(
        {
            "type": "ready",
            "provider": provider_name,
            "mode": settings.mode,
            "targetLanguage": target_language,
        }
    )

    outbound: asyncio.Queue[dict | None] = asyncio.Queue()
    jobs: asyncio.Queue[AudioWindow | None] = asyncio.Queue(maxsize=_MAX_JOBS)
    stop = asyncio.Event()

    async def sender() -> None:
        while True:
            event = await outbound.get()
            if event is None:
                break
            try:
                await socket.send_json(event)
            except Exception:
                logger.debug("Could not send caption event; socket likely closed")
                stop.set()
                break

    async def worker() -> None:
        processing = False
        while not stop.is_set():
            try:
                window = await asyncio.wait_for(jobs.get(), timeout=0.4)
            except asyncio.TimeoutError:
                continue
            if window is None:
                break
            if not processing:
                await outbound.put({"type": "status", "speaking": False, "processing": True})
                processing = True
            for event in await pipeline.process_window(window):
                await outbound.put(event)
            if jobs.empty():
                await outbound.put(
                    {
                        "type": "status",
                        "speaking": pipeline.in_speech,
                        "processing": False,
                    }
                )
                processing = False

    def offer_job(window: AudioWindow) -> None:
        """Prefer the newest utterance when the provider is behind."""
        if jobs.full():
            try:
                jobs.get_nowait()
            except asyncio.QueueEmpty:
                pass
        try:
            jobs.put_nowait(window)
        except asyncio.QueueFull:
            logger.debug("Dropped caption job; provider still busy")

    sender_task = asyncio.create_task(sender(), name="caption-sender")
    worker_task = asyncio.create_task(worker(), name="caption-worker")

    try:
        while True:
            message = await socket.receive()
            if message["type"] == "websocket.disconnect":
                break

            if message.get("bytes"):
                status_events, windows = pipeline.feed(message["bytes"])
                for event in status_events:
                    await outbound.put(event)
                for window in windows:
                    offer_job(window)
                continue

            text = message.get("text")
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                await outbound.put(
                    {
                        "type": "error",
                        "code": "BAD_MESSAGE",
                        "message": "Client sent invalid JSON.",
                    }
                )
                continue

            if payload.get("type") == "config":
                next_target = str(payload.get("targetLanguage") or target_language).strip().lower()
                if next_target and next_target != target_language:
                    target_language = next_target
                    provider = create_provider(settings, target_language=target_language)
                    pipeline = LivePipeline(provider=provider, mode=settings.mode)
                    # Drop stale jobs for the previous language.
                    while not jobs.empty():
                        try:
                            jobs.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                    await outbound.put(
                        {
                            "type": "ready",
                            "provider": provider_name,
                            "mode": settings.mode,
                            "targetLanguage": target_language,
                        }
                    )
                continue

            if payload.get("type") == "stop":
                for event in await pipeline.flush():
                    await outbound.put(event)
                break
    except WebSocketDisconnect:
        logger.info("Caption client disconnected")
    except Exception:
        logger.exception("Caption stream failed")
        try:
            await outbound.put(
                {
                    "type": "error",
                    "code": "STREAM_FAILED",
                    "message": "Live caption stream crashed. Refresh and start again.",
                }
            )
        except Exception:
            logger.debug("Could not notify client after stream failure")
    finally:
        stop.set()
        try:
            jobs.put_nowait(None)
        except asyncio.QueueFull:
            try:
                jobs.get_nowait()
            except asyncio.QueueEmpty:
                pass
            try:
                jobs.put_nowait(None)
            except asyncio.QueueFull:
                pass
        await outbound.put(None)
        await asyncio.gather(worker_task, sender_task, return_exceptions=True)
