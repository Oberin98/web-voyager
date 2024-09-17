import asyncio
import platform

from typing import Literal

from pydantic import BaseModel, Field

from langchain_core.tools import tool

from state import AgentState


# ========================================================
# Click action
# ========================================================


class ClickInputSchema(BaseModel):
    reason: str = Field(
        ..., description="Brief explanation of the reason why this action is selected"
    )
    bbox_label: str = Field(
        ..., description="Numerical label of the element's bounding box to be clicked"
    )


#
# Define click_tool as an abstract function to enable structured LLM output for the click_node
#


@tool(args_schema=ClickInputSchema)
def click_tool(input: ClickInputSchema):
    """Click on the interactive element with a bounding box labeled with the selected bbox_label."""
    pass


#
# Define click node
#


async def click_node(state: AgentState) -> AgentState:
    page = state["page"]
    args = state["action"]["args"]

    observation: str = ""

    if args is None:
        observation = f"Failed to click element due to missing arguments"
    elif args["bbox_label"] is None:
        observation = f'Failed to click element due to missing "bbox_label" argument'
    elif args["reason"] is None or args["reason"].strip() == "":
        observation = f'Failed to click element due to missing "reason" argument'
    else:
        reason = args["reason"]
        bbox_label = args["bbox_label"]

        await page.click(f"[data-interactive-index='{bbox_label}']")

        observation = f'Сlicked on item {bbox_label} for the reason "{reason}"'

    return {
        **state,
        "observations": state["observations"] + [observation],
    }


# ========================================================
# Type action
# ========================================================


class TypeInputSchema(BaseModel):
    reason: str = Field(
        ..., description="Brief explanation of the reason why this action is selected"
    )
    bbox_label: str = Field(
        ..., description="Numerical label of the element to type into"
    )
    text: str = Field(..., description="Text to be typed")


#
# Define type_tool as an abstract function to enable structured LLM output for the type_node
#


@tool(args_schema=TypeInputSchema)
def type_tool(input: TypeInputSchema):
    """Type text into the element with the bounding box labeled with the selected bbox_label."""
    pass


#
# Define type node
#


async def type_node(state: AgentState):
    page = state["page"]
    args = state["action"]["args"]

    observation: str = ""

    if args is None:
        observation = f"Failed to type in element due to missing arguments"
    elif args["bbox_label"] is None:
        observation = f'Failed to type in element due to missing "bbox_label" argument'
    elif args["text"] is None or args["text"].strip() == "":
        observation = f'Failed to type in element due to missing "text" argument'
    elif args["reason"] is None or args["reason"].strip() == "":
        observation = f'Failed to type in element due to missing "reason" argument'
    else:
        reason = args["reason"]
        text = args["text"]
        bbox_label = args["bbox_label"]

        await page.click(f"[data-interactive-index='{bbox_label}']")

        # Check if MacOS
        select_all = "Meta+A" if platform.system() == "Darwin" else "Control+A"

        await page.keyboard.press(select_all)
        await page.keyboard.press("Backspace")
        await page.keyboard.type(text)
        await page.keyboard.press("Enter")

        observation = (
            f'Typed "{text}" in the element {bbox_label} for the reason "{reason}"'
        )

    return {
        **state,
        "observations": state["observations"] + [observation],
    }


# ========================================================
# Scroll action
# ========================================================


class ScrollInputSchema(BaseModel):
    reason: str = Field(
        ..., description="Brief explanation of the reason why this action is selected"
    )
    target: str = Field(
        ...,
        description=(
            "Ether numerical label of the element to be scrolled "
            "or 'WINDOW' to scroll the whole page"
        ),
    )
    direction: Literal["up", "down"] = Field(..., description="Direction of the scroll")


#
# Define scroll_tool as an abstract function to enable structured LLM output for the scroll_node
#


@tool(args_schema=ScrollInputSchema)
def scroll_tool(input: ScrollInputSchema):
    """Scroll either the whole page if target is 'WINDOW',
    or scroll the element with the bounding box labeled with the selected target."""
    pass


#
# Define scroll node
#


async def scroll_node(state: AgentState):
    page = state["page"]
    args = state["action"]["args"]

    observation: str = ""

    if args is None:
        observation = "Failed to scroll due to missing arguments."
    elif args["target"] is None:
        observation = "Failed to scroll due to missing 'target' argument."
    elif args["direction"] is None:
        observation = "Failed to scroll due to missing 'direction' argument."
    elif args["reason"] is None:
        observation = "Failed to scroll due to missing 'reason' argument."
    else:
        reason = args["reason"]
        target = args["target"]
        direction = args["direction"]

        if target.upper() == "WINDOW":
            # Scroll the whole page
            # TODO - make scroll amount dynamic
            scroll_amount = 500
            scroll_direction = (
                -scroll_amount if direction.lower() == "up" else scroll_amount
            )
            await page.evaluate(f"window.scrollBy(0, {scroll_direction})")
        else:
            # Scrolling specific element
            # TODO - make scroll amount dynamic
            scroll_amount = 200
            target_id = int(target)
            bbox = state["bboxes"][target_id]
            x, y = bbox["x"], bbox["y"]
            scroll_direction = (
                -scroll_amount if direction.lower() == "up" else scroll_amount
            )
            await page.mouse.move(x, y)
            await page.mouse.wheel(0, scroll_direction)

        observation = f"Scrolled {direction} in {'window' if target.upper() == 'WINDOW' else 'element'} for the reason '{reason}'"

    return {
        **state,
        "observations": state["observations"] + [observation],
    }


# ========================================================
# Wait action
# ========================================================


class WaitInputSchema(BaseModel):
    reason: str = Field(
        ..., description="Brief explanation of the reason why this action is selected"
    )


#
# Define wait_tool as an abstract function to enable structured LLM output for the wait_node
# TODO - make wait time dynamic


@tool(args_schema=WaitInputSchema)
def wait_tool(input: WaitInputSchema):
    """Wait for a 5 seconds."""
    pass


#
# Define wait node
#


async def wait_node(state: AgentState):
    args = state["action"]["args"]

    observation: str = ""

    if args is None:
        observation = "Failed to wait due to missing arguments."
    elif args["reason"] is None:
        observation = 'Failed to wait due to missing "reason" argument.'
    else:
        await asyncio.sleep(5)

        reason = args["reason"]
        observation = f'Waited for 5 seconds for the reason "{reason}"'

    return {
        **state,
        "observations": state["observations"] + [observation],
    }


# ========================================================
# Go back action
# ========================================================


class GoBackInputSchema(BaseModel):
    reason: str = Field(
        ..., description="Brief explanation of the reason why this action is selected"
    )


#
# Define go_back_tool as an abstract function to enable structured LLM output for the go_back_node
#


@tool(args_schema=GoBackInputSchema)
def go_back_tool(input: GoBackInputSchema):
    """Go to the previous page."""
    pass


#
# Define go back node
#


async def go_back_node(state: AgentState):
    page = state["page"]
    args = state["action"]["args"]

    observation: str = ""

    if args is None:
        observation = "Failed to wait due to missing arguments."
    elif args["reason"] is None:
        observation = 'Failed to wait due to missing "reason" argument.'
    else:
        await page.go_back()

        reason = args["reason"]
        observation = f'Navigated back a page to {page.url} for the reason "{reason}"'

    return {
        **state,
        "observations": state["observations"] + [observation],
    }


# ========================================================
# Go to google page action
# ========================================================


class GoToGoogleInputSchema(BaseModel):
    reason: str = Field(
        ..., description="Brief explanation of the reason why this action is selected"
    )


#
# Define go_to_google_tool as an abstract function to enable structured LLM output for the go_to_google_node
#


@tool(args_schema=GoToGoogleInputSchema)
def go_to_google_tool(input: GoToGoogleInputSchema):
    """Go to the google page."""
    pass


async def go_to_google_node(state: AgentState):
    page = state["page"]
    args = state["action"]["args"]

    observation: str = ""

    if args is None:
        observation = "Failed to go to google due to missing arguments."
    elif args["reason"] is None:
        observation = 'Failed to go to google due to missing "reason" argument.'
    else:
        await page.goto("https://www.google.com/")

        reason = args["reason"]
        observation = f'Navigated to google.com for the reason "{reason}"'

    return {
        **state,
        "observations": state["observations"] + [observation],
    }


action_tools = {
    "click": click_tool,
    "type": type_tool,
    "scroll": scroll_tool,
    "wait": wait_tool,
    "go_back": go_back_tool,
    "go_to_google": go_to_google_tool,
}

action_nodes = {
    "click": click_node,
    "type": type_node,
    "scroll": scroll_node,
    "wait": wait_node,
    "go_back": go_back_node,
    "go_to_google": go_to_google_node,
}
