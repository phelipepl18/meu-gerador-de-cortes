import streamlit as st
from moviepy.editor import VideoFileClip, clips_array
from groq import Groq
import os
import gc
import PIL.Image

# Correção para o erro de redimensionamento em versões novas do Pillow
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Gerador de Cortes Podcast", layout="wide")

# 2. CONEXÃO COM A GROQ (Secrets)
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("⚠️ Erro: Configure GROQ_API_KEY nos Secrets do Streamlit!")

# FUNÇÃO PARA CONVERTER MM:SS PARA SEGUNDOS
def converter_tempo_para_segundos(tempo_texto):
    try:
        tempo_texto = tempo_texto.strip().replace(",", ".")
        if ":" in tempo_texto:
            partes = tempo_texto.split(":")
            if len(partes) == 2:
                return float(partes[0]) * 60 + float(partes[1])
        return float(tempo_texto)
    except Exception as e:
        return None

st.title("🎙️ Estrategista de Cortes (Modo Podcast)")

# 3. UPLOAD DO VÍDEO
file = st.file_uploader("Suba seu vídeo original", type=["mp4", "mov", "avi"])

if file:
    # Salva o vídeo temporariamente no servidor
    temp_path = "video_original_temp.mp4"
    with open(temp_path, "wb") as f:
        f.write(file.getbuffer())

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. Análise da IA")
        if st.button("Analisar Momentos Virais"):
            with st.spinner("IA transcrevendo e analisando..."):
                try:
                    video_full = VideoFileClip(temp_path)
                    video_full.audio.write_audiofile("audio_temp.mp3", codec='libmp3lame')
                    
                    with open("audio_temp.mp3", "rb") as a_file:
                        transcription = client.audio.transcriptions.create(
                            file=("audio_temp.mp3", a_file.read()),
                            model="whisper-large-v3-turbo",
                            response_format="text"
                        )
                    
                    prompt = f"Analise o texto e sugira 3 cortes virais com Início e Fim em MM:SS. Texto: {transcription}"
                    res = client.chat.completions.create(
                        messages=[{"role": "user", "content": prompt}],
                        model="llama-3.1-8b-instant"
                    )
                    st.session_state['analise'] = res.choices[0].message.content
                    video_full.close()
                except Exception as e:
                    st.error(f"Erro na IA: {e}")

        if 'analise' in st.session_state:
            st.info(st.session_state['analise'])

    with col2:
        st.subheader("2. Configurar o Corte")
        # Usamos st.text_input para aceitar o formato 01:40
        t_in_raw = st.text_input("Tempo de Início (ex: 01:40)", value="0")
        t_out_raw = st.text_input("Tempo de Fim (ex: 02:10)", value="15")
        
        estilo = st.radio("Formato de Saída:", ["Foco Único (Centro)", "Split Screen (Podcast)"])

        if st.button("🚀 Gerar e Recortar Vídeo"):
            # Converte os tempos para segundos reais (float)
            start_sec = converter_tempo_para_segundos(t_in_raw)
            end_sec = converter_tempo_para_segundos(t_out_raw)

            if start_sec is None or end_sec is None:
                st.error("❌ Formato de tempo inválido. Use 01:30 ou apenas segundos.")
            elif end_sec <= start_sec:
                st.error("❌ O tempo de fim deve ser maior que o de início.")
            else:
                with st.spinner(f"Recortando de {start_sec}s até {end_sec}s..."):
                    try:
                        # Carrega apenas o trecho necessário para economizar memória
                        with VideoFileClip(temp_path) as video:
                            clip = video.subclip(start_sec, end_sec)
                            w, h = clip.size
                            
                            if estilo == "Foco Único (Centro)":
                                target_w = int(h * (9/16))
                                if target_w % 2 != 0: target_w -= 1
                                final_clip = clip.crop(x_center=w/2, width=target_w, height=h)
                            else:
                                # Modo Split Screen para Podcasts
                                meia_w = w / 2
                                esq = clip.crop(x1=0, y1=0, x2=meia_w, y2=h).resize(width=480)
                                dire = clip.crop(x1=meia_w, y1=0, x2=w, y2=h).resize(width=480)
                                final_clip = clips_array([[esq], [dire]]).resize(height=1080)

                            output = "corte_finalizado.mp4"
                            final_clip.write_videofile(
                                output, 
                                codec="libx264", 
                                audio_codec="aac", 
                                fps=24, 
                                preset="ultrafast",
                                ffmpeg_params=["-pix_fmt", "yuv420p"]
                            )

                            st.video(output)
                            with open(output, "rb") as f:
                                st.download_button("⬇️ Baixar Corte", f, file_name="meu_corte.mp4")
                        
                        gc.collect()
                    except Exception as e:
                        st.error(f"Erro ao processar vídeo: {e}")
