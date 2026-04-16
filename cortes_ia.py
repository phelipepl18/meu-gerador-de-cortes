import streamlit as st
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
    from moviepy.editor import VideoFileClip, clips_array
from groq import Groq
import os
import gc

# 1. CONFIGURAÇÃO
st.set_page_config(page_title="Gerador de Cortes Podcast", layout="wide")

# 2. CONEXÃO GROQ
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception:
    st.error("⚠️ Erro: Chave Groq não configurada!")

st.title("🎙️ Gerador de Cortes para Podcast")
st.write("Ideal para vídeos com troca de câmera ou duas pessoas.")

def processar_tempo(texto):
    try:
        texto = texto.strip().replace(",", ".")
        if ":" in texto:
            partes = texto.split(":")
            return float(partes[0]) * 60 + float(partes[1])
        return float(texto)
    except: return None

uploaded_file = st.file_uploader("Suba seu vídeo", type=["mp4", "mov", "avi"])

if uploaded_file:
    temp_path = "video_original.mp4"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("1. Análise de Ganchos")
        if st.button("Analisar com IA"):
            with st.spinner("Lendo áudio..."):
                try:
                    clip_audio = VideoFileClip(temp_path)
                    clip_audio.audio.write_audiofile("audio.mp3", codec='libmp3lame')
                    with open("audio.mp3", "rb") as f_aud:
                        transcription = client.audio.transcriptions.create(
                            file=("audio.mp3", f_aud.read()),
                            model="whisper-large-v3-turbo",
                            response_format="text"
                        )
                    prompt = f"Sugira 3 cortes virais (Início - Fim) em MM:SS. Texto: {transcription}"
                    res = client.chat.completions.create(messages=[{"role":"user","content":prompt}], model="llama-3.1-8b-instant")
                    st.session_state['sugestao'] = res.choices[0].message.content
                    clip_audio.close()
                except Exception as e: st.error(f"Erro: {e}")
        
        if 'sugestao' in st.session_state:
            st.success("Sugestões:")
            st.write(st.session_state['sugestao'])

    with col2:
        st.subheader("2. Estilo do Corte")
        t_in = st.text_input("Início (ex: 01:10)", "0")
        t_out = st.text_input("Fim (ex: 01:40)", "15")
        
        estilo = st.radio("Escolha o formato do vídeo:", 
                         ["Foco Único (Centralizado)", "Split Screen (Duas pessoas - Uma em cima da outra)"])

        if st.button("Gerar Vídeo Viral"):
            t1, t2 = processar_tempo(t_in), processar_tempo(t_out)
            if t1 is not None and t2 is not None:
                with st.spinner("Renderizando..."):
                    try:
                        video = VideoFileClip(temp_path).subclip(t1, t2)
                        w, h = video.size
                        
                        if estilo == "Foco Único (Centralizado)":
                            target_w = int(h * (9/16))
                            if target_w % 2 != 0: target_w -= 1
                            final_clip = video.crop(x_center=w/2, width=target_w, height=h)
                        
                        else:
                            # MODO SPLIT SCREEN (Empilhado)
                            # 1. Corta a pessoa da Esquerda e Direita
                            meia_largura = w / 2
                            # Ajustamos cada clipe para ser um quadrado ou proporção que caiba
                            lado_esq = video.crop(x1=0, y1=0, x2=meia_largura, y2=h).resize(width=600)
                            lado_dir = video.crop(x1=meia_largura, y1=0, x2=w, y2=h).resize(width=600)
                            
                            # 2. Empilha verticalmente
                            final_clip = clips_array([[lado_esq], [lado_dir]])
                            # Redimensiona para caber no celular (Vertical)
                            final_clip = final_clip.resize(height=1080)

                        out_name = "corte_final.mp4"
                        final_clip.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", ffmpeg_params=["-pix_fmt", "yuv420p"])
                        
                        st.video(out_name)
                        with open(out_name, "rb") as f:
                            st.download_button("Download", f, file_name="corte.mp4")
                        
                        video.close()
                        final_clip.close()
                        gc.collect()
                    except Exception as e: st.error(f"Erro: {e}")
