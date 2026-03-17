import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.backend.database import get_db
from app.backend.models.events import (
    CompleteEvent,
    ErrorEvent,
    ProgressUpdateEvent,
    StartEvent,
)
from app.backend.models.schemas import ErrorResponse, ResearchPipelineRequest
from app.backend.services.api_key_service import ApiKeyService
from src.utils.progress import progress

router = APIRouter(prefix="/research-pipeline")


@router.post(
    path="/run",
    responses={
        200: {"description": "Successful response with streaming updates"},
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def run(request_data: ResearchPipelineRequest, request: Request, db: Session = Depends(get_db)):
    try:
        # Hydrate API keys from database if not provided
        if not request_data.api_keys:
            api_key_service = ApiKeyService(db)
            request_data.api_keys = api_key_service.get_api_keys_dict()

        # Convert model_provider to string if it's an enum
        model_provider = request_data.model_provider
        if hasattr(model_provider, "value"):
            model_provider = model_provider.value

        # Function to detect client disconnection
        async def wait_for_disconnect():
            """Wait for client disconnect and return True when it happens"""
            try:
                while True:
                    message = await request.receive()
                    if message["type"] == "http.disconnect":
                        return True
            except Exception:
                return True

        # Set up streaming response
        async def event_generator():
            # Queue for progress updates
            progress_queue = asyncio.Queue()
            run_task = None
            disconnect_task = None

            # Simple handler to add updates to the queue
            def progress_handler(agent_name, ticker, status, analysis, timestamp):
                event = ProgressUpdateEvent(agent=agent_name, ticker=ticker, status=status, timestamp=timestamp, analysis=analysis)
                progress_queue.put_nowait(event)

            # Register our handler with the progress tracker
            progress.register_handler(progress_handler)

            try:
                # Send initial message
                yield StartEvent().to_sse()

                # Ingest content in a background thread
                progress.update_status("ingestion", None, "Ingesting content from source")
                ingestion_event = ProgressUpdateEvent(
                    agent="ingestion",
                    ticker=None,
                    status="Ingesting content from source",
                    timestamp=None,
                    analysis=None,
                )
                yield ingestion_event.to_sse()

                try:
                    from src.inputs import ingest

                    transcript, input_type = await asyncio.to_thread(ingest, request_data.source, skip_video=request_data.skip_video)
                except Exception as e:
                    yield ErrorEvent(message=f"Failed to ingest content: {str(e)}").to_sse()
                    return

                ingestion_done_event = ProgressUpdateEvent(
                    agent="ingestion",
                    ticker=None,
                    status=f"Content ingested successfully ({len(transcript)} chars)",
                    timestamp=None,
                    analysis=None,
                )
                yield ingestion_done_event.to_sse()

                # Run the research pipeline in a background thread
                def run_pipeline():
                    from langchain_core.messages import HumanMessage

                    from src.research_pipeline import create_research_workflow

                    workflow = create_research_workflow()
                    agent = workflow.compile()

                    final_state = agent.invoke(
                        {
                            "messages": [HumanMessage(content="Analyze this transcript and generate equity ideas.")],
                            "data": {"transcript": transcript},
                            "metadata": {
                                "show_reasoning": False,
                                "model_name": request_data.model_name,
                                "model_provider": model_provider,
                            },
                        }
                    )
                    return final_state

                # Start the pipeline execution in a background task
                run_task = asyncio.create_task(asyncio.to_thread(run_pipeline))

                # Start the disconnect detection task
                disconnect_task = asyncio.create_task(wait_for_disconnect())

                # Stream progress updates until run_task completes or client disconnects
                while not run_task.done():
                    # Check if client disconnected
                    if disconnect_task.done():
                        print("Client disconnected, cancelling research pipeline execution")
                        run_task.cancel()
                        try:
                            await run_task
                        except asyncio.CancelledError:
                            pass
                        return

                    # Either get a progress update or wait a bit
                    try:
                        event = await asyncio.wait_for(progress_queue.get(), timeout=1.0)
                        yield event.to_sse()
                    except asyncio.TimeoutError:
                        # Just continue the loop
                        pass

                # Get the final result
                try:
                    result = await run_task
                except asyncio.CancelledError:
                    print("Research pipeline task was cancelled")
                    return

                if not result:
                    yield ErrorEvent(message="Failed to generate research pipeline results").to_sse()
                    return

                # Send the final result
                final_data = CompleteEvent(data=result.get("data", {}))
                yield final_data.to_sse()

            except asyncio.CancelledError:
                print("Research pipeline event generator cancelled")
                return
            finally:
                # Clean up
                progress.unregister_handler(progress_handler)
                if run_task and not run_task.done():
                    run_task.cancel()
                    try:
                        await run_task
                    except asyncio.CancelledError:
                        pass
                if disconnect_task and not disconnect_task.done():
                    disconnect_task.cancel()

        # Return a streaming response
        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while processing the research pipeline request: {str(e)}")
