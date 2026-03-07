# Parses raw LLM output into structured suggestion objects.
#
# Responsibilities:
# - Accept raw text or token stream from the model provider
# - Extract bullet-point suggestions from the model output
# - Normalize formatting (strip markdown, clean whitespace)
# - Return a list of suggestion strings ready for the frontend
# - Handle incomplete or malformed model responses gracefully
# - Support streaming parse mode where suggestions are extracted incrementally
