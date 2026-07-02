import asyncio
import tempfile

from agents import AgentProtocol, AgentResult, AgentStatus
from agents.base import Agent
from agents.executor import ExecutorAgent
from agents.memory_agent import MemoryAgent
from agents.research import ResearchAgent
from core.context import TurnContext
from core.task import Task
from goals.models import Goal, Subtask
from goals.store import GoalStore
from modelgw import ModelGateway, ModelProvider, ModelProviderError, set_model_gateway
from services import GoalService


class EchoProvider(ModelProvider):
    name = "echo"

    def generate(self, *, model, system, prompt, temperature=0.2, options=None) -> str:
        return f"echo:{prompt}"


class FailingProvider(ModelProvider):
    name = "failing"

    def generate(self, *, model, system, prompt, temperature=0.2, options=None) -> str:
        raise ModelProviderError("backend unreachable")


def _with_failing_gateway():
    set_model_gateway(ModelGateway({"failing": FailingProvider()}, default="failing"))


class RecordingMemoryService:
    def __init__(self):
        self.writes = []

    def write(self, text, **kwargs):
        self.writes.append({"text": text, **kwargs})
        return "mem123"


def _with_echo_gateway():
    set_model_gateway(ModelGateway({"echo": EchoProvider()}, default="echo"))


def teardown_function():
    set_model_gateway(None)


def test_agents_satisfy_protocol():
    _with_echo_gateway()
    assert isinstance(ExecutorAgent(), AgentProtocol)
    assert isinstance(ResearchAgent(), AgentProtocol)


def test_executor_run_uses_working_context():
    _with_echo_gateway()
    agent = ExecutorAgent()
    task = Task(agent="executor", instruction="do the thing")
    ctx = TurnContext(working_context="CTX")
    result = asyncio.run(agent.run(task, ctx))
    assert result.status == AgentStatus.OK
    assert "do the thing" in result.output
    assert "CTX" in result.output


def test_research_run_uses_memory_results():
    _with_echo_gateway()
    agent = ResearchAgent()
    task = Task(agent="research", instruction="find facts")
    ctx = TurnContext(memory_results=[{"text": "fact-alpha"}, {"text": "fact-beta"}])
    result = asyncio.run(agent.run(task, ctx))
    assert "fact-alpha" in result.output
    assert "[1] fact-beta" in result.output


def test_memory_agent_run_completes_subtask():
    _with_echo_gateway()
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = f.name
    store = GoalStore(db_path=db)
    goal = Goal(description="g", subtasks=[Subtask(text="alpha")])
    store.upsert(goal)

    agent = MemoryAgent.__new__(MemoryAgent)  # skip Chroma construction
    agent.name, agent.model, agent.system_prompt = "memory", "m", "s"

    instr = f'COMPLETE_SUBTASK goal_id="{goal.id}" subtask="alpha"'
    ctx = TurnContext(goal_service=GoalService(store))
    result = asyncio.run(MemoryAgent.run(agent, Task(agent="memory", instruction=instr), ctx))
    assert result.output == f"acknowledged: {instr}"
    refreshed = store.get(goal.id)
    assert refreshed is not None and refreshed.subtasks[0].done


def test_memory_agent_run_no_matching_goal():
    agent = MemoryAgent.__new__(MemoryAgent)
    agent.name, agent.model, agent.system_prompt = "memory", "m", "s"
    instr = 'COMPLETE_SUBTASK goal_id="missing" subtask="nope"'
    ctx = TurnContext(goal_service=None)
    result = asyncio.run(MemoryAgent.run(agent, Task(agent="memory", instruction=instr), ctx))
    assert result.output.startswith("no matching goal/subtask")


def test_memory_agent_run_writes_through_service():
    agent = MemoryAgent.__new__(MemoryAgent)
    agent.name, agent.model, agent.system_prompt = "memory", "m", "s"
    service = RecordingMemoryService()
    ctx = TurnContext(session_id="s1", memory_service=service)
    result = asyncio.run(
        MemoryAgent.run(agent, Task(agent="memory", instruction="note this down"), ctx)
    )
    assert result.output == "memory.written id=mem123"
    assert service.writes[0]["text"] == "note this down"
    assert service.writes[0]["session_id"] == "s1"
    assert service.writes[0]["origin"] == "memory_agent"


def test_agent_result_defaults():
    r = AgentResult()
    assert r.status == AgentStatus.OK
    assert r.output == ""
    assert r.metadata == {}
    assert r.events == []


def test_base_agent_run_reports_error_status_on_provider_failure():
    """The core regression: a swallowed ModelProviderError must never look
    like a successful empty answer to the pipeline. AgentStatus.ERROR must
    actually be constructed and returned, not just defined and unused."""
    _with_failing_gateway()
    agent = Agent("generic", "m", "s")
    task = Task(agent="generic", instruction="do something")
    ctx = TurnContext()
    result = asyncio.run(agent.run(task, ctx))
    assert result.status == AgentStatus.ERROR
    assert "generic" in result.output
    assert "backend unreachable" in result.output


def test_executor_run_reports_error_status_on_provider_failure():
    _with_failing_gateway()
    agent = ExecutorAgent()
    task = Task(agent="executor", instruction="do the thing")
    ctx = TurnContext(working_context="CTX")
    result = asyncio.run(agent.run(task, ctx))
    assert result.status == AgentStatus.ERROR
    assert "executor" in result.output


def test_research_run_reports_error_status_on_provider_failure():
    _with_failing_gateway()
    agent = ResearchAgent()
    task = Task(agent="research", instruction="find facts")
    ctx = TurnContext(memory_results=[{"text": "fact-alpha"}])
    result = asyncio.run(agent.run(task, ctx))
    assert result.status == AgentStatus.ERROR
    assert "research" in result.output
