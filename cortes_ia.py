import streamlit as st
from moviepy.editor import VideoFileClip, clips_array, ImageClip, CompositeVideoClip
from groq import Groq
import os
import gc
import PIL.Image

# Correção de compatibilidade Pillow
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

st.set_page_config(page_title="Gerador de Cortes Podcast", layout="wide")

# Conexão segura com a API
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("⚠️ Configure a GROQ_API_KEY nos Secrets!")

# Função que aceita formato 2:00
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

# Uploads
file = st.file_uploader("1. Suba seu vídeo original", type=["mp4", "mov", "avi"])
bg_image = st.file_uploader("2. Opcional: Suba uma imagem de fundo (Para o modo Fundo Personalizado)", type=["jpg", "jpeg", "png"])

if file:
    temp_path = "video_original_temp.mp4"
    with open(temp_path, "wb") as f:
        f.write(file.getbuffer())

    with VideoFileClip(temp_path) as v_info:
        duracao_real = v_info.duration
        m_tot, s_tot = int(duracao_real // 60), int(duracao_real % 60)
        st.warning(f"📏 Duração do vídeo: {m_tot:02d}:{s_tot:02d}")

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
                    
                    prompt = (
                        f"O vídeo tem {m_tot:02d}:{s_tot:02d}. Sugira 3 cortes virais. "
                        f"O tempo final nunca pode passar de {m_tot:02d}:{s_tot:02d}. "
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
        t_in_raw = st.text_input("Início (ex: 2:00)", value="0:00")
        t_out_raw = st.text_input("Fim (ex: 2:30)", value="0:30")
        
        estilo = st.radio("Formato de Saída:", 
                         ["Foco Único (Centro)", "Split Screen (Podcast)", "Fundo Personalizado (Vídeo no meio)"])

        if st.button("🚀 Gerar Vídeo"):
            start_sec = converter_tempo(t_in_raw)
            end_sec = converter_tempo(t_out_raw)

            if start_sec is not None and end_sec is not None and start_sec < end_sec:
                if end_sec > duracao_real: end_sec = duracao_real
                
                with st.spinner("Processando vídeo..."):
                    try:
                        with VideoFileClip(temp_path) as video:
                            clip = video.subclip(start_sec, end_sec)
                            w, h = clip.size
                            
                            if estilo == "Foco Único (Centro)":
                                tw = int(h * (9/16))
                                if tw % 2 != 0: tw -= 1
                                final = clip.crop(x_center=w/2, width=tw, height=h)
                                
                            elif estilo == "Split Screen (Podcast)":
                                esq = clip.crop(x1=0, x2=w/2).resize(width=480)
                                dire = clip.crop(x1=w/2, x2=w).resize(width=480)
                                final = clips_array([[esq], [dire]]).resize(height=1080)
                                
                            elif estilo == "Fundo Personalizado (Vídeo no meio)":
                                if bg_image is None:
                                    st.error("❌ Para este modo, você precisa subir uma imagem de fundo acima!")
                                    st.stop()
                                
                                # Salva imagem temporária
                                with open("bg_temp.png", "wb") as f:
                                    f.write(bg_image.getbuffer())
                                
                                # Cria o fundo (1080x1920 padrão Reels)
                                bg_clip = ImageClip("bg_temp.png").set_duration(clip.duration).resize(height=1920)
                                if bg_clip.w < 1080: bg_clip = bg_clip.resize(width=1080)
                                bg_clip = bg_clip.crop(x_center=bg_clip.w/2, y_center=bg_clip.h/2, width=1080, height=1920)
                                
                                # Redimensiona o vídeo para a largura da imagem (horizontal)
                                video_meio = clip.resize(width=1080)
                                
                                # Sobrepõe o vídeo no centro do fundo
                                final = CompositeVideoClip([bg_clip, video_meio.set_position("center")])

                            output = "corte_final.mp4"
                            final.write_videofile(output, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast")
                            
                            st.video(output)
                            with open(output, "rb") as f:
                                st.download_button("⬇️ Baixar Corte", f, "corte.mp4")
                        gc.collect()
                    except Exception as e:
                        st.error(f"Erro no processamento: {e}")
