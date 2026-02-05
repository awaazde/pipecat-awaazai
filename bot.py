#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import json
import os

from dotenv import load_dotenv
from loguru import logger
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import parse_telephony_websocket
from pipecat_awaazai.serializer import AwaazAIFrameSerializer
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.transcriptions.language import Language
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.base_transport import BaseTransport
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from pipecat.turns.user_stop import TurnAnalyzerUserTurnStopStrategy
from pipecat.turns.user_turn_strategies import UserTurnStrategies

load_dotenv(override=True)


async def run_bot(transport: BaseTransport, handle_sigint: bool):
    llm = OpenAILLMService(api_key=os.getenv("OPENAI_API_KEY"))

    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))

    tts = ElevenLabsTTSService(
        api_key=os.getenv("ELEVENLABS_API_KEY"),
        voice_id="Xb7hH8MSUJpSbSDYk0k2",  # British Reading Lady
        model="eleven_turbo_v2_5",
        params=ElevenLabsTTSService.InputParams(language=Language.EN),
    )

    messages = [
        {
            "role": "system",
            "content": "You are a helpful LLM in an audio call. Your goal is to demonstrate your capabilities in a succinct way. Your output will be converted to audio so don't include special characters in your answers. Respond to what the user said in a creative and helpful way.",
        },
    ]

    context = LLMContext(messages)
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            user_turn_strategies=UserTurnStrategies(
                stop=[TurnAnalyzerUserTurnStopStrategy(turn_analyzer=LocalSmartTurnAnalyzerV3())]
            ),
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
        ),
    )

    pipeline = Pipeline(
        [
            transport.input(),  # Websocket input from client
            stt,  # Speech-To-Text
            user_aggregator,
            llm,  # LLM
            tts,  # Text-To-Speech
            transport.output(),  # Websocket output to client
            assistant_aggregator,
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=8000,
            audio_out_sample_rate=8000,
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        # Kick off the conversation.
        messages.append({"role": "system", "content": "Please introduce yourself to the user."})
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        await task.cancel()

    runner = PipelineRunner(handle_sigint=handle_sigint)

    await runner.run(task)

async def _parse_stream_sid(websocket) -> str:
    '''
    # adapted from parse_telephony_websocket in pipecat/runner/utils.py
    # once we are fully natively supported by Pipecat, we can remove this code
    '''
    start_data = websocket.iter_text()

    # First message
    first_message_raw = await start_data.__anext__()
    logger.trace(f"First message: {first_message_raw}")
    try:
        first_message = json.loads(first_message_raw)
    except json.JSONDecodeError:
        first_message = {}

    # Second message
    second_message_raw = await start_data.__anext__()
    logger.trace(f"Second message: {second_message_raw}")
    try:
        second_message = json.loads(second_message_raw)
    except json.JSONDecodeError:
        second_message = {}

    for call_data_raw in [first_message, second_message]:
        if "start" in call_data_raw:
            start_data = call_data_raw.get("start", {})
            stream_sid = start_data.get("stream_sid")
            if stream_sid:
                return stream_sid
            
    raise ValueError(f"Could not find stream_sid in initial websocket messages: {first_message}, {second_message}")

async def bot(runner_args: RunnerArguments):
    """Main bot entry point compatible with Pipecat Cloud."""

    stream_id:str = await _parse_stream_sid(runner_args.websocket)

    serializer = AwaazAIFrameSerializer(
        stream_sid=stream_id
    )

    transport = FastAPIWebsocketTransport(
        websocket=runner_args.websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            serializer=serializer,
        ),
    )

    handle_sigint = runner_args.handle_sigint

    await run_bot(transport, handle_sigint)


if __name__ == "__main__":
    from pipecat.runner.run import main, TELEPHONY_TRANSPORTS
    TELEPHONY_TRANSPORTS.append("awaazai")

    main()
