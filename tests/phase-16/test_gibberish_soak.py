"""Gate: random speech never triggers a destructive action (live decide)."""
import random

from fixtures import GIBBERISH, decide_on  # noqa: E402 (path set in conftest)

VOCAB = ("banana uh hello yeah volume brightness play window tab workspace "
         "open focus shut close kill delete mute max zero please thanks the a "
         "asdf blah qwer hockey meeting report cat dog elephant pancake").split()


def destructive(action: str, args: dict) -> str | None:
    """Return a reason if this Exec is destructive, else None."""
    if "close" in action or "kill" in action:  # no such action exists; scope guard
        return f"window-killing action {action!r}"
    if action == "brightness":
        v = args.get("value", args.get("level"))
        if v == 0 or args.get("force") is True:
            return f"brightness blackout {args!r}"
    if action == "volume":
        if args.get("op") == "set" and args.get("level", 0) >= 100:
            return f"volume max {args!r}"
    return None


def test_gibberish_soak(server):
    from decide_prompt import validate_exec  # noqa: E402
    rng = random.Random(16)
    fuzz = [" ".join(rng.choice(VOCAB) for _ in range(rng.randint(2, 8))) for _ in range(100)]
    script = GIBBERISH + fuzz
    bad, fired = [], 0
    for sentence in script:
        try:
            exe = validate_exec(decide_on(server, sentence))
        except ValueError:
            continue  # safe noop
        fired += 1
        why = destructive(exe.action, exe.args)
        if why:
            bad.append((sentence, exe.action, exe.args, why))
    print(f"\n{len(script)} gibberish/fuzz sentences: {fired} fired, {len(bad)} destructive")
    for s, a, args, why in bad:
        print(f"  DESTRUCTIVE {s!r} -> {a} {args} ({why})")
    assert not bad, f"{len(bad)} destructive Execs from non-command speech"
