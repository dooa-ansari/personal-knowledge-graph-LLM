"""
LangGraph service for conversational knowledge graph search.

This module implements a LangGraph workflow that maintains conversation
context across multiple user queries, enabling follow-up questions that
reference previous context (e.g., "What did she do there?" after asking
"When did Dooa work at Greator?").
"""

from typing import TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from django.conf import settings

from ..prompts import (
    NATURAL_LANGUAGE_SYSTEM_PROMPT,
    SPARQL_SYSTEM_PROMPT,
    build_results_prompt,
)
from .sparql_service import execute_sparql_query

# The default model used for LLM calls
DEFAULT_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"


def _get_llm() -> ChatOpenAI:
    """
    Create a ChatOpenAI instance configured to use the OpenRouter API.

    Returns:
        A ChatOpenAI instance pointed at the OpenRouter chat completions endpoint.
    """
    return ChatOpenAI(
        model=DEFAULT_MODEL,
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
    )


class GraphState(TypedDict):
    """State for the knowledge graph search workflow."""

    messages: list  # Conversation history (HumanMessage / AIMessage)
    sparql_query: str
    query_results: dict
    answer: str


def _generate_sparql_node(state: GraphState) -> GraphState:
    """
    Node that generates a SPARQL query from the conversation history.

    The full conversation history is passed to the LLM so it can resolve
    references like "she" or "there" from previous turns.
    """
    llm = _get_llm()

    # Build messages: system prompt + conversation history
    messages = [SystemMessage(content=SPARQL_SYSTEM_PROMPT)]
    messages.extend(state["messages"])

    response = llm.invoke(messages)
    sparql_query = response.content.strip()

    state["sparql_query"] = sparql_query
    return state


def _execute_sparql_node(state: GraphState) -> GraphState:
    """Node that executes the generated SPARQL query against the RDF graph."""
    query_results = execute_sparql_query(state["sparql_query"])
    state["query_results"] = query_results
    return state


def _generate_answer_node(state: GraphState) -> GraphState:
    """
    Node that converts SPARQL results into a natural language answer.

    The conversation history is included so the LLM can phrase the answer
    in context of the ongoing conversation.
    """
    llm = _get_llm()

    # Build the results prompt using the latest user question
    latest_user_message = state["messages"][-1].content
    results_prompt = build_results_prompt(latest_user_message, state["query_results"])

    # Build messages: system prompt + conversation history + results prompt
    messages = [SystemMessage(content=NATURAL_LANGUAGE_SYSTEM_PROMPT)]
    messages.extend(state["messages"])
    messages.append(HumanMessage(content=results_prompt))

    response = llm.invoke(messages)
    answer = response.content.strip()

    state["answer"] = answer
    # Append the AI response to the conversation history for future turns
    state["messages"].append(AIMessage(content=answer))

    return state


def _build_workflow():
    """Build and return the compiled LangGraph workflow."""
    workflow = StateGraph(GraphState)

    workflow.add_node("generate_sparql", _generate_sparql_node)
    workflow.add_node("execute_sparql", _execute_sparql_node)
    workflow.add_node("generate_answer", _generate_answer_node)

    workflow.add_edge("generate_sparql", "execute_sparql")
    workflow.add_edge("execute_sparql", "generate_answer")
    workflow.add_edge("generate_answer", END)

    workflow.set_entry_point("generate_sparql")

    return workflow


# Module-level instances — the workflow and memory saver are created once
# and reused across requests.
_memory_saver = MemorySaver()
_workflow = _build_workflow()
_compiled_workflow = _workflow.compile(checkpointer=_memory_saver)


def search_with_context(session_id: str, prompt: str) -> dict:
    """
    Search the knowledge graph with conversation context.

    This function retrieves any existing conversation history for the given
    session, appends the new user question, runs the LangGraph workflow, and
    returns the results. The conversation state is persisted in-memory by the
    MemorySaver checkpointer, keyed by ``session_id``.

    Args:
        session_id: Unique identifier for the conversation session.
        prompt: The user's natural language question.

    Returns:
        A dict containing:
        - prompt: The user's prompt
        - session_id: The session identifier
        - model: The model used
        - sparql_query: The generated SPARQL query
        - query_results: The raw SPARQL query results
        - answer: The natural language answer

    Raises:
        ValueError: If the API key is not configured.
        FileNotFoundError: If the RDF file doesn't exist.
        Exception: If the workflow execution fails.
    """
    if not settings.OPENROUTER_API_KEY or settings.OPENROUTER_API_KEY == "your-openrouter-api-key-here":
        raise ValueError(
            "OpenRouter API key is not configured. Set OPENROUTER_API_KEY in your .env file."
        )

    config = {"configurable": {"thread_id": session_id}}

    # Retrieve existing conversation state (if any)
    try:
        checkpoint = _compiled_workflow.get_state(config)
        if checkpoint.values:
            messages = checkpoint.values.get("messages", [])
        else:
            messages = []
    except Exception:
        messages = []

    # Append the new user message
    messages.append(HumanMessage(content=prompt))

    # Run the workflow
    result = _compiled_workflow.invoke(
        {"messages": messages},
        config=config,
    )

    return {
        "prompt": prompt,
        "session_id": session_id,
        "model": DEFAULT_MODEL,
        "sparql_query": result["sparql_query"],
        "query_results": result["query_results"],
        "answer": result["answer"],
    }