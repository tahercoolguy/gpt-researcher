# libraries
from __future__ import annotations
import json
from fastapi import WebSocket
from langchain.adapters import openai as lc_openai
from colorama import Fore, Style
from typing import Optional

from gpt_researcher_gemini.master.prompts import auto_agent_instructions
import os
import google.generativeai as genai

async def create_chat_completion(
        messages: list,  # type: ignore
        model: Optional[str] = None,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        llm_provider: Optional[str] = None,
        stream: Optional[bool] = False,
        websocket: WebSocket | None = None,
) -> str:
    """Create a chat completion using the OpenAI API
    Args:
        messages (list[dict[str, str]]): The messages to send to the chat completion
        model (str, optional): The model to use. Defaults to None.
        temperature (float, optional): The temperature to use. Defaults to 0.9.
        max_tokens (int, optional): The max tokens to use. Defaults to None.
        stream (bool, optional): Whether to stream the response. Defaults to False.
        llm_provider (str, optional): The LLM Provider to use.
        webocket (WebSocket): The websocket used in the currect request
    Returns:
        str: The response from the chat completion
    """

    # validate input
    if model is None:
        raise ValueError("Model cannot be None")
    if max_tokens is not None and max_tokens > 30000:
        raise ValueError(f"Max tokens cannot be more than 8001, but got {max_tokens}")

    # create response
    for attempt in range(10):  # maximum of 10 attempts
        response = await send_chat_completion_request(
            messages, model, temperature, max_tokens, stream, llm_provider, websocket
        )
        return response

    logging.error("Failed to get response from OpenAI API")
    raise RuntimeError("Failed to get response from OpenAI API")


import logging


async def send_chat_completion_request(
        messages, model, temperature, max_tokens, stream, llm_provider, websocket
):
    new_messages = [{"role": "user", "parts":[]}]
    for message in messages:
        if message['role'] == "system" or message['role'] == "user":
            new_messages[0]['parts'].append(message['content'])
        else:
            new_dict = {"role": "model", "parts":[message['content']]}
            new_messages.append(new_dict)

    messages = new_messages
    # print(messages)
    if not stream:
        os.environ['GOOGLE_API_KEY'] = "AIzaSyBBKHWk5C8Ar7A1EEWuhfX2jYqQAYZbPj0"
        genai.configure(api_key=os.environ['GOOGLE_API_KEY'])
        chat_model = genai.GenerativeModel('gemini-pro')
        result = chat_model.generate_content(messages,safety_settings = [{"category": "HARM_CATEGORY_HARASSMENT","threshold": "BLOCK_NONE"},{"category": "HARM_CATEGORY_HATE_SPEECH","threshold": "BLOCK_NONE"},{"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT","threshold": "BLOCK_NONE"},{"category": "HARM_CATEGORY_DANGEROUS_CONTENT","threshold": "BLOCK_NONE"}])
        if 'block_reason' in str(result.prompt_feedback):
            result = lc_openai.ChatCompletion.create(
                    model=model,  # Change model here to use different models
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    provider=llm_provider,  # Change provider here to use a different API
            )
            final_result = result["choices"][0]["message"]["content"]
        else:
            final_result = result.text
        return final_result
    else:
        return await stream_response(model, messages, temperature, max_tokens, llm_provider, websocket)


async def stream_response(model, messages, temperature, max_tokens, llm_provider, websocket=None):
    paragraph = ""
    response = ""
    os.environ['GOOGLE_API_KEY'] = "AIzaSyBBKHWk5C8Ar7A1EEWuhfX2jYqQAYZbPj0"
    genai.configure(api_key=os.environ['GOOGLE_API_KEY'])
    chat_model = genai.GenerativeModel('gemini-pro')
    result = chat_model.generate_content(messages, stream=True,safety_settings = [{"category": "HARM_CATEGORY_HARASSMENT","threshold": "BLOCK_NONE"},{"category": "HARM_CATEGORY_HATE_SPEECH","threshold": "BLOCK_NONE"},{"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT","threshold": "BLOCK_NONE"},{"category": "HARM_CATEGORY_DANGEROUS_CONTENT","threshold": "BLOCK_NONE"}])
    if 'block_reason' in str(result.prompt_feedback):

        for chunk in lc_openai.ChatCompletion.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                provider=llm_provider,
                stream=True,
        ):
            content = chunk["choices"][0].get("delta", {}).get("content")
            if content is not None:
                response += content
                paragraph += content
                if "\n" in paragraph:
                    if websocket is not None:
                        websocket.send_json({"type": "report", "output": f"{Fore.GREEN}{paragraph}{Style.RESET_ALL}"}) #await
                        print(f"{Fore.GREEN}{paragraph}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.GREEN}{paragraph}{Style.RESET_ALL}")
                    paragraph = ""

    else:
        for chunk in result:
            content = chunk.text
            if content is not None:
                response += content
                paragraph += content
                if "\n" in paragraph:
                    if websocket is not None:
                         websocket.send_json({"type": "report", "output": paragraph})
                    else:
                        print(f"{Fore.GREEN}{paragraph}{Style.RESET_ALL}")
                    paragraph = ""
    return response


def choose_agent(smart_llm_model: str, llm_provider: str, task: str) -> dict:
    """Determines what server should be used
    Args:
        task (str): The research question the user asked
        smart_llm_model (str): the llm model to be used
        llm_provider (str): the llm provider used
    Returns:
        server - The server that will be used
        agent_role_prompt (str): The prompt for the server
    """
    try:
        response = create_chat_completion(
            model=smart_llm_model,
            messages=[
                {"role": "system", "content": f"{auto_agent_instructions()}"},
                {"role": "user", "content": f"task: {task}"}],
            temperature=0,
            llm_provider=llm_provider
        )
        agent_dict = json.loads(response)
        print(f"Agent: {agent_dict.get('server')}")
        return agent_dict
    except Exception as e:
        print(f"{Fore.RED}Error in choose_agent: {e}{Style.RESET_ALL}")
        return {"server": "Default Agent",
                "agent_role_prompt": "You are an AI critical thinker research assistant. Your sole purpose is to write well written, critically acclaimed, objective and structured reports on given text."}