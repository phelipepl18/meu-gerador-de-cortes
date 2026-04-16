import streamlit as st
from moviepy.editor import VideoFileClip, clips_array
from groq import Groq
import os
import gc
import PIL.Image

# Correção para o erro de redimensionamento
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

st.set_page_config(page_title="Gerador de Cortes Podcast", layout="wide")

# Conexão Groq
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Configure sua GROQ_API_KEY nos Secrets!")

def converter_tempo(texto):
    try:
        texto = texto.strip().replace(",", ".")
        if ":" in texto:
            partes = texto.split(":")
            return float(partes[0]) * 60 + float(partes[1])
        return float(texto)
    except: return None

st.title("🎙️ Estrategista de Cortes (Modo Podcast)")

file = st.file_uploader("Suba seu vídeo", type=["mp4", "mov"])

if file:
    with open("temp_video.mp4", "wb") as f:
        f.write(file.getbuffer())

    c1, c2 = st.columns(2)

    with c1:
        if st.button("Analisar Momentos Virais"):
            with st.spinner("IA analisando..."):
                video_full = VideoFileClip("temp_video.mp4")
                video_full.audio.write_audiofile("temp.mp3")
                with open("temp.mp3", "rb") as a:
                    trans = client.audio.transcriptions.create(file=("temp.mp3", a.read()), model="whisper-large-v3-turbo", response_format="text")
                res = client.chat.completions.create(messages=[{"role":"user","content":f"Sugira 3 cortes em MM:SS: {trans}"}], model="llama-3.1-8b-instant")
                st.session_state['dicas'] = res.choices[0].message.content
                video_full.close()
        
        if 'dicas' in st.session_state:
            st.info(st.session_state['dicas'])

    with c2:
        t_in = st.text_input("Início (ex: 01:40)", "0")
        t_out = st.text_input("Fim (ex: 02:10)", "15")
        estilo = st.radio("Formato:", ["Foco Único", "Split Screen (Duas Pessoas)"])

        if st.button("Gerar Corte"):
            t1, t2 = converter_tempo(t_in), converter_tempo(t_out)
            with st.spinner("Cortando..."):
                video = VideoFileClip("temp_video.mp4").subclip(t1, t2)
                w, h = video.size
                
                if estilo == "Foco Único":
                    tw = int(h * (9/16))
                    if tw % 2 != 0: tw -= 1
                    final = video.crop(x_center=w/2, width=tw, height=h)
                else:
                    # Lógica para podcast com troca de câmera
                    meia = w / 2
                    esq = video.crop(x1=0, y1=0, x2=meia, y2=h).resize(width=480)
                    dire = video.crop(x1=meia, y1=0, x2=w, y2=h).resize(width=480)
                    final = clips_array([[esq], [dire]]).resize(height=1080)

                final.write_videofile("corte.mp4", codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", ffmpeg_params=["-pix_fmt", "yuv420p"])
                st.video("corte.mp4")
                with open("corte.mp4", "rb") as f:
                    st.download_button("Baixar", f, "corte.mp4")
                video.close()
                gc.collect()
