"""One valid Exec per action reaches its stub handler."""
from executor.dispatch import HANDLERS, dispatch
from harness.contracts import ACTIONS, Exec


def test_registry_covers_all_actions():
    assert set(HANDLERS) == set(ACTIONS) and len(HANDLERS) == len(ACTIONS)


def test_route_all_actions():
    for action in ACTIONS:
        res = dispatch(Exec(action=action, args={}))
        assert res.code == 200
        assert action in res.detail


def test_routing_hits_correct_handler():
    seen = []
    for action in ACTIONS:
        def make(a):
            def h(args):
                from harness.contracts import Result
                seen.append(a)
                return Result(code=200, detail=f"marker:{a}")
            return h
        import executor.dispatch as d
        old = d.HANDLERS[action]
        d.HANDLERS[action] = make(action)
        try:
            res = dispatch(Exec(action=action, args={"x": 1}))
            assert res.detail == f"marker:{action}"
        finally:
            d.HANDLERS[action] = old
    assert sorted(seen) == sorted(ACTIONS)


def test_dict_input_routed():
    res = dispatch({"action": "volume", "args": {"level": 50}})
    assert res.code == 200
