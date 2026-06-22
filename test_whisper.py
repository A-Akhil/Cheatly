"""Test OpenAI whisper as a fallback"""
import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import whisper
import numpy as np

print(f"OpenAI whisper loaded successfully")
print(f"Available models: {whisper.available_models()}")

print("\nLoading 'base' model...", flush=True)
model = whisper.load_model("base", device="cpu", download_root=r"C:\Users\akhil\AppData\Local\Cheatly\whisper\openai")
print("Model loaded successfully!", flush=True)

# Quick test with silence
print("\nTranscribing 1 second of silence...", flush=True)
audio = np.zeros(16000, dtype=np.float32)
result = model.transcribe(audio, language="en", fp16=False)
print(f"Result: '{result['text'].strip()}'")
print("\nOpenAI whisper is working!")
