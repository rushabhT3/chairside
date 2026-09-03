from chairside_agent.agents.consultation import ConsultationAgent, ConsultOptions
from chairside_agent.agents.runtime import Runtime
from chairside_agent.main import replay
from chairside_agent.replay import project


async def test_replay_matches_stored_projection(rt: Runtime) -> None:
    p = await ConsultationAgent(rt).run(ConsultOptions(client_id="cl-01"))

    assert replay(rt, p["id"]) == 0
    assert project(p["id"], rt.ledger.read_events(p["id"])) == rt.projections.load(p["id"])


async def test_replay_detects_tampered_projection(rt: Runtime, capsys) -> None:
    p = await ConsultationAgent(rt).run(ConsultOptions(client_id="cl-01"))
    stored = rt.projections.load(p["id"])
    stored["order"]["total_cents"] += 1
    rt.projections.save(p["id"], stored)

    assert replay(rt, p["id"]) == 1
    assert "total_cents" in capsys.readouterr().out
