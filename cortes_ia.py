import streamlit as st
from moviepy.editor import VideoFileClip
from groq import Groq
import os
import gc

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Gerador de Cortes Virais", layout="wide")

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

st.title("🚀 Estrategista de Cortes Virais")

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
        st.subheader("2. Ajuste do Corte e Foco")
        
        # Inputs de Tempo
        t_inicio_input = st.text_input("Início do corte (ex: 01:10)", value="0", key="start_raw")
        t_fim_input = st.text_input("Fim do corte (ex: 01:45)", value="15", key="end_raw")
        
        st.divider()
        
        # NOVO: Controle de Foco (Câmera Virtual)
        st.write("📽️ **Ajuste o foco da câmera (Face Tracking Manual)**")
        foco_pos = st.slider("Esquerda <---> Direita", -1.0, 1.0, 0.0, 0.1, help="Use isso para centralizar a pessoa que está falando.")
        
        if st.button("Gerar Vídeo com Foco Selecionado"):
            t_inicio = processar_tempo(t_inicio_input)
            t_fim = processar_tempo(t_fim_input)
            
            if t_inicio is None or t_fim is None:
                st.error("Formato de tempo inválido!")
            elif t_fim <= t_inicio:
                st.error("O fim deve ser maior que o início!")
            else:
                with st.spinner("Cortando e enquadrando falante..."):
                    try:
                        with VideoFileClip(temp_path) as video_full:
                            video_cut = video_full.subclip(t_inicio, t_fim)
                            
                            # Lógica de Enquadramento 9:16
                            w, h = video_cut.size
                            target_w = int(h * (9/16))
                            if target_w % 2 != 0: target_w -= 1
                            
                            # Cálculo do centro com base no Slider
                            centro_original = w / 2
                            # Distância máxima que o corte pode "correr" para os lados
                            margem_movimento = (w - target_w) / 2
                            novo_centro = centro_original + (margem_movimento * foco_pos)
                            
                            # Aplica o corte focado
                            final_video = video_cut.crop(x_center=novo_centro, width=target_w, height=h)
                            
                            output_name = "corte_focado.mp4"
                            final_video.write_videofile(
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
                                st.download_button("⬇️ Baixar Corte Focado", f, file_name="corte_viral.mp4")
                            
                            final_video.close()
                            video_cut.close()
                            gc.collect()

                    except Exception as e:
                        st.error(f"Erro ao processar: {e}")

st.info("💡 Dica: Se no vídeo original a pessoa está na esquerda, mova o slider para a esquerda. Se houver duas pessoas, use o slider para escolher qual delas quer focar no corte.")
