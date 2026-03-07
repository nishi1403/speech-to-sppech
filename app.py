import streamlit as st
import google.generativeai as genai
import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure API Keys
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# ElevenLabs Settings
ELEVENLABS_VOICE_ID = "21m00Tcm4TlvDq8ikWAM" # Rachel

st.set_page_config(page_title="Speech-to-Speech Chatbot", page_icon="🗣️", layout="centered")

st.title("🗣️ Multilingual Speech-to-Speech Chatbot")
st.markdown("Record your voice! The bot will identify your language and translate it into your target language.")

target_language = st.selectbox("Select Target Language", ["English", "Spanish", "French", "German", "Hindi", "Japanese", "Chinese", "Korean", "Italian", "Portuguese"])

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("text"):
            st.markdown(msg["text"])
        if msg.get("audio") and isinstance(msg["audio"], bytes):
            # Try to infer format based on role
            fmt = "audio/wav" if msg["role"] == "user" else "audio/mpeg"
            st.audio(msg["audio"], format=fmt)

audio_value = st.audio_input("Record a voice message")

def process_audio(audio_bytes, target_lang):
    prompt = f"Listen to this audio. Identify its spoken language. Translate the speech into {target_lang}. Return ONLY a JSON object with two keys: 'detected_language' and 'translated_text'. Do not include markdown formatting or any other text."
    
    try:
        response = model.generate_content([
            prompt,
            {
                "mime_type": "audio/wav",
                "data": audio_bytes
            }
        ])
        
        # Clean up the response if it has markdown code blocks
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean_text)
        return result
    except Exception as e:
        st.error(f"Error processing audio with Gemini: {e}")
        return None

def generate_speech(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            return response.content
        else:
            st.error(f"ElevenLabs API Error: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error generating speech: {e}")
        return None

if audio_value is not None:
    # Check if we already processed this exact audio to prevent rerun loops
    if "last_processed" not in st.session_state or st.session_state.last_processed != audio_value:
        st.session_state.last_processed = audio_value
        audio_bytes = audio_value.getvalue()
        
        with st.chat_message("user"):
            st.audio(audio_bytes, format="audio/wav")
            st.session_state.messages.append({"role": "user", "audio": audio_bytes})
            
        with st.spinner("Analyzing and Translating..."):
            translation_result = process_audio(audio_bytes, target_language)
            
        if translation_result:
            detected_lang = translation_result.get("detected_language", "Unknown")
            translated_text = translation_result.get("translated_text", "")
            
            response_text = f"**Detected Language:** {detected_lang}\n\n**Translation:** {translated_text}"
            
            with st.spinner("Generating Speech..."):
                output_audio = generate_speech(translated_text)
                
            with st.chat_message("assistant"):
                st.markdown(response_text)
                if output_audio:
                    st.audio(output_audio, format="audio/mpeg")
                
                st.session_state.messages.append({"role": "assistant", "text": response_text, "audio": output_audio})
