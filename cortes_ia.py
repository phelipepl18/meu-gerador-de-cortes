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

# FUNÇÃO DE CONVERSÃO QUE ACEITA 2:00 ou 02:30
def converter_tempo(texto):
    try:
        texto = texto.strip().replace(",", ".")
        if ":" in texto:
            partes = texto.split(":")
            minutos = int(partes[0])
            segundos = float(partes[1])
            return (minutos * 60) + segundos
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
        min_totais = int(duracao_real // 60)
        seg_totais = int(duracao_real % 60)
        st.warning(f"📏 Duração do vídeo: {min_totais:02d}:{seg_totais:02d} ({duracao_real:.2f} segundos)")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. Análise da IA")
        if st.button("Analisar Momentos Virais"):
            with st.spinner("IA analisando..."):
                try:
                    with VideoFileClip(temp_path) as video_full:
                        video_full.audio.write_audiofile("audio_temp.mp3", codec='libmp3lame')
                    
                    with open("audio_temp.mp3", "rb") as a_file:
                        trans = client.audio.transcriptions.create(
                            file=("audio_temp.mp3", a_file.read()),
                            model="whisper-large-v3-turbo",
                            response_format="text"
                        )
                    
                    # PROMPT REFORÇADO PARA NÃO SUGERIR TEMPO ERRADO
                    prompt = (
                        f"O vídeo tem EXATAMENTE {min_totais:02d}:{seg_totais:02d}. "
                        f"Sugira 3 cortes virais. O tempo de FIM nunca pode ultrapassar {min_totais:02d}:{seg_totais:02d}. "
                        f"Formato: [Início MM:SS - Fim MM:SS]. Texto: {trans}"
                    )
                    
                    res = client.chat.completions.create(
                        messages=[{"role": "user", "content": prompt}],
                        model="llama-3.1-8b-instant"
                    )
                    st.session_state['analise'] = res.choices[0].message.content
                except Exception as e:
                    st.error(f"Erro na IA: {e}")

        if 'analise' in st.session_state:
            st.info(st.session_state['analise'])

    with col2:
        st.subheader("2. Configurar o Corte")
        # Agora você pode digitar 2:00 tranquilamente
        t_in_raw = st.text_input("Início (ex: 1:30 ou 01:30)", value="0:00")
        t_out_raw = st.text_input("Fim (ex: 2:00 ou 02:00)", value="0:30")
        
        estilo = st.radio("Formato:", ["Foco Único (Centro)", "Split Screen (Podcast)"])

        if st.button("🚀 Gerar Vídeo"):
            start_sec = converter_tempo(t_in_raw)
            end_sec = converter_tempo(t_out_raw)

            if start_sec is None or end_sec is None:
                st.error("❌ Formato de tempo inválido! Use o padrão Minutos:Segundos (ex: 2:00)")
            elif start_sec >= duracao_real:
                st.error(f"❌ O início ({t_in_raw}) ultrapassa a duração do vídeo!")
            elif end_sec > duracao_real:
                st.warning(f"⚠️ O fim ({t_out_raw}) era maior que o vídeo. Ajustando para o final real.")
                end_sec = duracao_real

            if start_sec is not None and end_sec is not None and start_sec < end_sec:
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

                            final.write_videofile("corte_ok.mp4", codec="libx264", audio_codec="aac", fps=24, preset="ultrafast")
                            st.video("corte_ok.mp4")
                            with open("corte_ok.mp4", "rb") as f:
                                st.download_button("Download", f, "corte.mp4")
                        gc.collect()
                    except Exception as e:
                        st.error(f"Erro: {e}")
