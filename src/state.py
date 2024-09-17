from typing import List, TypedDict, Literal

from playwright.async_api import Playwright, Browser, Page

from langchain_core.messages import SystemMessage


#
# Enum of possible nodes
#


class Nodes:
    INIT = "init_node"
    AGENT = "agent_node"
    HISTORY = "history_node"
    CLICK = "click_node"
    TYPE = "type_node"
    SCROLL = "scroll_node"
    WAIT = "wait_node"
    GO_BACK = "go_back_node"
    GO_TO_GOOGLE = "go_to_google_node"


#
# Enum of possible actions
#


class Actions:
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    WAIT = "wait"
    GO_BACK = "go_back"
    GO_TO_GOOGLE = "go_to_google"
    RETRY = "retry"
    END = "end"


# Action (to be) performed by the agent
class Action(TypedDict):
    # Type of action which identifies the tool to be called
    type: Literal["click", "type", "scroll", "wait", "go_back", "go_to_google", "retry"]
    # Arguments to be passed to the tool
    args: dict


# Bounding box of an interactive element on the page
class BBox(TypedDict):
    x: float
    y: float
    text: str
    type: str
    ariaLabel: str


# This represents the state of the agent as it proceeds through execution
class AgentState(TypedDict):
    # User request
    input: str
    # The Agent's output
    action: Action
    # The most recent response from a tool
    observations: List[str]
    # Agent's actions history (variable in the agent't prompt)
    history: List[SystemMessage]
    # The bounding boxes of the interactive elements on the page
    bboxes: List[BBox]
    # b64 encoded screenshot
    b64_image: str
    # The Playwright instance (required in the state only to be properly closed in the end of the workflow)
    playwright: Playwright
    # The Playwright browser (required in the state only to be properly closed in the end of the workflow)
    browser: Browser
    # The Playwright web page lets us interact with the web environment
    page: Page
