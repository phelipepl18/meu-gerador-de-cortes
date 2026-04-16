import streamlit as st
from moviepy.editor import VideoFileClip
from openai import OpenAI
import os
import gc
import re

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Gerador de Cortes Virais IA", layout="wide")

# 2. CONEXÃO COM A OPENAI
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception:
    st.error("⚠️ Erro: Chave da OpenAI não encontrada!")

st.title("🚀 Estrategista de Cortes Virais")

# 3. UPLOAD
uploaded_file = st.file_uploader("Suba seu vídeo para análise", type=["mp4", "mov", "avi"])

if uploaded_file:
    temp_path = "video_original_temp.mp4"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("1. Inteligência de Conteúdo")
        if st.button("Analisar Momentos Virais"):
            with st.spinner("IA analisando o melhor gancho..."):
                try:
                    # Transcrição
                    clip_audio = VideoFileClip(temp_path)
                    clip_audio.audio.write_audiofile("audio_temp.mp3", codec='libmp3lame')
                    
                    with open("audio_temp.mp3", "rb") as audio_f:
                        transcript = client.audio.transcriptions.create(
                            model="whisper-1", 
                            file=audio_f,
                            response_format="text"
                        )
                    
                    # PEDIR PARA A IA SUGERIR CORTES
                    prompt = f"Com base nesta transcrição de vídeo, identifique os 3 momentos mais virais, engraçados ou impactantes. Para cada momento, forneça um título e o tempo estimado de início e fim em segundos. Transcrição: {transcript}"
                    
                    response = client.chat.completions.create(
                        model="gpt-4o", # Ou gpt-3.5-turbo
                        messages=[{"role": "user", "content": prompt}]
                    )
                    
                    st.session_state['analise_viral'] = response.choices[0].message.content
                    st.session_state['transcricao'] = transcript
                    clip_audio.close()
                except Exception as e:
                    st.error(f"Erro: {e}")

        if 'analise_viral' in st.session_state:
            st.success("🎯 Sugestões da IA:")
            st.write(st.session_state['analise_viral'])
            st.divider()
            with st.expander("Ver transcrição completa"):
                st.write(st.session_state['transcricao'])

    with col2:
        st.subheader("2. Gerar o Corte Escolhido")
        st.info("Escolha um dos tempos sugeridos pela IA ao lado:")
        
        c_start = st.number_input("Início (seg)", value=0.0)
        c_end = st.number_input("Fim (seg)", value=15.0)
        
        if st.button("Gerar Vídeo Selecionado"):
            with st.spinner("Criando corte em alta compatibilidade..."):
                try:
                    video = VideoFileClip(temp_path).subclip(c_start, c_end)
                    
                    # Ajuste 9:16 Par
                    w, h = video.size
                    target_w = int(h * (9/16))
                    if target_w % 2 != 0: target_w -= 1
                    
                    video_vertical = video.crop(x_center=w/2, width=target_w, height=h)

                    output_name = "corte_viral_escolhido.mp4"
                    video_vertical.write_videofile(
                        output_name,
                        codec="libx264",
                        audio_codec="aac",
                        bitrate="3000k",
                        fps=24,
                        preset="ultrafast",
                        ffmpeg_params=["-pix_fmt", "yuv420p"]
                    )

                    st.video(output_name)
                    
                    with open(output_name, "rb") as f:
                        st.download_button("⬇️ Baixar Corte Viral", f, file_name="corte.mp4")
                    
                    video.close()
                    video_vertical.close()
                    gc.collect()
                except Exception as e:
                    st.error(f"Erro: {e}")
