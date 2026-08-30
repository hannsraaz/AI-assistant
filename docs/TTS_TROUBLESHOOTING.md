# FRIDAY TTS Troubleshooting Guide

---

## Common Issues & Solutions

### 1. "Speech sounds like English text reading Hindi"
- **Cause:** `HINGLISH_ENABLED` is disabled or word is missing from transliteration dictionary.
- **Fix:** Ensure `hinglish_enabled = True` in `config.py`. Add missing words or phonetic overrides to `data/language/hinglish_dictionary.json` or `data/language/pronunciation_dictionary.json`.

### 2. "Technical word (like GitHub or VS Code) was pronounced weirdly"
- **Fix:** Check `data/language/pronunciation_dictionary.json` and add an exact phonetic spelling (e.g. `"GitHub": "Git Hub"`, `"VS Code": "V S Code"`).

### 3. "Piper voice model fails to load"
- **Fix:** Run `.\.venv\Scripts\python -c "from audio_tts import prepare_tts_assets, TTSConfig; prepare_tts_assets(TTSConfig())"` while online once to download the 60MB ONNX assets into `data/piper/`. Once downloaded, FRIDAY runs 100% offline.

### 4. "No audio output on speaker"
- **Fix:** Check `sounddevice.query_devices()` to ensure the default Windows audio output device is active and not muted.

### 5. "Audio is speaking too fast or too slow"
- **Fix:** Adjust `rate` or `piper_length_scale` in `config.py` (e.g. `piper_length_scale = 1.0` is normal speed, `1.15` is slower, `0.85` is faster).
