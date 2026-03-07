import os
import pyaudio
from google.cloud import texttospeech
from core.config import settings

# Configuration
# PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
# Gemini-TTS uses 24kHz sample rate by default for Linear16
SAMPLE_RATE = 24000
MODEL_NAME = "gemini-2.5-flash-tts"
VOICE_NAME = "Kore"
LANGUAGE_CODE = "en-US"

def play_streaming_tts(prompt, text):
    """
    Synthesizes speech using Gemini-TTS and plays it immediately via PyAudio.
    """
    client = texttospeech.TextToSpeechClient()

    # 1. Setup PyAudio stream
    # We use Int16 because the API returns LINEAR16 encoding
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=SAMPLE_RATE,
        output=True
    )

    print(f"Streaming audio from model: {MODEL_NAME}...")

    # 2. Define the Request Generator
    # The API requires a generator that yields requests.
    # The first request must contain the configuration.
    def request_generator():
        # First request: Configuration
        streaming_config = texttospeech.StreamingSynthesizeConfig(
            voice=texttospeech.VoiceSelectionParams(
                name=VOICE_NAME,
                language_code=LANGUAGE_CODE,
                model_name=MODEL_NAME
            )
        )
        yield texttospeech.StreamingSynthesizeRequest(streaming_config=streaming_config)

        # Second request: Input Text and Prompt
        # Note: The prompt field is only supported in the first input chunk.
        yield texttospeech.StreamingSynthesizeRequest(
            input=texttospeech.StreamingSynthesisInput(
                text=text,
                prompt=prompt
            )
        )

    # 3. Call the API and Stream Audio
    try:
        responses = client.streaming_synthesize(request_generator())

        for response in responses:
            if response.audio_content:
                # Write the binary audio content directly to the PyAudio stream
                stream.write(response.audio_content)

    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        # 4. Cleanup
        print("\nStream finished.")
        stream.stop_stream()
        stream.close()
        p.terminate()

if __name__ == "__main__":
    # Example prompts from the documentation
    style_prompt = "Say the following in a curious, storytelling way."

    text_input = """
    Radio Bakery is a New York City gem, celebrated for its exceptional and creative baked goods. 
    The pistachio croissant is often described as a delight with perfect sweetness. 
    The rhubarb custard croissant is a lauded masterpiece of flaky pastry and tart filling.
    """

    play_streaming_tts(style_prompt, text_input)