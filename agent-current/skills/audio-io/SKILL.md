---
name: audio-io
description: Record microphone audio, enumerate local audio devices, transcribe short recordings, and speak text through the local speaker on this Windows machine. Use when the assistant needs microphone input, a quick speech-to-text loop, text-to-speech playback, or a lightweight audio device check before building richer voice workflows.
---

# Audio IO

Use the bundled Python script for local microphone, transcription, and speech output tasks.

## Quick start

List audio devices:

```powershell
python skills\audio-io\scripts\audio_io.py list
```

Record a short WAV file from the default input:

```powershell
python skills\audio-io\scripts\audio_io.py record state\mic.wav --seconds 3
```

Transcribe that recording:

```powershell
python skills\audio-io\scripts\audio_io.py transcribe state\mic.wav --language zh
```

Speak text through the default output:

```powershell
python skills\audio-io\scripts\audio_io.py speak --text "你好，我是the agent。"
```

Optionally save TTS output to a file:

```powershell
python skills\audio-io\scripts\audio_io.py speak --text "测试语音" --save-to state\tts.wav
```

## Workflow

1. Run `list` if device selection matters.
2. Use `record` for short captures first and check the returned `peak` value.
3. Use `transcribe` on the saved WAV when text is needed.
4. Use `speak` for direct local playback or save-to-file generation.

## Notes

- `record` writes PCM WAV files.
- `transcribe` uses `faster-whisper` with the local `tiny` model on CPU for a small, fast baseline.
- `speak` uses `pyttsx3`, so available voices depend on the Windows voices installed on this machine.
- If Chinese text prints as mojibake in the terminal, the JSON may still be structurally valid; verify via file content or downstream use.
