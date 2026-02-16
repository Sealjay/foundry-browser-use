"""Browser automation agent using Browser Use and Azure OpenAI.

This module demonstrates browser automation using the Browser Use library with
Azure OpenAI as the underlying LLM. The agent can perform web browsing tasks
such as searching, clicking, and extracting information from web pages.

Configuration:
    Set the following environment variables (e.g., in a .env file):
    - AZURE_OPENAI_API_KEY: Your Azure OpenAI API key
    - AZURE_OPENAI_ENDPOINT: Your Azure OpenAI endpoint URL
    - AZURE_OPENAI_DEPLOYMENT_NAME: Your model deployment name
    - AZURE_OPENAI_API_VERSION: API version (e.g., "2024-12-01-preview")

Example:
    Run directly to see a demo:
    $ uv run python agent.py
"""

import asyncio
import os

from browser_use import Agent
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI


async def main() -> None:
    """Run the browser automation agent with a demo task."""
    # Load environment variables from .env file
    load_dotenv()

    # Retrieve Azure OpenAI configuration from environment
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION")

    # Validate that all required environment variables are set
    if not all([api_key, endpoint, deployment_name, api_version]):
        raise ValueError(
            "Missing required environment variables. Please set "
            "AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, "
            "AZURE_OPENAI_DEPLOYMENT_NAME, and AZURE_OPENAI_API_VERSION"
        )

    # Initialise Azure OpenAI client
    llm = AzureChatOpenAI(
        azure_deployment=deployment_name,
        api_version=api_version,
        azure_endpoint=endpoint,
        api_key=api_key,  # type: ignore[arg-type]  # pydantic coerces str to SecretStr at runtime
        temperature=0.0,
    )

    # Create browser automation agent
    agent = Agent(
        task="Go to google.com and search for 'Browser Use python automation'",
        llm=llm,  # type: ignore[arg-type]  # AzureChatOpenAI is a BaseChatModel subclass; Pylance can't resolve langchain's type hierarchy
        use_vision=False,  # DOM-only mode for faster execution
        max_steps=25,  # Safety cap to prevent runaway execution
    )

    # Execute the agent and retrieve results
    result = await agent.run()
    print(result.final_result())


if __name__ == "__main__":
    asyncio.run(main())
