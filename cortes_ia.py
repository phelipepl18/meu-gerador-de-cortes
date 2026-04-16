import streamlit as st
from moviepy.editor import VideoFileClip
from openai import OpenAI
import os

# Pega a chave que você salvou nos Secrets
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.title("✂️ Gerador Viral com IA")

uploaded_file = st.file_uploader("Suba seu vídeo aqui", type=["mp4"])

if uploaded_file:
    with open("temp.mp4", "wb") as f:
        f.write(uploaded_file.read())
    
    if st.button("Analisar Falas com IA"):
        with st.spinner("A IA está ouvindo o vídeo..."):
            # Extrai o áudio para a IA ouvir
            video = VideoFileClip("temp.mp4")
            video.audio.write_audiofile("temp_audio.mp3")
            
            # Manda para a OpenAI transcrever
            audio_file = open("temp_audio.mp3", "rb")
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file,
                response_format="text"
            )
            
            st.subheader("O que foi dito no vídeo:")
            st.write(transcript)
            st.info("Agora você sabe exatamente onde estão os momentos bons para cortar!")
