import streamlit as st
import requests
import os

# Fungsi untuk memanggil Langflow API
def run_research_agent(api_url, api_key, research_topic):
    """
    Fungsi ini mengirimkan permintaan ke Langflow API untuk menjalankan agen riset.
    """
    # Pastikan URL diakhiri dengan /run
    if not api_url.endswith('/run'):
        api_url += '/run'

    payload = {
        "input_value": research_topic,
        "output_type": "chat",
        "input_type": "chat",
        "tweaks": {
            # Anda dapat menambahkan penyesuaian (tweaks) di sini jika alur kerja Anda membutuhkannya
        }
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()  # Akan memunculkan kesalahan untuk status kode 4xx/5xx
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Terjadi kesalahan saat menghubungi Langflow API: {e}")
        return None

# Konfigurasi halaman Streamlit
st.set_page_config(page_title="Agen Riset Langflow", layout="wide")

st.title("Agen Riset dengan Langflow & Streamlit")
st.write("Aplikasi ini memungkinkan Anda untuk melakukan riset menggunakan agen yang dibuat di Langflow.")

# Sidebar untuk input pengguna
with st.sidebar:
    st.header("Konfigurasi")
    langflow_api_url = st.text_input("URL API Langflow", placeholder="Masukkan URL API Langflow Anda")
    langflow_api_key = st.text_input("Kunci API Langflow", type="password", placeholder="Masukkan Kunci API Langflow Anda")
    openai_api_key = st.text_input("Kunci API OpenAI", type="password", placeholder="Masukkan Kunci API OpenAI Anda")

    st.info("Pastikan untuk memasukkan URL API dan kunci yang valid dari Langflow dan OpenAI.")

# Area utama untuk input dan output
research_topic = st.text_input("Masukkan Topik Riset", placeholder="Contoh: Perkembangan terbaru dalam kecerdasan buatan")

# Tombol untuk memulai riset
start_research = st.button("Mulai Riset")

# Tombol untuk mereset
if 'research_result' in st.session_state:
    if st.button("Riset Ulang"):
        del st.session_state.research_result
        st.rerun()

# Logika untuk menjalankan riset dan menampilkan hasil
if start_research:
    if not langflow_api_url or not langflow_api_key or not openai_api_key:
        st.warning("Harap masukkan URL API Langflow, Kunci API Langflow, dan Kunci API OpenAI di sidebar.")
    elif not research_topic:
        st.warning("Harap masukkan topik riset.")
    else:
        # Menetapkan kunci API OpenAI sebagai variabel lingkungan sementara untuk sesi ini
        os.environ["OPENAI_API_KEY"] = openai_api_key

        with st.spinner("Agen sedang melakukan riset..."):
            result = run_research_agent(langflow_api_url, langflow_api_key, research_topic)

            if result:
                st.session_state.research_result = result

# Menampilkan hasil jika ada di session state
if 'research_result' in st.session_state:
    st.subheader("Hasil Riset")
    result_data = st.session_state.research_result

    # Struktur output dapat bervariasi tergantung pada bagaimana Anda membangun alur kerja Langflow Anda.
    # Sesuaikan path berikut sesuai dengan struktur JSON output dari Langflow Anda.
    try:
        # Contoh path umum untuk mendapatkan output teks
        output_text = result_data['outputs'][0]['outputs'][0]['results']['message']['text']
        st.markdown(output_text)
    except (KeyError, IndexError, TypeError) as e:
        st.error(f"Tidak dapat mengekstrak hasil dari respons API. Pastikan struktur alur kerja Anda sesuai. Error: {e}")
        st.json(result_data) # Tampilkan seluruh JSON respons untuk debugging
