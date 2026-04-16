import streamlit as st
from moviepy.editor import VideoFileClip
from openai import OpenAI
import os

# Configuração da IA
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="IA de Cortes Virais", layout="wide")
st.title("🤖 Gerador de Cortes Inteligente")

uploaded_file = st.file_uploader("Suba seu vídeo original (max 5 min)", type=["mp4", "mov"])

if uploaded_file:
    # Salva o vídeo temporário
    with open("video_original.mp4", "wb") as f:
        f.write(uploaded_file.read())
    
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. Análise da IA")
        if st.button("Transcrever Áudio"):
            with st.spinner("A IA está ouvindo o vídeo..."):
                video = VideoFileClip("video_original.mp4")
                video.audio.write_audiofile("audio.mp3")
                
                # Transcrição com Whisper
                audio_file = open("audio.mp3", "rb")
                transcript = client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file
                )
                st.session_state['transcricao'] = transcript.text
                st.success("Transcrição concluída!")
        
        if 'transcricao' in st.session_state:
            st.text_area("Texto detectado:", st.session_state['transcricao'], height=200)

    with col2:
        st.subheader("2. Criar o Corte")
        start_t = st.number_input("Início (segundos)", min_value=0.0, value=0.0)
        end_t = st.number_input("Fim (segundos)", min_value=0.0, value=30.0)
        
        if st.button("Gerar Clipe Viral (9:16)"):
            with st.spinner("Cortando e formatando..."):
                clip = VideoFileClip("video_original.mp4").subclip(start_t, end_t)
                
                # Transforma em vertical (9:16)
                w, h = clip.size
                target_w = h * (9/16)
                final_clip = clip.crop(x_center=w/2, width=target_w, height=h)
                
                output_name = "corte_final.mp4"
                final_clip.write_videofile(output_name, codec="libx264")
                
                st.video(output_name)
                with open(output_name, "rb") as f:
                    st.download_button("Baixar Corte", f, file_name="corte_viral.mp4")
