# Pipecat Awaaz AI Telephony Serializer Integration

Host your Pipecat agents with [Awaaz AI](https://www.awaaz.ai/) telephony stack.

**Maintainer:** Awaaz AI

## Installation

```bash
pip install pipecat-awaazai
```

Or via `uv`, update your `pyproject.toml`:
```toml
[project]
name = "your-project"
version = "0.1.0"
dependencies = [
    "pipecat-awaazai",
    "another-package"
]
```

```bash
uv sync
```

## Prerequisites

- Purchase a Phone number from Awaaz AI  

## Usage with Pipecat Pipeline

`AwaazAIFrameSerializer` convert between frames and media streams, enabling real-time communication over a websocket to host agent over Awaaz AI's telephony stack over an indian phone number

```python
from pipecat_awaazai import AwaazAIFrameSerializer

    transport = FastAPIWebsocketTransport(
        websocket=websocket_client,
        params=FastAPIWebsocketParams(
            audio_out_enabled=True,
            add_wav_header=True,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(sample_rate=8000),
            vad_audio_passthrough=True,
            serializer=AwaazAIFrameSerializer(stream_id),
            audio_out_sample_rate=8000
        ),
    )
```

See [`example.py`](example.py) for a complete working example including event handlers and transport setup.

## Running the Example

1. Install dependencies:
    ```bash
    uv sync
    ```

2. Set up your environment

   ```bash
   cp env.example .env
   ```

3. Run:
    ```bash
    uv run python example.py
    ```

The bot will create a websocket that will accept connections from Awaaz AI assigned phone number. Once websocket is running, call Awaaz AI assigned phone number and it will provide agent over call

## Compatibility

**Tested with Pipecat v0.0.98**

- Python 3.9+

## License

BSD-2-Clause - see [LICENSE](LICENSE)

## Support

- Docs: https://docs.awaaz.de/voice-hosting/custom (refer to API docs for message formats)
- Pipecat Discord: https://discord.gg/pipecat (`#community-integrations`)
