import streamlit as st
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip, ColorClip
from groq import Groq
import os, gc, json, re, random, time
from PIL import Image, ImageDraw, ImageFont

# --- CORREÇÃO DE COMPATIBILIDADE PILLOW ---
import PIL.Image
if not hasattr(PIL.Image, 'Resampling'):
    PIL.Image.LANCZOS = PIL.Image.ANTIALIAS
else:
    PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS
    PIL.Image.LANCZOS = PIL.Image.Resampling.LANCZOS

st.set_page_config(page_title="Estrategista de Cortes", layout="wide")

if 'analisar' not in st.session_state:
    st.session_state['analisar'] = False

# Estilo para botões e cards
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div.stButton > button:first-child {
        background-color: #2e77d0;
        color: white; border-radius: 10px; height: 3em; font-weight: bold;
    }
    .stVideo { border-radius: 12px; border: 1px solid #333; background-color: black; }
    </style>
    """, unsafe_allow_html=True)

try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("⚠️ Configure a GROQ_API_KEY nos Secrets.")

def criar_imagem_texto(texto, largura=1080):
    img = Image.new('RGBA', (largura, 450), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 110)
    except:
        font = ImageFont.load_default()
    
    texto_up = texto.upper()
    w_txt, h_txt = draw.textbbox((0, 0), texto_up, font=font)[2:4]
    draw.text(((largura - w_txt) / 2, (450 - h_txt) / 2), texto_up, font=font, fill="white", align="center")
    path = f"t_{random.randint(0,999)}.png"
    img.save(path)
    return path

def processar_corte(video_path, bg_path, start, end, tema, output_name, dur_max):
    s_v = max(0, float(start))
    e_v = min(float(end), float(dur_max))
    
    with VideoFileClip(video_path) as video:
        clip = video.subclip(s_v, e_v)
        # Força o fundo a ser 1080x1920 exato
        bg = ImageClip(bg_path).set_duration(clip.duration).resize(height=1920)
        bg = bg.crop(x_center=bg.w/2, y_center=bg.h/2, width=1080, height=1920)
        
        vid_centro = clip.resize(width=1000)
        path_txt = criar_imagem_texto(tema)
        txt_clip = ImageClip(path_txt).set_duration(clip.duration).set_position(('center', 220))
        tarja = ColorClip(size=(1080, 420), color=(0,0,0)).set_opacity(0.7).set_duration(clip.duration).set_position(('center', 240))
        
        final = CompositeVideoClip([bg, tarja, txt_clip, vid_centro.set_position("center")])
        # Trava de segurança para dimensões pares (essencial para navegadores)
        final = final.resize(width=1080, height=1920)
        
        # CODEC ULTRA COMPATÍVEL (H.264 para Web)
        final.write_videofile(output_name, 
                              codec="libx264", 
                              audio_codec="aac", 
                              bitrate="2000k", 
                              fps=24, 
                              preset="ultrafast", 
                              ffmpeg_params=["-pix_fmt", "yuv420p"],
                              logger=None)
    
    if os.path.exists(path_txt): os.remove(path_txt)
    return output_name

st.title("🎙️ Estrategista de Cortes Profissional")

with st.sidebar:
    st.header("1. Upload de Arquivos")
    file = st.file_uploader("Vídeo Original", type=["mp4", "mov"])
    bg_img = st.file_uploader("Imagem de Fundo", type=["jpg", "png"])
    if st.button("🚀 GERAR 3 VÍDEOS"):
        if file and bg_img:
            # Limpa lixo de vídeos antigos para liberar espaço no servidor
            for f in os.listdir():
                if f.startswith("corte_final_") and f.endswith(".mp4"): os.remove(f)
            st.session_state['analisar'] = True

if file and bg_img:
    temp_v, temp_bg = "v_temp.mp4", "bg_temp.png"
    with open(temp_v, "wb") as f: f.write(file.getbuffer())
    with open(temp_bg, "wb") as f: f.write(bg_img.getbuffer())

    if st.session_state['analisar']:
        with st.spinner("Editando vídeos com qualidade profissional..."):
            try:
                with VideoFileClip(temp_v) as v:
                    dur_tot = v.duration
                    v.audio.write_audiofile("aud.mp3", codec='libmp3lame', logger=None)
                
                with open("aud.mp3", "rb") as a:
                    trans = client.audio.transcriptions.create(file=("aud.mp3", a.read()), model="whisper-large-v3-turbo", response_format="text")
                
                prompt = f"Vídeo de {dur_tot}s. Escolha 3 cortes virais. Retorne JSON: [{{'inicio': seg, 'fim': seg, 'tema': 'titulo'}}] Texto: {trans}"
                res = client.chat.completions.create(messages=[{"role":"user","content":prompt}], model="llama-3.1-8b-instant")
                
                match = re.search(r'\[.*\]', res.choices[0].message.content, re.DOTALL)
                cortes = json.loads(match.group().replace("'", '"'))

                st.header("2. Seus Cortes Gerados")
                cols = st.columns(3)
                for i, corte in enumerate(cortes[:3]):
                    out_name = f"corte_final_{i}_{int(time.time())}.mp4"
                    processar_corte(temp_v, temp_bg, corte['inicio'], corte['fim'], corte['tema'], out_name, dur_tot)
                    
                    with cols[i]:
                        st.video(out_name)
                        st.write(f"📌 **{corte['tema']}**")
                        with open(out_name, "rb") as f:
                            st.download_button(f"Baixar Vídeo {i+1}", f, file_name=f"corte_{i+1}.mp4")
                
                st.session_state['analisar'] = False
                gc.collect()
            except Exception as e:
                st.error(f"Erro: {e}")
else:
    st.info("💡 Carregue os arquivos na barra lateral para gerar os cortes.")
