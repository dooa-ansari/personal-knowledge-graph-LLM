"""LangGraph workflow for session-aware semantic RAG conversations.

Delegates core logic to the SearchRagUseCase via the DI container,
while LangGraph handles session state persistence via MemorySaver.
"""

from typing import TypedDict

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from resume_api.interfaces.container import container


class RagGraphState(TypedDict):
    messages: list
    retrieval_query: str
    retrieved_chunks: list
    answer: str


def _rewrite_query_node(state: RagGraphState) -> RagGraphState:
    use_case = container.search_rag_use_case
    latest_question = next(
        message.content
        for message in reversed(state["messages"])
        if isinstance(message, HumanMessage)
    )
    history = "\n".join(
        f"{message.type}: {message.content}"
        for message in state["messages"][:-1]
    )
    state["retrieval_query"] = use_case.rewrite_query(latest_question, history)
    return state


def _retrieve_node(state: RagGraphState) -> RagGraphState:
    use_case = container.search_rag_use_case
    state["retrieved_chunks"] = use_case.retrieve(state["retrieval_query"])
    return state


def _answer_node(state: RagGraphState) -> RagGraphState:
    use_case = container.search_rag_use_case
    latest_question = next(
        message.content
        for message in reversed(state["messages"])
        if isinstance(message, HumanMessage)
    )
    history = "\n".join(
        f"{message.type}: {message.content}"
        for message in state["messages"][:-1]
    )
    state["answer"] = use_case.answer(latest_question, history, state["retrieved_chunks"])
    state["messages"].append(AIMessage(content=state["answer"]))
    return state


def _build_workflow():
    workflow = StateGraph(RagGraphState)
    workflow.add_node("rewrite_query", _rewrite_query_node)
    workflow.add_node("retrieve", _retrieve_node)
    workflow.add_node("answer", _answer_node)
    workflow.add_edge("rewrite_query", "retrieve")
    workflow.add_edge("retrieve", "answer")
    workflow.add_edge("answer", END)
    workflow.set_entry_point("rewrite_query")
    return workflow.compile(checkpointer=MemorySaver())


_workflow = _build_workflow()


def search_rag_with_context(session_id: str, prompt: str) -> dict:
    """Run a session-aware RAG turn and return answer plus retrieved chunks."""
    if not session_id:
        raise ValueError("Session ID is required.")
    if not prompt.strip():
        raise ValueError("Prompt is required.")

    config = {"configurable": {"thread_id": session_id}}
    checkpoint = _workflow.get_state(config)
    messages = list(checkpoint.values.get("messages", [])) if checkpoint.values else []
    messages.append(HumanMessage(content=prompt.strip()))
    result = _workflow.invoke({"messages": messages}, config=config)
    return {
        "prompt": prompt.strip(),
        "session_id": session_id,
        "model": container.search_rag_use_case.model,
        "retrieval_query": result["retrieval_query"],
        "answer": result["answer"],
        "retrieved_chunks": result["retrieved_chunks"],
    }