from typing import List, Optional, TypedDict
from playwright.async_api import Page

from langchain_core.messages import BaseMessage


class BBox(TypedDict):
    x: float
    y: float
    text: str
    type: str
    ariaLabel: str


class Prediction(TypedDict):
    action: str
    args: Optional[List[str]]


# This represents the state of the agent
# as it proceeds through execution
class AgentState(TypedDict):
    # The Playwright web page lets us interact with the web environment
    page: Page
    # User request
    input: str
    # b64 encoded screenshot
    img: str
    # The bounding boxes from the browser annotation function
    bboxes: List[BBox]
    # The Agent's output
    prediction: Prediction
    # A system message (or messages) containing the intermediate steps
    scratchpad: List[BaseMessage]
    # The most recent response from a tool
    observation: str
