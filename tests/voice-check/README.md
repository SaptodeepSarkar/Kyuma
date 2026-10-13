# tests/voice-check/ — is it the mic or the pipeline?

Interactive diagnostic. It tells you what to say, records your voice, then
runs the REAL chain on the recording (VAD → STT → buffer → decide).

```
.venv/bin/python tests/voice-check/voice_check.py [--case 0|1|2] [--seconds 4]
.venv/bin/python tests/voice-check/voice_check.py --list-mics
.venv/bin/python tests/voice-check/voice_check.py --mic-target bluez_input.… --case 1
.venv/bin/python tests/voice-check/voice_check.py --wav path/to/clip.wav  # no mic needed
.venv/bin/python tests/voice-check/voice_check.py --act  # REALLY dispatch (acts on desktop)
```

Dry-run by default: nothing touches your desktop. Needs a model server
(:8081 or :8080) for the decide step, else it stops after STT with that verdict.
