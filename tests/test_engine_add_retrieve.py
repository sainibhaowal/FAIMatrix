from faim.core.engine import FAIMEngine


def test_engine_add_and_retrieve_deterministic():
    engine = FAIMEngine()
    g = "test_graph"

    ids: list[str] = []
    for payload in ["hello world", "hello again", "another message"]:
        nid = engine.add_memory(g, payload, meta={})
        ids.append(str(nid))

    first = [n.id for n in engine.retrieve(g, "hello", k=2)]
    second = [n.id for n in engine.retrieve(g, "hello", k=2)]

    assert first == second
    assert len(first) == 2
