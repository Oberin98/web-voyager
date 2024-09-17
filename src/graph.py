import asyncio

from typing import Literal

from playwright.async_api import async_playwright

from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, SystemMessage
from langgraph.graph import StateGraph, START, END

from state import AgentState, Nodes, Actions
from actions import action_tools, action_nodes
from prompt import prompt
from utils.mark_page import mark_page
from utils.patch_asyncio import patch_asyncio

patch_asyncio()


#
# Annotate ineractive elements on the page with numerical labels
# TODO - Refactor into a separate node to avoid redundant calls in case when no action is selected
#


async def annotate_page(state: AgentState):
    await asyncio.sleep(3)
    marked_page = await mark_page.with_retry().ainvoke(state["page"])
    return {**state, **marked_page}


#
# Parse agent output to AgentState's action field format
#


def parse_agent_output(message: AIMessage):
    answer_prefix = "ANSWER:"

    if message.content.startswith(answer_prefix):
        return {
            "action": {
                "type": Actions.END,
                "args": {"answer": message.content[len(answer_prefix) :].strip()},
            }
        }

    if hasattr(message, "tool_calls"):
        tool_call = message.tool_calls[0]
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        tool_to_action_mapping = {
            "click_tool": Actions.CLICK,
            "type_tool": Actions.TYPE,
            "scroll_tool": Actions.SCROLL,
            "wait_tool": Actions.WAIT,
            "go_back_tool": Actions.GO_BACK,
            "go_to_google_tool": Actions.GO_TO_GOOGLE,
        }

        action_type = tool_to_action_mapping.get(tool_name)

        if action_type is not None:
            return {"action": {"type": action_type, "args": tool_args}}
        else:
            return {
                "action": {
                    "type": Actions.RETRY,
                    "args": {"message": f"""Invalid tool call: {tool_name}"""},
                }
            }

    return {
        "action": {
            "type": Actions.RETRY,
            "args": {
                "message": f"""No action selected. Please select a valid action to proceed with the task."""
            },
        }
    }


#
# Define agent node
#

llm = ChatOpenAI(model="gpt-4o").bind_tools(
    [
        action_tools.get("click"),
        action_tools.get("type"),
        action_tools.get("scroll"),
        action_tools.get("wait"),
        action_tools.get("go_back"),
        action_tools.get("go_to_google"),
    ]
)

agent_node = annotate_page | prompt | llm | parse_agent_output


#
# Define node to map previous agent's actions to string descriptions to be used as context in the prompt
#


# TODO - parse retry action args message to be a part of the history
def history_node(state: AgentState) -> AgentState:
    """After a tool is invoked, we want to update the actions history so the agent is aware of its previous steps"""
    observations = state["observations"]

    history = "Previous actions history:\n "

    if observations and len(observations) > 0:
        history += "\n".join(f"{i+1}. {obs}" for i, obs in enumerate(observations))
    else:
        history += "No actions taken yet"

    return {**state, "history": [SystemMessage(content=history)]}


#
# Define init node
#


# TODO - add end_node to properly close page, browser and playwright
async def init_node(state: AgentState) -> AgentState:
    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})

        await page.goto("https://www.google.com")

        return {
            **state,
            "playwright": playwright,
            "browser": browser,
            "page": page,
            "observations": [],
            "history": [],
            "bboxes": [],
        }

    except:
        if page:
            await page.close()
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()

        return END


#
# Define router
#


# TODO - add action type for answer to know when workflow is completed
def router(
    state: AgentState,
) -> Literal[
    "click_node",
    "type_node",
    "scroll_node",
    "wait_node",
    "go_back_node",
    "go_to_google_node",
    "history_node",
    "__end__",
]:
    action_type = state["action"]["type"]

    action_to_node_mapping = {
        Actions.RETRY: Nodes.HISTORY,
        Actions.CLICK: Nodes.CLICK,
        Actions.TYPE: Nodes.TYPE,
        Actions.SCROLL: Nodes.SCROLL,
        Actions.WAIT: Nodes.WAIT,
        Actions.GO_BACK: Nodes.GO_BACK,
        Actions.GO_TO_GOOGLE: Nodes.GO_TO_GOOGLE,
    }

    node = action_to_node_mapping.get(action_type)

    if action_type == Actions.END:
        return END
    elif node is not None:
        return node
    else:
        return Nodes.AGENT


#
# Define graph
#

graph_builder = StateGraph(AgentState)

graph_builder.add_node(Nodes.INIT, init_node)
graph_builder.add_node(Nodes.AGENT, agent_node)
graph_builder.add_node(Nodes.HISTORY, history_node)

# Define action nodes
graph_builder.add_node(Nodes.CLICK, action_nodes.get("click"))
graph_builder.add_node(Nodes.TYPE, action_nodes.get("type"))
graph_builder.add_node(Nodes.SCROLL, action_nodes.get("scroll"))
graph_builder.add_node(Nodes.WAIT, action_nodes.get("wait"))
graph_builder.add_node(Nodes.GO_BACK, action_nodes.get("go_back"))
graph_builder.add_node(Nodes.GO_TO_GOOGLE, action_nodes.get("go_to_google"))

# Define entry point
graph_builder.add_edge(START, Nodes.INIT)
graph_builder.add_edge(Nodes.INIT, Nodes.AGENT)

# Define connections between nodes
graph_builder.add_conditional_edges(
    Nodes.AGENT,
    router,
)

graph_builder.add_edge(Nodes.CLICK, Nodes.HISTORY)
graph_builder.add_edge(Nodes.TYPE, Nodes.HISTORY)
graph_builder.add_edge(Nodes.SCROLL, Nodes.HISTORY)
graph_builder.add_edge(Nodes.WAIT, Nodes.HISTORY)
graph_builder.add_edge(Nodes.GO_BACK, Nodes.HISTORY)
graph_builder.add_edge(Nodes.GO_TO_GOOGLE, Nodes.HISTORY)
graph_builder.add_edge(Nodes.HISTORY, Nodes.AGENT)

#
# Compile graph
#

graph = graph_builder.compile()
