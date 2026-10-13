# tests/voice-check/ — is it the mic or the pipeline?

Interactive diagnostic. It tells you what to say, records your voice, then
runs the REAL chain on the recording (VAD → STT → buffer → decide).

```
# 1. record one wav per phrase (prompts you, Enter to start/stop each)
.venv/bin/python tests/voice-check/voice_check.py --collect tests/voice-check/samples
# 2. run the pipeline on all of them (dry-run; --act really dispatches)
.venv/bin/python tests/voice-check/voice_check.py --analyze-dir tests/voice-check/samples
# single-shot variants
.venv/bin/python tests/voice-check/voice_check.py --wav path/to/clip.wav
.venv/bin/python tests/voice-check/voice_check.py --list-mics
.venv/bin/python tests/voice-check/voice_check.py --mic-target bluez_input.… --collect tests/voice-check/samples-bt
```

Dry-run by default: nothing touches your desktop. Needs a model server
(:8081 or :8080) for the decide step, else it stops after STT with that verdict.
