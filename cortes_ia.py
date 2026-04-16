import streamlit as st
from moviepy.editor import VideoFileClip, clips_array, ImageClip, CompositeVideoClip
from groq import Groq
import os
import gc
import PIL.Image

# Correção de compatibilidade para redimensionamento de imagem
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

st.set_page_config(page_title="Gerador de Cortes Podcast", layout="wide")

# Conexão segura com Groq
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("⚠️ Configure a GROQ_API_KEY nos Secrets do Streamlit!")

# Função para converter MM:SS em segundos reais
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

# Uploads de arquivos
file = st.file_uploader("1. Suba seu vídeo original", type=["mp4", "mov", "avi"])
bg_image = st.file_uploader("2. Opcional: Imagem de fundo (Para Fundo Personalizado)", type=["jpg", "jpeg", "png"])

if file:
    temp_path = "video_original_temp.mp4"
    with open(temp_path, "wb") as f:
        f.write(file.getbuffer())

    # Captura a duração real para ancorar a IA e o código
    with VideoFileClip(temp_path) as v_info:
        duracao_real = v_info.duration
        m_tot, s_tot = int(duracao_real // 60), int(duracao_real % 60)
        st.warning(f"📏 Duração Real do Vídeo: {m_tot:02d}:{s_tot:02d} (Não aceite sugestões maiores que isso)")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. Análise Geral da IA")
        if st.button("Analisar Momentos Virais"):
            with st.spinner("Extraindo áudio e analisando..."):
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
                    
                    # PROMPT REFORÇADO: Bloqueia a IA de inventar tempos
                    prompt = (
                        f"O vídeo tem EXATAMENTE {m_tot:02d}:{s_tot:02d}. "
                        f"Sugira 3 cortes. O tempo de FIM NUNCA pode ser maior que {m_tot:02d}:{s_tot:02d}. "
                        f"Responda no formato: [MM:SS - MM:SS] + Resumo. Texto: {trans}"
                    )
                    
                    res = client.chat.completions.create(
                        messages=[{"role": "user", "content": prompt}],
                        model="llama-3.1-8b-instant"
                    )
                    st.session_state['analise_geral'] = res.choices[0].message.content
                except Exception as e:
                    st.error(f"Erro na IA: {e}")

        if 'analise_geral' in st.session_state:
            st.info(st.session_state['analise_geral'])

    with col2:
        st.subheader("2. Configurar o Corte")
        t_in_raw = st.text_input("Início do corte (ex: 1:30)", value="0:00")
        t_out_raw = st.text_input("Fim do corte (ex: 2:00)", value="0:30")
        
        # Sugestão de Tema Forte (Hook Viral)
        if st.button("💡 Sugerir Tema Viral para este tempo"):
            if 'transcricao' in st.session_state:
                with st.spinner("Criando título impactante..."):
                    prompt_tema = (
                        f"Baseado no trecho entre {t_in_raw} e {t_out_raw} da transcrição: {st.session_state['transcricao']}. "
                        f"Crie um título viral curto para usar de capa."
                    )
                    res_tema = client.chat.completions.create(
                        messages=[{"role": "user", "content": prompt_tema}],
                        model="llama-3.1-8b-instant"
                    )
                    st.success(f"🔥 Tema sugerido: **{res_tema.choices[0].message.content}**")
            else:
                st.error("Analise o vídeo primeiro.")

        estilo = st.radio("Formato de Saída:", 
                         ["Foco Único (Centro)", "Split Screen (Podcast)", "Fundo Personalizado (Vídeo no meio)"])

        if st.button("🚀 Gerar Vídeo"):
            start_sec = converter_tempo(t_in_raw)
            end_sec = converter_tempo(t_out_raw)

            # VALIDAÇÃO DE SEGURANÇA
            if start_sec is not None and end_sec is not None:
                if start_sec >= duracao_real:
                    st.error("❌ O início não pode ser depois do fim do vídeo!")
                else:
                    if end_sec > duracao_real:
                        end_sec = duracao_real # Ajuste automático para o limite real
                    
                    with st.spinner("Renderizando vídeo..."):
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
                                    if bg_image:
                                        with open("bg_temp.png", "wb") as f: f.write(bg_image.getbuffer())
                                        bg_clip = ImageClip("bg_temp.png").set_duration(clip.duration).resize(height=1920)
                                        if bg_clip.w < 1080: bg_clip = bg_clip.resize(width=1080)
                                        bg_clip = bg_clip.crop(x_center=bg_clip.w/2, y_center=bg_clip.h/2, width=1080, height=1920)
                                        final = CompositeVideoClip([bg_clip, clip.resize(width=1080).set_position("center")])
                                    else:
                                        st.error("Faça o upload da imagem de fundo."); st.stop()

                                output = "corte_finalizado.mp4"
                                final.write_videofile(output, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast")
                                st.video(output)
                                with open(output, "rb") as f:
                                    st.download_button("⬇️ Baixar", f, "meu_corte.mp4")
                            gc.collect()
                        except Exception as e:
                            st.error(f"Erro no processamento: {e}")
