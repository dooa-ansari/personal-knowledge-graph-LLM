"""LangGraph workflow for session-aware semantic RAG conversations."""

from typing import TypedDict

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from .model_config import DEFAULT_MODEL
from .openrouter_service import query_openrouter
from .vector_search_service import search_semantic


RAG_CONVERSATION_SYSTEM_PROMPT = """
You answer questions using only the supplied resume context and conversation.
Use conversation history to resolve references such as "there", "that role",
or "what about next?", but do not treat history as resume facts unless those
facts are also present in the retrieved context.
If the retrieved context does not answer the question, say so clearly.
Return only a concise natural-language answer.
""".strip()


class RagGraphState(TypedDict):
    messages: list
    retrieved_chunks: list
    answer: str


def _retrieve_node(state: RagGraphState) -> RagGraphState:
    retrieval_query = "\n".join(
        message.content for message in state["messages"][-4:]
    )
    state["retrieved_chunks"] = search_semantic(retrieval_query)
    return state


def _answer_node(state: RagGraphState) -> RagGraphState:
    latest_question = next(
        message.content
        for message in reversed(state["messages"])
        if isinstance(message, HumanMessage)
    )
    context = "\n\n".join(
        f"Context {index}: {chunk['document']}"
        for index, chunk in enumerate(state["retrieved_chunks"], start=1)
    ) or "No matching resume context was retrieved."
    history = "\n".join(
        f"{message.type}: {message.content}"
        for message in state["messages"][:-1]
    )
    prompt = (
        f"Conversation history:\n{history or '(none)'}\n\n"
        f"Current question: {latest_question}\n\n"
        f"Retrieved resume context:\n{context}\n\n"
        "Answer using only the retrieved context."
    )
    answer = query_openrouter(
        prompt,
        model=DEFAULT_MODEL,
        system_prompt=RAG_CONVERSATION_SYSTEM_PROMPT,
    ).strip()
    state["answer"] = answer
    state["messages"].append(AIMessage(content=answer))
    return state


def _build_workflow():
    workflow = StateGraph(RagGraphState)
    workflow.add_node("retrieve", _retrieve_node)
    workflow.add_node("answer", _answer_node)
    workflow.add_edge("retrieve", "answer")
    workflow.add_edge("answer", END)
    workflow.set_entry_point("retrieve")
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
        "model": DEFAULT_MODEL,
        "answer": result["answer"],
        "retrieved_chunks": result["retrieved_chunks"],
    }