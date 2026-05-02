---
name: voice-loop
description: Run a local voice loop on this Windows machine by recording microphone audio, transcribing it, generating a simple spoken reply, and playing that reply through the speaker. Use when the assistant needs a quick offline-style listen-and-respond loop, hands-free local interaction, or a baseline voice companion workflow before adding richer real-time orchestration.
---

# Voice Loop

Use the bundled Python script to run a single-turn voice interaction: record -> transcribe -> reply -> speak.

## Quick start

Run a default Chinese confirmation loop:

```powershell
python skills\voice-loop\scripts\voice_loop.py --seconds 4
```

Echo back what was heard:

```powershell
python skills\voice-loop\scripts\voice_loop.py --seconds 4 --reply-mode echo
```

Always speak a fixed sentence after listening:

```powershell
python skills\voice-loop\scripts\voice_loop.py --seconds 4 --reply-mode literal --reply-text "你好，我已经收到你的话了。"
```

## Behavior

1. Record microphone audio to a WAV file under `state\`.
2. Transcribe that recording with the shared audio transcription module.
3. Build a simple reply:
   - `confirm`: repeat back in confirmation form
   - `echo`: echo back directly
   - `literal`: ignore transcription and speak the provided fixed text
4. Speak the reply through the default speaker.
5. Print a JSON result that includes recording metadata, transcription text, and the spoken reply.

## Notes

- This is a single-turn loop, not full duplex or streaming conversation.
- It depends on `skills\audio-io\scripts\audio_core.py` for shared audio primitives.
- Use `--fallback-reply` to control what gets spoken when transcription is empty.
- Keep recordings short first; that makes verification faster and avoids long dead-air loops.
