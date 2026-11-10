<div align="center">
  <img src="https://avatars.githubusercontent.com/u/130314967?s=200&v=4" alt="xAI Logo" width="100" />
  <h1>xAI Python SDK</h1>
  <p>The official Python SDK for xAI's APIs</p>
  <a href="https://pypi.org/project/xai-sdk">
    <img src="https://img.shields.io/pypi/v/xai-sdk" alt="PyPI Version" />
  </a>
  <a href="">
    <img src="https://img.shields.io/pypi/l/xai-sdk" alt="License" />
  </a>
  <a href="">
    <img src="https://img.shields.io/pypi/pyversions/xai-sdk" alt="Python Version" />
  </a>
</div>

<br>

The xAI Python SDK is a gRPC-based Python library for interacting with xAI's APIs. Built for Python 3.10 and above, it offers both **synchronous** and **asynchronous** clients.

Whether you're generating text, images, videos, or structured outputs, the xAI SDK is designed to be intuitive, robust, and developer-friendly.

## Documentation

Comprehensive documentation is available at [docs.x.ai](https://docs.x.ai). Explore detailed guides, API references, and tutorials to get the most out of the xAI SDK.

## Installation

Install from PyPI with pip.

```bash
pip install xai-sdk
```

Alternatively you can also use [uv](https://docs.astral.sh/uv/)

```bash
uv add xai-sdk
```

### Requirements
Python 3.10 or higher is required to use the xAI SDK.

## Usage

The xAI SDK supports both synchronous (`xai_sdk.Client`) and asynchronous (`xai_sdk.AsyncClient`) clients. For a complete set of examples demonstrating the SDK's capabilities, including authentication, chat, image generation, video generation, function calling, and more, refer to the [examples folder](/examples).

### Client Instantiation

To use the xAI SDK, you need to instantiate either a synchronous or asynchronous client. By default, the SDK looks for an environment variable named `XAI_API_KEY` for authentication. If this variable is set, you can instantiate the clients without explicitly passing the API key:

```python
from xai_sdk import Client, AsyncClient

# Synchronous client
sync_client = Client()

# Asynchronous client
async_client = AsyncClient()
```

If you prefer to explicitly pass the API key, you can do so using `os.getenv` or by loading it from a `.env` file using the `python-dotenv` package:

```python
import os
from dotenv import load_dotenv
from xai_sdk import Client, AsyncClient

load_dotenv()

api_key = os.getenv("XAI_API_KEY")
sync_client = Client(api_key=api_key)
async_client = AsyncClient(api_key=api_key)
```

Make sure to set the `XAI_API_KEY` environment variable or load it from a `.env` file before using the SDK. This ensures secure handling of your API key without hardcoding it into your codebase.

### Multi-Turn Chat (Synchronous)

The xAI SDK supports multi-turn conversations with a simple `append` method to manage conversation history, making it ideal for interactive applications.

First, create a `chat` instance, start `append`ing messages to it, and finally call `sample` to yield a response from the model. While the underlying APIs are still stateless, this approach makes it easy to manage the message history.

```python
from xai_sdk import Client
from xai_sdk.chat import system, user

client = Client()
chat = client.chat.create(
    model="grok-4.6",
    messages=[system("You are a pirate assistant.")]
)

while True:
    prompt = input("You: ")
    if prompt.lower() == "exit":
        break
    chat.append(user(prompt))
    response = chat.sample()
    print(f"Grok: {response.content}")
    chat.append(response)
```

### Multi-Turn Chat (Asynchronous)

For async usage, simply import `AsyncClient` instead of `Client`.

```python
import asyncio
from xai_sdk import AsyncClient
from xai_sdk.chat import system, user

async def main():
    client = AsyncClient()
    chat = client.chat.create(
        model="grok-4.6",
        messages=[system("You are a pirate assistant.")]
    )

    while True:
        prompt = input("You: ")
        if prompt.lower() == "exit":
            break
        chat.append(user(prompt))
        response = await chat.sample()
        print(f"Grok: {response.content}")
        chat.append(response)

if __name__ == "__main__":
    asyncio.run(main())
```

### Streaming

The xAI SDK supports streaming responses, allowing you to process model outputs in real-time, which is ideal for interactive applications like chatbots. The `stream` method returns a tuple containing `response` and `chunk`. The chunks contain the text deltas from the stream, while the `response` variable automatically accumulates the response as the stream progresses.

```python
from xai_sdk import Client
from xai_sdk.chat import user

client = Client()
chat = client.chat.create(model="grok-4.6")

while True:
    prompt = input("You: ")
    if prompt.lower() == "exit":
        break
    chat.append(user(prompt))
    print("Grok: ", end="", flush=True)
    for response, chunk in chat.stream():
        print(chunk.content, end="", flush=True)
    print()
    chat.append(response)
```

### Image Understanding

You can easily interleave images and text together, making tasks like image understanding and analysis easy.

```python
from xai_sdk import Client
from xai_sdk.chat import image, user

client = Client()
chat = client.chat.create(model="grok-4.6")

chat.append(
    user(
        "Which animal looks happier in these images?",
        image("https://images.unsplash.com/photo-1561037404-61cd46aa615b"),   # Puppy
        image("https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba") # Kitten
    )
)
response = chat.sample()
print(f"Grok: {response.content}")
```

### Video Generation

Generate videos from text prompts using the `grok-imagine-video` model. The SDK handles the asynchronous polling workflow automatically — you submit a prompt and receive the completed video response.

```python
from xai_sdk import Client

client = Client()
response = client.video.generate(
    prompt="A serene lake at sunrise with mist rolling over the water",
    model="grok-imagine-video",
    duration=5,
    aspect_ratio="16:9",
    resolution="720p",
)
print(f"Video URL: {response.url}")
print(f"Duration: {response.duration}s")
```

You can also generate videos from an input image (image-to-video):

```python
response = client.video.generate(
    prompt="The camera slowly zooms in as the scene comes to life",
    model="grok-imagine-video",
    image_url="https://example.com/landscape.jpg",
    duration=5,
)
print(f"Video URL: {response.url}")
```

Or use reference images to guide the style and content of the generated video:

```python
response = client.video.generate(
    prompt="A person walking through a futuristic city",
    model="grok-imagine-video",
    reference_image_urls=[
        "https://example.com/style-ref1.jpg",
        "https://example.com/style-ref2.jpg",
    ],
    duration=10,
    aspect_ratio="16:9",
)
print(f"Video URL: {response.url}")
```

#### Video Editing

Edit an existing video based on a text prompt by passing `video_url` to `generate()`:

```python
response = client.video.generate(
    prompt="Add a rainbow in the sky",
    model="grok-imagine-video",
    video_url="https://example.com/my-video.mp4",
)
print(f"Video URL: {response.url}")
```

#### Video Extension

Extend an existing video by appending new generated content using `client.video.extend()`:

```python
response = client.video.extend(
    prompt="The camera slowly zooms out to reveal the city skyline",
    model="grok-imagine-video",
    video_url="https://example.com/my-video.mp4",
    duration=6,
)
print(f"Video URL: {response.url}")
```

Extensions can be chained — feed the returned URL back as input:

```python
response = client.video.extend(
    prompt="A bird flies across the sky",
    model="grok-imagine-video",
    video_url=response.url,
)
print(f"Extended Video URL: {response.url}")
```

## Advanced Features

The xAI SDK excels in advanced use cases, such as:

- **Function Calling**: Define tools and let the model intelligently call them (see sync [function_calling.py](/examples/sync/function_calling.py) and async [function_calling.py](/examples/aio/function_calling.py)).
- **Image Generation**: Generate images with image generation models (see sync [image_generation.py](/examples/sync/image_generation.py) and async [image_generation.py](/examples/aio/image_generation.py)).
- **Image Understanding**: Analyze images with vision models (see sync [image_understanding.py](/examples/sync/image_understanding.py) and async [image_understanding.py](/examples/aio/image_understanding.py)).
- **Video Generation**: Generate videos from text prompts, images, or reference images with the `grok-imagine-video` model (see sync [video_generation.py](/examples/sync/video_generation.py) and async [video_generation.py](/examples/aio/video_generation.py)).
- **Video Extension**: Extend existing videos with new content based on a prompt (see sync [video_extension.py](/examples/sync/video_extension.py) and async [video_extension.py](/examples/aio/video_extension.py)).
- **Structured Outputs**: Return model responses as structured objects in the form of Pydantic models (see sync [structured_outputs.py](/examples/sync/structured_outputs.py) and async [structured_outputs.py](/examples/aio/structured_outputs.py)).
- **Reasoning Models**: Leverage reasoning-focused models with configurable effort levels (see sync [reasoning.py](/examples/sync/reasoning.py) and async [reasoning.py](/examples/aio/reasoning.py)).
- **Deferred Chat**: Sample a long-running response from a model via polling (see sync [deferred_chat.py](/examples/sync/deferred_chat.py) and async [deferred_chat.py](/examples/aio/deferred_chat.py)).
- **Tokenization**: Tokenize text with the tokenizer API (see sync [tokenizer.py](/examples/sync/tokenizer.py) and async [tokenizer.py](/examples/aio/tokenizer.py)).
- **Models**: Retrieve information on different models available to you, including, name, aliases, token price, max prompt length etc (see sync [models.py](/examples/sync/models.py) and async [models.py](/examples/aio/models.py))
- **Agentic Tool Calling**: Let Grok autonomously decide when to search the web, 𝕏, or execute code to answer your questions with real-time information (e.g., "What was Arsenal's most recent game result?" triggers a web search automatically). See sync [server_side_tools.py](/examples/sync/server_side_tools.py) and async [server_side_tools.py](/examples/aio/server_side_tools.py)
- **Telemetry & Observability**: Export OpenTelemetry traces with rich metadata attributes to console or OTLP backends (see sync [telemetry.py](/examples/sync/telemetry.py) and async [telemetry.py](/examples/aio/telemetry.py))

## Telemetry & Observability

The xAI SDK includes the option to export OpenTelemetry traces to the console or an OTLP compatible backend. Exporting telemetry is not enabled by default, and you must explicitly configure this in code to start exporting traces.

When enabled, each API call automatically generates detailed traces (spans) that capture the complete execution flow of that call, as well as rich metadata including attributes such as input prompts, model responses, and token usage statistics.
When consumed by an observability platform which can visualize these traces, this makes it easy to monitor, debug, and analyze your applications' performance and behavior.

The attributes on the generated traces *largely* follow the [OpenTelemetry GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/), meaning Otel backends that support these conventions, such as Langfuse can visualize these traces in a structured way.

In some cases, where there is no corresponding standard in the OpenTelemetry GenAI semantic conventions, the xAI SDK adds some additional attributes to particular traces that users may find useful.

### Export Options

#### Console Export (Development)

Console export prints trace data in JSON format directly to your console:

```python
from xai_sdk.telemetry import 

<!-- truncated for Mythos neural library -->
