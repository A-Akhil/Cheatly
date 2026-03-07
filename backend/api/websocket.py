# WebSocket handler for real-time streaming communication with the frontend.
#
# Responsibilities:
# - Accept and maintain WebSocket connections from the React frontend
# - Stream live transcript updates to the frontend as they are produced
# - Stream AI suggestion chunks to the frontend as tokens are generated
# - Handle client disconnections and reconnection events gracefully
# - Broadcast pipeline state changes (listening, processing, idle)
# - Use asyncio to manage concurrent WebSocket connections
# - Integrate with suggestion_engine.py to push suggestions on generation
