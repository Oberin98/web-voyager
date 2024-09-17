import asyncio

from graph import graph


async def run_agent(question: str, max_steps: int = 150):
    result = await graph.ainvoke(
        {
            "input": question,
        },
        {
            "recursion_limit": max_steps,
        },
    )

    action: dict = result.get("action", {})
    args: dict = action.get("args", {})
    answer: str = args.get("answer", "")

    print(f"Answer: {answer}")


# asyncio.run(run_agent("Could you please explain what SoM-GPT4V is?"))
