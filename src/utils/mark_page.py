import os
import base64
import asyncio

from playwright.async_api import Page

from langchain_core.runnables import chain

#
#   Page annotation
#


with open(os.path.join(os.getcwd(), "src", "utils", "mark_page.js")) as f:
    mark_page_script = f.read()


SCREENSHOT_ORDER = 0


@chain
async def mark_page(page: Page):
    await page.wait_for_load_state()

    await page.evaluate(mark_page_script)

    for _ in range(10):
        try:
            bboxes = await page.evaluate("markPage()")
            break
        except Exception:
            # May be loading...
            asyncio.sleep(5)

    global SCREENSHOT_ORDER
    SCREENSHOT_ORDER += 1

    screenshot = await page.screenshot(
        path=f"""./screenshot-{SCREENSHOT_ORDER}.png""",
    )

    # Clean up bboxes
    await page.evaluate("removeStyleMarks()")

    return {
        "b64_image": base64.b64encode(screenshot).decode(),
        "bboxes": bboxes,
    }
