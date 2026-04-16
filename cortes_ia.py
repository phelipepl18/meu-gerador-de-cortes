import streamlit as st
from moviepy.editor import VideoFileClip
from openai import OpenAI
import os
import gc

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Gerador de Cortes Inteligente", layout="wide")

st.markdown("""
    <style>
    .stVideo { width: 100%; max-width: 400px; margin: auto; }
    </style>
    """, unsafe_allow_html=True)

# 2. CONEXÃO COM A OPENAI
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception:
    st.error("⚠️ Erro: Chave da OpenAI não encontrada nos Secrets!")

st.title("✂️ Gerador de Cortes Inteligente (Formato 9:16)")

# 3. UPLOAD DO ARQUIVO
uploaded_file = st.file_uploader("Escolha o arquivo", type=["mp4", "mov", "avi"])

if uploaded_file:
    temp_path = "video_original_temp.mp4"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    st.success(f"Vídeo carregado: {uploaded_file.name}")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("1. Análise da IA")
        if st.button("Transcrever Áudio"):
            with st.spinner("IA analisando..."):
                try:
                    clip_audio = VideoFileClip(temp_path)
                    clip_audio.audio.write_audiofile("audio_temp.mp3", codec='libmp3lame')
                    
                    with open("audio_temp.mp3", "rb") as audio_f:
                        transcript = client.audio.transcriptions.create(
                            model="whisper-1", 
                            file=audio_f
                        )
                    st.session_state['transcricao'] = transcript.text
                    st.success("Concluído!")
                    clip_audio.close()
                    if os.path.exists("audio_temp.mp3"): os.remove("audio_temp.mp3")
                except Exception as e:
                    st.error(f"Erro na transcrição: {e}")

        if 'transcricao' in st.session_state:
            st.text_area("Texto:", st.session_state['transcricao'], height=250)

    with col2:
        st.subheader("2. Criar o Corte")
        start_t = st.number_input("Início (seg)", min_value=0.0, step=0.5, value=0.0)
        end_t = st.number_input("Fim (seg)", min_value=0.1, step=0.5, value=15.0)
        
        if st.button("Gerar Clipe Viral (9:16)"):
            with st.spinner("Processando..."):
                try:
                    video = VideoFileClip(temp_path).subclip(start_t, end_t)
                    
                    # LÓGICA 9:16 COM AJUSTE PARA NÚMEROS PARES
                    w, h = video.size
                    target_w = int(h * (9/16))
                    
                    # GARANTE QUE A LARGURA SEJA PAR (Resolve o erro 607x1080)
                    if target_w % 2 != 0:
                        target_w -= 1
                    
                    if w > target_w:
                        video_vertical = video.crop(x_center=w/2, width=target_w, height=h)
                    else:
                        video_vertical = video

                    output_name = "corte_final.mp4"
                    video_vertical.write_videofile(
                        output_name,
                        codec="libx264",
                        audio_codec="aac",
                        bitrate="3000k",
                        fps=24,
                        preset="ultrafast",
                        threads=4,
                        ffmpeg_params=["-pix_fmt", "yuv420p"]
                    )

                    st.video(output_name)
                    
                    with open(output_name, "rb") as f:
                        st.download_button(
                            label="⬇️ Baixar Vídeo",
                            data=f,
                            file_name="meu_corte_viral.mp4",
                            mime="video/mp4"
                        )
                    
                    video.close()
                    video_vertical.close()
                    gc.collect()

                except Exception as e:
                    st.error(f"Erro ao gerar vídeo: {e}")

st.divider()
st.info("Ajuste automático de escala par aplicado para evitar erros de renderização.")
