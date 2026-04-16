import streamlit as st
from moviepy.editor import VideoFileClip, clips_array
from groq import Groq
import os
import gc
import PIL.Image

# Correção Pillow
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

st.set_page_config(page_title="Gerador de Cortes Podcast", layout="wide")

# Conexão Groq
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("⚠️ Configure a GROQ_API_KEY nos Secrets!")

def converter_tempo_para_segundos(tempo_texto):
    try:
        tempo_texto = tempo_texto.strip().replace(",", ".")
        if ":" in tempo_texto:
            partes = tempo_texto.split(":")
            if len(partes) == 2:
                return float(partes[0]) * 60 + float(partes[1])
        return float(tempo_texto)
    except: return None

st.title("🎙️ Estrategista de Cortes (Modo Podcast)")

file = st.file_uploader("Suba seu vídeo", type=["mp4", "mov", "avi"])

if file:
    temp_path = "video_original_temp.mp4"
    with open(temp_path, "wb") as f:
        f.write(file.getbuffer())

    # Carrega o vídeo uma vez para saber a duração
    with VideoFileClip(temp_path) as v_info:
        duracao_total = v_info.duration
        st.warning(f"📏 Duração do vídeo original: {duracao_total:.2f} segundos (aprox. {int(duracao_total//60)}min {int(duracao_total%60)}s)")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("1. Analisar Momentos Virais"):
            with st.spinner("IA analisando..."):
                try:
                    with VideoFileClip(temp_path) as video_full:
                        video_full.audio.write_audiofile("audio_temp.mp3", codec='libmp3lame')
                    with open("audio_temp.mp3", "rb") as a_file:
                        trans = client.audio.transcriptions.create(file=("audio_temp.mp3", a_file.read()), model="whisper-large-v3-turbo", response_format="text")
                    prompt = f"Sugira 3 cortes em MM:SS dentro do limite de {duracao_total} segundos. Texto: {trans}"
                    res = client.chat.completions.create(messages=[{"role":"user","content":prompt}], model="llama-3.1-8b-instant")
                    st.session_state['analise'] = res.choices[0].message.content
                except Exception as e: st.error(f"Erro na IA: {e}")

        if 'analise' in st.session_state:
            st.info(st.session_state['analise'])

    with col2:
        st.subheader("2. Configurar o Corte")
        t_in_raw = st.text_input("Início (ex: 01:20)", value="0")
        t_out_raw = st.text_input("Fim (ex: 01:50)", value="30")
        estilo = st.radio("Formato:", ["Foco Único (Centro)", "Split Screen (Podcast)"])

        if st.button("🚀 Gerar Vídeo"):
            start_sec = converter_tempo_para_segundos(t_in_raw)
            end_sec = converter_tempo_para_segundos(t_out_raw)

            if start_sec is None or end_sec is None:
                st.error("❌ Formato de tempo inválido!")
            elif start_sec >= duracao_total:
                st.error(f"❌ O início ({start_sec}s) não pode ser maior que o vídeo ({duracao_total}s)!")
            elif end_sec > duracao_total:
                st.error(f"❌ O fim ({end_sec}s) é maior que o vídeo. Ajustando para o final real...")
                end_sec = duracao_total

            if start_sec < end_sec:
                with st.spinner("Processando..."):
                    try:
                        with VideoFileClip(temp_path) as video:
                            clip = video.subclip(start_sec, end_sec)
                            w, h = clip.size
                            if estilo == "Foco Único (Centro)":
                                tw = int(h * (9/16))
                                if tw % 2 != 0: tw -= 1
                                final = clip.crop(x_center=w/2, width=tw, height=h)
                            else:
                                meia = w / 2
                                esq = clip.crop(x1=0, x2=meia).resize(width=480)
                                dire = clip.crop(x1=meia, x2=w).resize(width=480)
                                final = clips_array([[esq], [dire]]).resize(height=1080)

                            final.write_videofile("corte_ok.mp4", codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", ffmpeg_params=["-pix_fmt", "yuv420p"])
                            st.video("corte_ok.mp4")
                            with open("corte_ok.mp4", "rb") as f:
                                st.download_button("Download", f, "corte.mp4")
                        gc.collect()
                    except Exception as e: st.error(f"Erro: {e}")
