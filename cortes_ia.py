import streamlit as st
from moviepy.editor import VideoFileClip, clips_array, ImageClip, CompositeVideoClip, ColorClip
from groq import Groq
import os
import gc
from PIL import Image, ImageDraw, ImageFont

# --- CORREÇÃO CRÍTICA PARA O ERRO 'ANTIALIAS' ---
import PIL.Image
if not hasattr(PIL.Image, 'Resampling'):
    # Para versões muito antigas do Pillow
    PIL.Image.LANCZOS = PIL.Image.ANTIALIAS
else:
    # Para versões novas (Pillow 10+)
    PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS
    PIL.Image.LANCZOS = PIL.Image.Resampling.LANCZOS
# ----------------------------------------------

st.set_page_config(page_title="Estrategista de Cortes Profissional", layout="wide")

# Conexão Groq
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("⚠️ Configure a GROQ_API_KEY nos Secrets do Streamlit!")

# Função para converter MM:SS em segundos
def converter_tempo(texto):
    try:
        texto = texto.strip().replace(",", ".")
        if ":" in texto:
            partes = texto.split(":")
            return (int(partes[0]) * 60) + float(partes[1])
        return float(texto)
    except:
        return None

# Função para criar o texto do Tema Forte usando Pillow
def criar_imagem_texto(texto, largura=1080):
    img = Image.new('RGBA', (largura, 300), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        # Tenta carregar uma fonte negritada padrão do Linux/Streamlit
        font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 75)
    except:
        font = ImageFont.load_default()
    
    w_txt, h_txt = draw.textbbox((0, 0), texto, font=font)[2:4]
    draw.text(((largura - w_txt) / 2, (300 - h_txt) / 2), texto, font=font, fill="white")
    path = "titulo_temp.png"
    img.save(path)
    return path

st.title("🎙️ Estrategista de Cortes Profissional")

col_up1, col_up2 = st.columns(2)
with col_up1:
    file = st.file_uploader("1. Suba seu vídeo original", type=["mp4", "mov", "avi"])
with col_up2:
    bg_image = st.file_uploader("2. Suba a imagem de fundo", type=["jpg", "jpeg", "png"])

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
            with st.spinner("IA processando áudio..."):
                try:
                    with VideoFileClip(temp_path) as video_full:
                        video_full.audio.write_audiofile("audio_temp.mp3", codec='libmp3lame')
                    with open("audio_temp.mp3", "rb") as a_file:
                        trans = client.audio.transcriptions.create(
                            file=("audio_temp.mp3", a_file.read()),
                            model="whisper-large-v3-turbo",
                            response_format="text"
                        )
                    st.session_state['transcricao'] = trans
                    prompt = (f"O vídeo tem {m_tot:02d}:{s_tot:02d}. Sugira 3 cortes virais até esse limite. "
                             f"Formato: [MM:SS - MM:SS] + Título. Texto: {trans}")
                    res = client.chat.completions.create(messages=[{"role":"user","content":prompt}], model="llama-3.1-8b-instant")
                    st.session_state['analise_ia'] = res.choices[0].message.content
                except Exception as e:
                    st.error(f"Erro na IA: {e}")

        if 'analise_ia' in st.session_state:
            st.info(st.session_state['analise_ia'])

    with col2:
        st.subheader("2. Configurar o Corte")
        t_in_raw = st.text_input("Início (ex: 1:30)", value="0:00")
        t_out_raw = st.text_input("Fim (ex: 2:00)", value="0:30")
        titulo_manual = st.text_input("Título no Vídeo (Tema Forte):", placeholder="O SEGREDO DA RETENÇÃO")

        if st.button("💡 Sugerir Tema com IA"):
            if 'transcricao' in st.session_state:
                with st.spinner("Criando hook..."):
                    p_tema = f"Crie um título curto e forte para o trecho {t_in_raw} a {t_out_raw}: {st.session_state['transcricao']}"
                    res_t = client.chat.completions.create(messages=[{"role":"user","content":p_tema}], model="llama-3.1-8b-instant")
                    st.success(f"Sugestão: {res_t.choices[0].message.content}")
            else:
                st.error("Analise o vídeo primeiro.")

        estilo = st.radio("Formato:", ["Fundo Personalizado + Tema", "Foco Único", "Split Screen"])

        if st.button("🚀 Renderizar Vídeo Final"):
            s_sec = converter_tempo(t_in_raw)
            e_sec = converter_tempo(t_out_raw)

            if s_sec is not None and e_sec is not None and s_sec < e_sec:
                if e_sec > duracao_real: e_sec = duracao_real
                
                with st.spinner("Gerando vídeo..."):
                    try:
                        with VideoFileClip(temp_path) as video:
                            clip = video.subclip(s_sec, e_sec)
                            
                            if estilo == "Fundo Personalizado + Tema":
                                if not bg_image:
                                    st.error("Suba o fundo!"); st.stop()
                                
                                with open("bg.png", "wb") as f: f.write(bg_image.getbuffer())
                                bg = ImageClip("bg.png").set_duration(clip.duration).resize(height=1920)
                                bg = bg.crop(x_center=bg.w/2, y_center=bg.h/2, width=1080, height=1920)
                                
                                vid_meio = clip.resize(width=1000)
                                path_txt = criar_imagem_texto(titulo_manual.upper() if titulo_manual else "CORTE VIRAL")
                                txt_clip = ImageClip(path_txt).set_duration(clip.duration).set_position(('center', 400))
                                tarja = ColorClip(size=(1080, 180), color=(0,0,0)).set_opacity(0.5).set_duration(clip.duration).set_position(('center', 460))
                                
                                final = CompositeVideoClip([bg, tarja, txt_clip, vid_meio.set_position("center")])
                            
                            elif estilo == "Foco Único":
                                final = clip.crop(x_center=clip.w/2, width=int(clip.h*(9/16)), height=clip.h)
                            else:
                                esq = clip.crop(x1=0, x2=clip.w/2).resize(width=480)
                                dire = clip.crop(x1=clip.w/2, x2=clip.w).resize(width=480)
                                final = clips_array([[esq], [dire]]).resize(height=1080)

                            output = "resultado.mp4"
                            final.write_videofile(output, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast")
                            st.video(output)
                            with open(output, "rb") as f:
                                st.download_button("⬇️ Baixar", f, "corte.mp4")
                        gc.collect()
                    except Exception as err:
                        st.error(f"Erro: {err}")
