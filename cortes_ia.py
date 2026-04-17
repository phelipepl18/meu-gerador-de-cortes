import streamlit as st
from moviepy.editor import VideoFileClip, clips_array, ImageClip, CompositeVideoClip, ColorClip
from groq import Groq
import os
import gc
from PIL import Image, ImageDraw, ImageFont

# --- CORREÇÃO PARA ERRO DE REDIMENSIONAMENTO (ANTIALIAS) ---
import PIL.Image
if not hasattr(PIL.Image, 'Resampling'):
    PIL.Image.LANCZOS = PIL.Image.ANTIALIAS
else:
    PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS
    PIL.Image.LANCZOS = PIL.Image.Resampling.LANCZOS

st.set_page_config(page_title="Estrategista de Cortes Profissional", layout="wide")

# Conexão Groq
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("⚠️ Configure a GROQ_API_KEY nos Secrets do Streamlit!")

def converter_tempo(texto):
    try:
        texto = texto.strip().replace(",", ".")
        if ":" in texto:
            partes = texto.split(":")
            return (int(partes[0]) * 60) + float(partes[1])
        return float(texto)
    except: return None

def criar_imagem_texto(texto, largura=1080):
    img = Image.new('RGBA', (largura, 250), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        # Tenta carregar fonte negritada padrão do servidor Streamlit
        font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 80)
    except:
        font = ImageFont.load_default()
    
    w_txt, h_txt = draw.textbbox((0, 0), texto, font=font)[2:4]
    draw.text(((largura - w_txt) / 2, (250 - h_txt) / 2), texto, font=font, fill="white")
    path = "titulo_temp.png"
    img.save(path)
    return path

st.title("🎙️ Estrategista de Cortes Profissional")

col_up1, col_up2 = st.columns(2)
with col_up1:
    file = st.file_uploader("1. Suba seu vídeo original", type=["mp4", "mov", "avi"])
with col_up2:
    bg_image = st.file_uploader("2. Imagem de fundo (Obrigatório para Layout)", type=["jpg", "jpeg", "png"])

if file:
    temp_path = "video_original_temp.mp4"
    with open(temp_path, "wb") as f: f.write(file.getbuffer())

    with VideoFileClip(temp_path) as v_info:
        duracao_real = v_info.duration
        st.warning(f"📏 Duração do vídeo: {int(duracao_real // 60):02d}:{int(duracao_real % 60):02d}")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. Análise da IA")
        if st.button("Analisar Momentos Virais"):
            with st.spinner("Analisando áudio..."):
                try:
                    with VideoFileClip(temp_path) as video_full:
                        video_full.audio.write_audiofile("audio_temp.mp3", codec='libmp3lame')
                    with open("audio_temp.mp3", "rb") as a:
                        trans = client.audio.transcriptions.create(file=("audio_temp.mp3", a.read()), model="whisper-large-v3-turbo", response_format="text")
                    st.session_state['transcricao'] = trans
                    res = client.chat.completions.create(
                        messages=[{"role":"user","content":f"Sugira 3 cortes virais até {duracao_real}s: {trans}"}],
                        model="llama-3.1-8b-instant"
                    )
                    st.session_state['analise_ia'] = res.choices[0].message.content
                except Exception as e: st.error(f"Erro IA: {e}")
        if 'analise_ia' in st.session_state: st.info(st.session_state['analise_ia'])

    with col2:
        st.subheader("2. Configurar o Corte")
        t_in = st.text_input("Início", value="0:00")
        t_out = st.text_input("Fim", value="0:30")
        titulo_manual = st.text_input("Tema Forte (Texto no vídeo):", placeholder="EX: O SEGREDO DO SUCESSO")

        estilo = st.radio("Formato de Saída:", ["Fundo Personalizado + Tema", "Split Screen + Tema"])

        if st.button("🚀 Renderizar Vídeo Final"):
            s_sec, e_sec = converter_tempo(t_in), converter_tempo(t_out)
            if s_sec is not None and e_sec is not None and s_sec < e_sec:
                with st.spinner("Gerando composição..."):
                    try:
                        with VideoFileClip(temp_path) as video:
                            clip = video.subclip(s_sec, min(e_sec, video.duration))
                            
                            # Preparar elementos comuns (Texto e Tarja)
                            path_txt = criar_imagem_texto(titulo_manual.upper() if titulo_manual else "CORTE VIRAL")
                            txt_clip = ImageClip(path_txt).set_duration(clip.duration).set_position(('center', 380))
                            tarja = ColorClip(size=(1080, 200), color=(0,0,0)).set_opacity(0.6).set_duration(clip.duration).set_position(('center', 410))

                            if "Fundo Personalizado" in estilo:
                                if not bg_image: st.error("Suba o fundo!"); st.stop()
                                with open("bg.png", "wb") as f: f.write(bg_image.getbuffer())
                                bg = ImageClip("bg.png").set_duration(clip.duration).resize(height=1920)
                                bg = bg.crop(x_center=bg.w/2, y_center=bg.h/2, width=1080, height=1920)
                                vid_final = clip.resize(width=1000)
                                final = CompositeVideoClip([bg, tarja, txt_clip, vid_final.set_position("center")])
                            
                            else: # Split Screen + Tema
                                if not bg_image: st.error("Suba o fundo!"); st.stop()
                                with open("bg.png", "wb") as f: f.write(bg_image.getbuffer())
                                bg = ImageClip("bg.png").set_duration(clip.duration).resize(height=1920)
                                bg = bg.crop(x_center=bg.w/2, y_center=bg.h/2, width=1080, height=1920)
                                
                                # Lógica Split Screen (Lado a Lado)
                                w, h = clip.size
                                esq = clip.crop(x1=0, x2=w/2).resize(width=540)
                                dire = clip.crop(x1=w/2, x2=w).resize(width=540)
                                videos_lado = clips_array([[esq, dire]]).resize(width=1080)
                                
                                final = CompositeVideoClip([bg, videos_lado.set_position("center"), tarja, txt_clip])

                            # Trava de dimensões pares para o vídeo aparecer no site
                            if final.w % 2 != 0: final = final.margin(right=1)
                            if final.h % 2 != 0: final = final.margin(bottom=1)

                            output = "corte_final.mp4"
                            final.write_videofile(output, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", threads=4)
                            
                            st.video(output)
                            with open(output, "rb") as f:
                                st.download_button("⬇️ Baixar Corte", f, "corte_viral.mp4")
                        gc.collect()
                    except Exception as err: st.error(f"Erro na renderização: {err}")
