import asyncio
import base64
import re
import os

from agent_state import AgentState
from tools import tools
from utils.patch_asyncio import patch_asyncio

from langchain import hub
from langgraph.graph import END, START, StateGraph
from langchain_core.runnables import chain
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_openai import ChatOpenAI

from playwright.async_api import async_playwright, Page
from dotenv import load_dotenv

load_dotenv()
patch_asyncio()

#
#   Page annotation
#


with open(os.path.join(os.getcwd(), "src", "mark_page.js")) as f:
    mark_page_script = f.read()


screenshot_order = 0


@chain
async def mark_page(page: Page):
    await page.evaluate(mark_page_script)

    for _ in range(10):
        try:
            bboxes = await page.evaluate("markPage()")
            break
        except Exception:
            # May be loading...
            asyncio.sleep(5)

    global screenshot_order
    screenshot_order += 1

    screenshot = await page.screenshot(
        path=f"""./screenshot-{screenshot_order}.png""",
    )

    # Clean up bboxes
    await page.evaluate("unmarkPage()")

    return {
        "img": base64.b64encode(screenshot).decode(),
        "bboxes": bboxes,
    }


#
#   Agent definition
#


async def annotate(state: AgentState):
    marked_page = await mark_page.with_retry().ainvoke(state["page"])
    return {**state, **marked_page}


def format_descriptions(state: AgentState):
    labels = []

    for i, bbox in enumerate(state["bboxes"]):
        text = bbox.get("ariaLabel") or ""

        if not text.strip():
            text = bbox["text"]

        el_type = bbox.get("type")
        labels.append(f'{i} (<{el_type}/>): "{text}"')

    bbox_descriptions = "\nValid Bounding Boxes:\n" + "\n".join(labels)

    return {**state, "bbox_descriptions": bbox_descriptions}


def parse(text: str) -> dict:
    action_prefix = "Action: "
    action_block = text.strip().split("\n")[-1]

    print("PARSE_TEXT", text)

    if not action_block.startswith(action_prefix):
        return {"action": "retry", "args": f"Could not parse LLM Output: {text}"}

    action_str = action_block[len(action_prefix) :]
    split_output = action_str.split(" ", 1)

    if len(split_output) == 1:
        action, action_input = split_output[0], None
    else:
        action, action_input = split_output

    action = action.strip()

    if action_input is not None:
        action_input = [
            inp.strip().strip("[]") for inp in action_input.strip().split(";")
        ]

    return {"action": action, "args": action_input}


prompt = hub.pull("wfh/web-voyager")

llm = ChatOpenAI(model="gpt-4o", max_tokens=4096)

agent = annotate | RunnablePassthrough.assign(
    prediction=format_descriptions | prompt | llm | StrOutputParser() | parse
)


#
#   Graph definition
#


def update_scratchpad(state: AgentState):
    """After a tool is invoked, we want to update
    the scratchpad so the agent is aware of its previous steps"""
    old = state.get("scratchpad")

    if old:
        txt = old[0].content
        last_line = txt.rsplit("\n", 1)[-1]
        step = int(re.match(r"\d+", last_line).group()) + 1
    else:
        txt = "Previous action observations:\n"
        step = 1

    txt += f"\n{step}. {state['observation']}"

    return {**state, "scratchpad": [SystemMessage(content=txt)]}


graph_builder = StateGraph(AgentState)

graph_builder.add_node("agent", agent)
graph_builder.add_edge(START, "agent")

graph_builder.add_node("update_scratchpad", update_scratchpad)
graph_builder.add_edge("update_scratchpad", "agent")

for node_name, tool in tools.items():
    graph_builder.add_node(
        node_name,
        # The lambda ensures the function's string output is mapped to the "observation"
        # key in the AgentState
        RunnableLambda(tool) | (lambda observation: {"observation": observation}),
    )
    # Always return to the agent (by means of the update-scratchpad node)
    graph_builder.add_edge(node_name, "update_scratchpad")


def select_tool(state: AgentState):
    # Any time the agent completes, this function
    # is called to route the output to a tool or
    # to the end user.
    action = state["prediction"]["action"]

    if action == "ANSWER":
        return END
    if action == "retry":
        return "agent"

    return action


graph_builder.add_conditional_edges("agent", select_tool)

graph = graph_builder.compile()

#
# Running agent
#


async def run_agent(question: str, max_steps: int = 150):
    playwrite = await async_playwright().start()
    browser = await playwrite.chromium.launch(headless=False, args=None)
    page = await browser.new_page()

    try:
        await page.goto("https://www.google.com")

        event_stream = graph.astream(
            {
                "page": page,
                "input": question,
                "scratchpad": [],
            },
            {
                "recursion_limit": max_steps,
            },
        )

        final_answer = None
        steps = []

        async for event in event_stream:
            # We'll display an event stream here
            if "agent" not in event:
                continue

            pred = event["agent"].get("prediction") or {}
            action = pred.get("action")
            action_input = pred.get("args")
            steps.append(f"{len(steps) + 1}. {action}: {action_input}")

            print("\n".join(steps))

            if "ANSWER" in action:
                final_answer = action_input[0]
                break

        print(final_answer)
    finally:
        await page.close()
        await browser.close()
        await playwrite.stop()


asyncio.run(run_agent("Could you please explain what SoM-GPT4V is?"))
