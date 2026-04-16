import streamlit as st
from moviepy.editor import VideoFileClip, clips_array
from groq import Groq
import os
import gc
import PIL.Image

# CORREÇÃO DO ERRO 'ANTIALIAS' (Pillow 10+)
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Gerador de Cortes Podcast", layout="wide")

st.markdown("""
    <style>
    .stVideo { width: 100%; max-width: 400px; margin: auto; }
    </style>
    """, unsafe_allow_html=True)

# 2. CONEXÃO COM A GROQ
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception:
    st.error("⚠️ Erro: Configure GROQ_API_KEY nos Secrets!")

st.title("🎙️ Estrategista de Cortes (Modo Podcast)")

# Função para converter "01:40" ou "100" em segundos
def processar_tempo(texto):
    try:
        texto = texto.strip().replace(",", ".")
        if ":" in texto:
            partes = texto.split(":")
            if len(partes) == 2:
                return float(partes[0]) * 60 + float(partes[1])
        return float(texto)
    except:
        return None

# 3. UPLOAD DO VÍDEO
uploaded_file = st.file_uploader("Suba seu vídeo original", type=["mp4", "mov", "avi"])

if uploaded_file:
    temp_path = "video_original_temp.mp4"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("1. Análise da IA")
        if st.button("Analisar Momentos Virais"):
            with st.spinner("IA analisando ganchos..."):
                try:
                    clip_audio = VideoFileClip(temp_path)
                    clip_audio.audio.write_audiofile("audio_temp.mp3", codec='libmp3lame')
                    
                    with open("audio_temp.mp3", "rb") as audio_file:
                        transcription = client.audio.transcriptions.create(
                            file=("audio_temp.mp3", audio_file.read()),
                            model="whisper-large-v3-turbo",
                            response_format="text"
                        )
                    
                    prompt = f"Analise o texto e sugira 3 cortes virais com tempo de início e fim. Use o formato MM:SS (ex: 01:40). Texto: {transcription}"
                    
                    chat_completion = client.chat.completions.create(
                        messages=[{"role": "user", "content": prompt}],
                        model="llama-3.1-8b-instant",
                    )
                    
                    st.session_state['analise_viral'] = chat_completion.choices[0].message.content
                    clip_audio.close()
                    os.remove("audio_temp.mp3")
                except Exception as e:
                    st.error(f"Erro na análise: {e}")

        if 'analise_viral' in st.session_state:
            st.success("🎯 Sugestões da IA:")
            st.write(st.session_state['analise_viral'])

    with col2:
        st.subheader("2. Estilo e Geração")
        t_inicio_input = st.text_input("Início (ex: 01:10)", value="0")
        t_fim_input = st.text_input("Fim (ex: 01:45)", value="15")
        
        # Opção para resolver o problema da troca de câmera
        estilo = st.selectbox("Formato do Vídeo", 
                             ["Foco Único (Centralizado)", "Split Screen (Pessoa em cima e outra embaixo)"])
        
        if st.button("Gerar Vídeo Viral"):
            t_inicio = processar_tempo(t_inicio_input)
            t_fim = processar_tempo(t_fim_input)
            
            if t_inicio is None or t_fim is None:
                st.error("Tempo inválido!")
            else:
                with st.spinner("Renderizando vídeo vertical..."):
                    try:
                        video = VideoFileClip(temp_path).subclip(t_inicio, t_fim)
                        w, h = video.size
                        
                        if estilo == "Foco Único (Centralizado)":
                            target_w = int(h * (9/16))
                            if target_w % 2 != 0: target_w -= 1
                            final_clip = video.crop(x_center=w/2, width=target_w, height=h)
                        
                        else:
                            # MODO SPLIT SCREEN (Para Podcasts)
                            # Pega o lado esquerdo e direito e empilha
                            meia_w = w / 2
                            # Redimensionamos para manter qualidade sem estourar memória
                            lado_esq = video.crop(x1=0, y1=0, x2=meia_w, y2=h).resize(width=480)
                            lado_dir = video.crop(x1=meia_w, y1=0, x2=w, y2=h).resize(width=480)
                            
                            final_clip = clips_array([[lado_esq], [lado_dir]])
                            # Ajuste final para o tamanho vertical padrão
                            final_clip = final_clip.resize(height=1080)

                        output_name = "corte_final.mp4"
                        final_clip.write_videofile(
                            output_name,
                            codec="libx264",
                            audio_codec="aac",
                            bitrate="2500k",
                            fps=24,
                            preset="ultrafast",
                            ffmpeg_params=["-pix_fmt", "yuv420p"]
                        )

                        st.video(output_name)
                        with open(output_name, "rb") as f:
                            st.download_button("⬇️ Baixar Vídeo", f, file_name="corte.mp4")
                        
                        video.close()
                        final_clip.close()
                        gc.collect()
                    except Exception as e:
                        st.error(f"Erro no processamento: {e}")

# Limpeza de segurança
if os.path.exists("corte_final.mp4") and not uploaded_file:
    os.remove("corte_final.mp4")
