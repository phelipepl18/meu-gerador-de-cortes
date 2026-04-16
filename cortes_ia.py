import streamlit as st
from moviepy.editor import VideoFileClip, clips_array
from groq import Groq
import os
import gc
import PIL.Image

# 1. CORREÇÃO DE REDIMENSIONAMENTO (PILLOW)
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

st.set_page_config(page_title="Gerador de Cortes Podcast", layout="wide")

# 2. CONEXÃO COM A GROQ (SECRETS)
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    st.error("⚠️ Configure a GROQ_API_KEY corretamente nos Secrets do Streamlit!")

# 3. CONVERSOR DE TEMPO (MM:SS para SEGUNDOS)
def converter_tempo(texto):
    try:
        texto = texto.strip().replace(",", ".")
        if ":" in texto:
            partes = texto.split(":")
            # Aceita 2:00 ou 02:00
            return (int(partes[0]) * 60) + float(partes[1])
        return float(texto)
    except:
        return None

st.title("🎙️ Estrategista de Cortes (Modo Podcast)")

# 4. UPLOAD DO VÍDEO
file = st.file_uploader("Suba seu vídeo original", type=["mp4", "mov", "avi"])

if file:
    temp_path = "video_original_temp.mp4"
    with open(temp_path, "wb") as f:
        f.write(file.getbuffer())

    # Pegamos a duração exata para travar a IA
    with VideoFileClip(temp_path) as v_info:
        duracao_real = v_info.duration
        m_total = int(duracao_real // 60)
        s_total = int(duracao_real % 60)
        st.warning(f"📏 Duração do vídeo: {m_total:02d}:{s_total:02d} (Total: {duracao_real:.2f}s)")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. Análise da IA")
        if st.button("Analisar Momentos Virais"):
            with st.spinner("IA processando áudio e texto..."):
                try:
                    with VideoFileClip(temp_path) as video_full:
                        video_full.audio.write_audiofile("audio_temp.mp3", codec='libmp3lame')
                    
                    with open("audio_temp.mp3", "rb") as a_file:
                        trans = client.audio.transcriptions.create(
                            file=("audio_temp.mp3", a_file.read()),
                            model="whisper-large-v3-turbo",
                            response_format="text"
                        )
                    
                    # PROMPT RÍGIDO: Impede a IA de sugerir tempos maiores que o vídeo
                    prompt = (
                        f"O vídeo tem EXATAMENTE {m_total:02d}:{s_total:02d}. "
                        f"Sugira 3 cortes virais baseados no texto. "
                        f"O tempo de FIM NUNCA pode ultrapassar {m_total:02d}:{s_total:02d}. "
                        f"Responda apenas com: Título, Tempo [MM:SS - MM:SS] e Justificativa. "
                        f"Texto: {trans}"
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
        # Inputs agora aceitam 2:00 conforme solicitado
        t_in_raw = st.text_input("Início (ex: 2:00)", value="0:00")
        t_out_raw = st.text_input("Fim (ex: 2:30)", value="0:30")
        
        estilo = st.radio("Formato:", ["Foco Único (Centro)", "Split Screen (Podcast)"])

        if st.button("🚀 Gerar e Cortar"):
            start_sec = converter_tempo(t_in_raw)
            end_sec = converter_tempo(t_out_raw)

            if start_sec is None or end_sec is None:
                st.error("❌ Use o formato Minuto:Segundo (ex: 2:00)")
            elif start_sec >= duracao_real:
                st.error("❌ O tempo de início é maior que o vídeo!")
            elif end_sec > duracao_real:
                st.warning("⚠️ Tempo final ajustado para o limite máximo do vídeo.")
                end_sec = duracao_real

            if start_sec < end_sec:
                with st.spinner("Renderizando corte..."):
                    try:
                        with VideoFileClip(temp_path) as video:
                            clip = video.subclip(start_sec, end_sec)
                            w, h = clip.size
                            
                            if estilo == "Foco Único (Centro)":
                                target_w = int(h * (9/16))
                                if target_w % 2 != 0: target_w -= 1
                                final = clip.crop(x_center=w/2, width=target_w, height=h)
                            else:
                                # Split Screen para Podcast
                                meia = w / 2
                                esq = clip.crop(x1=0, x2=meia).resize(width=480)
                                dire = clip.crop(x1=meia, x2=w).resize(width=480)
                                final = clips_array([[esq], [dire]]).resize(height=1080)

                            output_name = "resultado_corte.mp4"
                            final.write_videofile(output_name, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast")
                            
                            st.video(output_name)
                            with open(output_name, "rb") as f:
                                st.download_button("⬇️ Baixar Corte", f, file_name="corte_viral.mp4")
                        gc.collect()
                    except Exception as e:
                        st.error(f"Erro no processamento: {e}")
