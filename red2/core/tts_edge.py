
from __future__ import annotations
import asyncio, threading, tempfile, os, time
from typing import Optional, Callable

# Онлайн TTS через Microsoft Edge (edge-tts).
# Совместим с версиями edge-tts, где Communicate.save() НЕ принимает параметр 'format'.
# Сохраняем MP3 и пытаемся воспроизвести:
# 1) playsound (если установлен)
# 2) os.startfile (дефолтный плеер Windows) — как запасной вариант

class TTS:
    def __init__(self, rate:int=175, volume:float=0.9, voice:str='ru-RU-SvetlanaNeural'):
        self.rate = int(rate)
        self.volume = float(volume)
        self.voice = voice or 'ru-RU-SvetlanaNeural'
        self._th = None
        self._stop = False

    def set_voice(self, voice_id: str):
        if voice_id:
            self.voice = voice_id

    def _edge_rate(self) -> str:
        pct = int(max(-25, min(25, (self.rate - 175) * 0.5)))
        return f"{'+' if pct >= 0 else ''}{pct}%"

    def _edge_vol(self) -> str:
        pct = int(max(-10, min(10, (self.volume - 0.9) * 50)))
        return f"{'+' if pct >= 0 else ''}{pct}%"

    def speak(self, text: str, on_done: Optional[Callable] = None):
        self.stop()
        self._stop = False
        self._th = threading.Thread(target=self._run_speak, args=(text, on_done), daemon=True)
        self._th.start()

    def stop(self):
        self._stop = True
        # Если playsound используется, остановки нет — просто не стартуем новое поверх

    def _run_speak(self, text: str, on_done: Optional[Callable]):
        try:
            import edge_tts
        except Exception as e:
            print("Edge TTS import error:", e)
            if on_done: on_done()
            return

        fd, path = tempfile.mkstemp(prefix="red_edge_tts_", suffix=".mp3")
        os.close(fd)

        async def _synth():
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=self._edge_rate(),
                volume=self._edge_vol(),
            )
            await communicate.save(path)  # без параметра 'format' (совместимо)

        try:
            asyncio.run(_synth())
            if self._stop:
                if on_done: on_done()
                return

            # 1) пытаемся playsound
            try:
                from playsound import playsound  # советую: pip install playsound==1.2.2
                playsound(path, block=True)
                try:
                    os.remove(path)
                except Exception:
                    pass
                if on_done: on_done()
                return
            except Exception as e:
                print("playsound not available or failed:", e)

            # 2) запасной вариант — открыть системным плеером
            try:
                os.startfile(path)  # асинхронно; пользовательский плеер сам закроет
                # запланируем удаление через 60 сек, чтобы файл не копился
                def _del_later(p):
                    time.sleep(60)
                    try: os.remove(p)
                    except Exception: pass
                threading.Thread(target=_del_later, args=(path,), daemon=True).start()
            except Exception as e:
                print("Fallback open error:", e)
        except Exception as e:
            print("Edge TTS error:", e)
        finally:
            if on_done: on_done()
