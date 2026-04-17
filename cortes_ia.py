import streamlit as st
from moviepy.editor import VideoFileClip, clips_array, ImageClip, CompositeVideoClip, ColorClip
from groq import Groq
import os
import gc
from PIL import Image, ImageDraw, ImageFont

# Configuração da página
st.set_page_config(page_title="Estrategista de Cortes Profissional", layout="wide")

# Conexão com a API Groq via Secrets do Streamlit
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    st.error("⚠️ Erro: GROQ_API_KEY não encontrada nos Secrets do Streamlit!")

# Função para converter formato MM:SS ou SS para segundos (float)
def converter_tempo(texto):
    try:
        texto = texto.strip().replace(",", ".")
        if ":" in texto:
            partes = texto.split(":")
            return (int(partes[0]) * 60) + float(partes[1])
        return float(texto)
    except:
        return None

# Função para criar a imagem do título (Tema Forte) usando Pillow
def criar_imagem_texto(texto, largura=1080):
    # Criamos uma imagem transparente
    img = Image.new('RGBA', (largura, 300), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Tenta usar uma fonte padrão, se falhar usa a básica do sistema
    try:
        # Nota: O nome da fonte pode variar no servidor, o ideal é ter o .ttf na pasta do GitHub
        font = ImageFont.truetype("LiberationSans-Bold.ttf", 70)
    except:
        try:
            font = ImageFont.truetype("Arial.ttf", 70)
        except:
            font = ImageFont.load_default()

    # Calcular posição centralizada
    w_txt, h_txt = draw.textbbox((0, 0), texto, font=font)[2:4]
    draw.text(((largura - w_txt) / 2, (300 - h_txt) / 2), texto, font=font, fill="white")
    
    path = "titulo_temp.png"
    img.save(path)
    return path

st.title("🎙️ Estrategista de Cortes Profissional")

# Upload de arquivos
col_up1, col_up2 = st.columns(2)
with col_up1:
    file = st.file_uploader("1. Suba seu vídeo original", type=["mp4", "mov", "avi"])
with col_up2:
    bg_image = st.file_uploader("2. Suba a imagem de fundo (Para modo Personalizado)", type=["jpg", "jpeg", "png"])

if file:
    temp_path = "video_original_temp.mp4"
    with open(temp_path, "wb") as f:
        f.write(file.getbuffer())

    # Obter informações reais do vídeo
    with VideoFileClip(temp_path) as v_info:
        duracao_real = v_info.duration
        m_tot, s_tot = int(duracao_real // 60), int(duracao_real % 60)
        st.warning(f"📏 Duração do vídeo: {m_tot:02d}:{s_tot:02d} (Não ultrapasse este limite)")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. Análise da IA")
        if st.button("Analisar Momentos Virais"):
            with st.spinner("IA extraindo áudio e analisando assuntos..."):
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
                    
                    prompt = (
                        f"O vídeo tem {m_tot:02d}:{s_tot:02d}. Sugira 3 cortes virais. "
                        f"O tempo de FIM nunca pode passar de {m_tot:02d}:{s_tot:02d}. "
                        f"Formato: [Início MM:SS - Fim MM:SS] + Título Sugerido. Texto: {trans}"
                    )
                    
                    res = client.chat.completions.create(
                        messages=[{"role": "user", "content": prompt}],
                        model="llama-3.1-8b-instant"
                    )
                    st.session_state['analise_ia'] = res.choices[0].message.content
                except Exception as e:
                    st.error(f"Erro na análise: {e}")

        if 'analise_ia' in st.session_state:
            st.info(st.session_state['analise_ia'])

    with col2:
        st.subheader("2. Configurar e Gerar")
        t_in_raw = st.text_input("Início do corte (ex: 1:30)", value="0:00")
        t_out_raw = st.text_input("Fim do corte (ex: 2:00)", value="0:30")
        
        # Campo para o Tema Forte que aparecerá no vídeo
        titulo_manual = st.text_input("Título no Vídeo (Tema Forte):", placeholder="Ex: O SEGREDO DA RETENÇÃO")

        if st.button("💡 Gerar Sugestão de Tema"):
            if 'transcricao' in st.session_state:
                with st.spinner("IA criando tema..."):
                    p_tema = f"Crie um título viral curto para o trecho {t_in_raw} a {t_out_raw}: {st.session_state['transcricao']}"
                    res_t = client.chat.completions.create(messages=[{"role":"user","content":p_tema}], model="llama-3.1-8b-instant")
                    st.success(f"Sugestão: {res_t.choices[0].message.content}")
            else:
                st.error("Analise o vídeo primeiro.")

        estilo = st.radio("Formato de Saída:", 
                         ["Fundo Personalizado + Tema Forte", "Foco Único (Centro)", "Split Screen (Podcast)"])

        if st.button("🚀 Renderizar Vídeo Final"):
            start_sec = converter_tempo(t_in_raw)
            end_sec = converter_tempo(t_out_raw)

            if start_sec is not None and end_sec is not None and start_sec < end_sec:
                if end_sec > duracao_real: end_sec = duracao_real
                
                with st.spinner("Processando vídeo e camadas..."):
                    try:
                        with VideoFileClip(temp_path) as video:
                            clip = video.subclip(start_sec, end_sec)
                            w, h = clip.size
                            
                            if estilo == "Fundo Personalizado + Tema Forte":
                                if not bg_image:
                                    st.error("❌ Suba a imagem de fundo para este modo!"); st.stop()
                                
                                # 1. Fundo (9:16)
                                with open("bg.png", "wb") as f: f.write(bg_image.getbuffer())
                                bg = ImageClip("bg.png").set_duration(clip.duration).resize(height=1920)
                                bg = bg.crop(x_center=bg.w/2, y_center=bg.h/2, width=1080, height=1920)
                                
                                # 2. Vídeo (Horizontal no centro)
                                vid_meio = clip.resize(width=1000)
                                
                                # 3. Tema Forte (Texto)
                                path_txt = criar_imagem_texto(titulo_manual.upper() if titulo_manual else "CORTE VIRAL")
                                txt_clip = ImageClip(path_txt).set_duration(clip.duration).set_position(('center', 400))
                                
                                # 4. Tarja para o Texto (melhora a leitura)
                                tarja = ColorClip(size=(1080, 180), color=(0,0,0)).set_opacity(0.5).set_duration(clip.duration).set_position(('center', 460))
                                
                                final = CompositeVideoClip([bg, tarja, txt_clip, vid_meio.set_position("center")])
                            
                            elif estilo == "Foco Único (Centro)":
                                tw = int(h * (9/16))
                                if tw % 2 != 0: tw -= 1
                                final = clip.crop(x_center=w/2, width=tw, height=h)
                                
                            else: # Split Screen
                                esq = clip.crop(x1=0, x2=w/2).resize(width=480)
                                dire = clip.crop(x1=w/2, x2=w).resize(width=480)
                                final = clips_array([[esq], [dire]]).resize(height=1080)

                            # Exportação com Codec compatível para Navegador
                            output_file = "corte_final_premium.mp4"
                            final.write_videofile(output_file, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast")
                            
                            st.video(output_file)
                            with open(output_file, "rb") as f:
                                st.download_button("⬇️ Baixar Corte", f, "meu_corte_viral.mp4")
                        gc.collect()
                    except Exception as e:
                        st.error(f"Erro na renderização: {e}")
