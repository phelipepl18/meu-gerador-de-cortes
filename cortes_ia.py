import streamlit as st
from moviepy.editor import VideoFileClip, clips_array
from groq import Groq
import os
import gc
import PIL.Image

# Correção Pillow para evitar erro de redimensionamento
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

st.set_page_config(page_title="Gerador de Cortes Podcast", layout="wide")

# Conexão com a API via Secrets
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("⚠️ Configure a GROQ_API_KEY nos Secrets do Streamlit!")

# Função para aceitar formato 2:00
def converter_tempo(texto):
    try:
        texto = texto.strip().replace(",", ".")
        if ":" in texto:
            partes = texto.split(":")
            return (int(partes[0]) * 60) + float(partes[1])
        return float(texto)
    except:
        return None

st.title("🎙️ Estrategista de Cortes (Modo Podcast)")

file = st.file_uploader("Suba seu vídeo", type=["mp4", "mov", "avi"])

if file:
    temp_path = "video_original_temp.mp4"
    with open(temp_path, "wb") as f:
        f.write(file.getbuffer())

    with VideoFileClip(temp_path) as v_info:
        duracao_real = v_info.duration
        m_tot, s_tot = int(duracao_real // 60), int(duracao_real % 60)
        st.warning(f"📏 Duração Real: {m_tot:02d}:{s_tot:02d}")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. Sugestões da IA")
        if st.button("Analisar Momentos Virais"):
            with st.spinner("Analisando..."):
                try:
                    with VideoFileClip(temp_path) as video_full:
                        video_full.audio.write_audiofile("audio_temp.mp3", codec='libmp3lame')
                    
                    with open("audio_temp.mp3", "rb") as a_file:
                        trans = client.audio.transcriptions.create(
                            file=("audio_temp.mp3", a_file.read()),
                            model="whisper-large-v3-turbo",
                            response_format="text"
                        )
                    
                    # Prompt que obriga a IA a respeitar o tempo real do vídeo
                    prompt = (
                        f"O vídeo tem {m_tot:02d}:{s_tot:02d}. Sugira 3 cortes. "
                        f"O tempo de FIM nunca pode ser maior que {m_tot:02d}:{s_tot:02d}. "
                        f"Responda no formato: [Início MM:SS - Fim MM:SS]. Texto: {trans}"
                    )
                    
                    res = client.chat.completions.create(
                        messages=[{"role": "user", "content": prompt}],
                        model="llama-3.1-8b-instant"
                    )
                    st.session_state['analise'] = res.choices[0].message.content
                except Exception as e:
                    st.error(f"Erro: {e}")

        if 'analise' in st.session_state:
            st.info(st.session_state['analise'])

    with col2:
        st.subheader("2. Gerar o Corte")
        # Aceita o formato 2:00 que você pediu
        t_in = st.text_input("Início (ex: 2:00)", value="0:00")
        t_out = st.text_input("Fim (ex: 2:30)", value="0:30")
        
        estilo = st.radio("Formato:", ["Foco Único (Centro)", "Split Screen (Podcast)"])

        if st.button("🚀 Gerar Vídeo"):
            start = converter_tempo(t_in)
            end = converter_tempo(t_out)

            if start is not None and end is not None:
                if end > duracao_real:
                    st.error(f"❌ O fim ({t_out}) é maior que o vídeo!")
                elif start < end:
                    with st.spinner("Cortando..."):
                        try:
                            with VideoFileClip(temp_path) as video:
                                clip = video.subclip(start, end)
                                # Lógica de redimensionamento
                                if estilo == "Foco Único (Centro)":
                                    w, h = clip.size
                                    target_w = int(h * (9/16))
                                    if target_w % 2 != 0: target_w -= 1
                                    final = clip.crop(x_center=w/2, width=target_w, height=h)
                                else:
                                    w, h = clip.size
                                    esq = clip.crop(x1=0, x2=w/2).resize(width=480)
                                    dire = clip.crop(x1=w/2, x2=w).resize(width=480)
                                    final = clips_array([[esq], [dire]]).resize(height=1080)

                                final.write_videofile("corte.mp4", codec="libx264", audio_codec="aac", fps=24)
                                st.video("corte.mp4")
                        except Exception as e:
                            st.error(f"Erro no MoviePy: {e}")
            gc.collect()
