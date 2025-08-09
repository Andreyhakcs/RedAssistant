
Online-голоса (Edge TTS) для RedAssistant
-----------------------------------------
Что это:
- Добавляет движок **Edge (online)** с голосами Microsoft (без ключа).
- Работает на Windows, генерит WAV и проигрывает системно.
- Можно переключаться между **edge** и **system** голосами в Settings.

Установка (очень просто):
1) Распакуй архив в КОРЕНЬ проекта **с заменой**.
   Обновятся/добавятся файлы:
   - red2/ui/user_prefs.py
   - red2/ui/settings_dialog.py
   - red2/core/tts_edge.py
   - red2/app_tts_engine_snippet.txt (помощник для app.py)
2) Открой `red2/app.py` и замени создание TTS на хелпер `_make_tts_from_prefs(...)`.
   Вставь код из файла `red2/app_tts_engine_snippet.txt` (в любом месте, выше использования).
3) Один раз установи библиотеку голосов:
   `py -m pip install edge-tts`
4) Запусти `py -m red2`. В Settings выбери:
   - TTS Engine: **edge**
   - TTS Voice: **ru-RU-SvetlanaNeural** (или любой другой)
   Нажми **Test TTS**.

Если звука нет:
- Проверь, что `edge-tts` установлен (см. п.3).
- Голос сменил — перезапускать не надо, достаточно нажать Save.
- На редких системах нужно добавить `playsound` как запасной путь: `py -m pip install playsound`.
