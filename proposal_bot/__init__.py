"""
Proposal Bot - LangChain Deep Agent System for Market Research Proposals

A sophisticated multi-agent system that automates the creation of market research proposals
using LangChain's Deep Agents pattern and LangGraph orchestration.
"""

__version__ = "1.0.0"

# Provide compatibility shim for deepagents
from langchain.agents import AgentType, initialize_agent
from langchain_core.language_models import BaseLanguageModel
from langchain_core.tools import BaseTool


def create_deep_agent(
    model: BaseLanguageModel,
    tools: list[BaseTool],
    system_prompt: str,
    **kwargs
):
    """
    Shim for deepagents.create_deep_agent using LangChain's initialize_agent.

    This provides basic compatibility while the system is being updated.
    """
    # Use LangChain 0.3.x's initialize_agent function
    # Ignore checkpointer and interrupt_on parameters as they're not supported in this version
    filtered_kwargs = {k: v for k, v in kwargs.items()
                       if k not in ['checkpointer', 'interrupt_on', 'backend']}

    # Create agent with error handling enabled
    agent = initialize_agent(
        tools=tools,
        llm=model,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        handle_parsing_errors=True,  # Enable error recovery
        **filtered_kwargs
    )

    return agent


# Import other modules for convenience
from . import agents, graphs, schemas, tools