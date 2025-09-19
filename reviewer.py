import streamlit as st
import openai
import requests
import os
import io # BARU: Diperlukan untuk menangani byte file dalam memori
import PyPDF2 # BARU: Pustaka untuk membaca file PDF

# --- Konfigurasi ---
# Atur kunci API OpenAI Anda di sini atau sebagai variabel lingkungan
# os.environ["OPENAI_API_KEY"] = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
openai.api_key = os.getenv("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")

# URL webhook n8n Anda
N8N_WEBHOOK_URL = "https://anahdraw.app.n8n.cloud/webhook-test/3daa2655-3333-4c34-87a4-7eb5e653af9d"

# --- Fungsi Bantuan ---

# BARU: Fungsi untuk mengekstrak teks dari file PDF
def extract_text_from_pdf(file_bytes):
    """
    Mengekstrak teks dari byte file PDF yang diunggah.
    """
    try:
        pdf_file = io.BytesIO(file_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
        return text
    except Exception as e:
        st.error(f"Gagal mengekstrak teks dari PDF: {e}")
        return None

def review_contract(contract_text):
    """
    Mengirim teks kontrak ke OpenAI API untuk ditinjau.
    """
    if not contract_text or not contract_text.strip():
        st.warning("Tidak ada teks yang dapat dianalisis dari file yang diunggah.")
        return None
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Anda adalah asisten hukum ahli yang berspesialisasi dalam peninjauan kontrak. Tinjau dokumen berikut secara komprehensif, identifikasi potensi risiko, klausul yang tidak jelas, dan area yang mungkin memerlukan negosiasi lebih lanjut. Berikan ringkasan, poin-poin penting, dan saran dalam format yang jelas dan mudah dibaca."},
                {"role": "user", "content": contract_text}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Terjadi kesalahan saat berkomunikasi dengan OpenAI: {e}")
        return None

def send_to_n8n(decision, contract_name, review_summary):
    """
    Mengirim keputusan dan data relevan ke webhook n8n.
    """
    try:
        payload = {
            "decision": decision,
            "contract_name": contract_name,
            "review_summary": review_summary
        }
        response = requests.post(N8N_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Gagal mengirim data ke n8n: {e}")
        return False

# --- Antarmuka Pengguna Streamlit ---

st.set_page_config(page_title="Tinjauan Kontrak AI", layout="wide")

st.title("📄 Tinjauan Dokumen Kontrak Komprehensif dengan AI")
st.markdown("Unggah dokumen kontrak Anda (.pdf, .txt, .md) untuk mendapatkan analisis mendalam dari OpenAI.")

# Inisialisasi status sesi
if 'review_result' not in st.session_state:
    st.session_state.review_result = None
if 'file_name' not in st.session_state:
    st.session_state.file_name = None
if 'processing' not in st.session_state:
    st.session_state.processing = False

# MODIFIKASI: Menambahkan 'pdf' ke tipe file yang diterima
uploaded_file = st.file_uploader("Pilih file dokumen (.pdf, .txt, .md)", type=['pdf', 'txt', 'md'])

if uploaded_file is not None:
    if st.button("Tinjau Dokumen", disabled=st.session_state.processing):
        with st.spinner("Membaca dan menganalisis kontrak... Harap tunggu sebentar."):
            st.session_state.processing = True
            contract_text = None
            try:
                # MODIFIKASI: Logika untuk menangani tipe file yang berbeda
                file_extension = os.path.splitext(uploaded_file.name)[1].lower()
                contract_bytes = uploaded_file.read()

                if file_extension == ".pdf":
                    contract_text = extract_text_from_pdf(contract_bytes)
                elif file_extension in [".txt", ".md"]:
                    contract_text = contract_bytes.decode("utf-8")
                else:
                    st.error("Format file tidak didukung.")

                # Hanya melanjutkan jika teks berhasil diekstrak
                if contract_text:
                    st.session_state.file_name = uploaded_file.name
                    st.session_state.review_result = review_contract(contract_text)
                else:
                    st.session_state.review_result = None # Reset jika ekstraksi gagal

            except Exception as e:
                st.error(f"Gagal memproses file: {e}")
                st.session_state.review_result = None
            finally:
                st.session_state.processing = False

# Menampilkan hasil tinjauan
if st.session_state.review_result:
    st.subheader("Hasil Tinjauan AI")
    st.markdown(st.session_state.review_result)

    st.subheader("Tindakan")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Setujui Dokumen", type="primary"):
            with st.spinner("Mengirim persetujuan..."):
                success = send_to_n8n("disetujui", st.session_state.file_name, st.session_state.review_result)
                if success:
                    st.success(f"Dokumen '{st.session_state.file_name}' telah disetujui dan notifikasi telah dikirim.")
                    st.session_state.review_result = None
                    st.session_state.file_name = None

    with col2:
        if st.button("❌ Tolak Dokumen"):
            with st.spinner("Mengirim penolakan..."):
                success = send_to_n8n("ditolak", st.session_state.file_name, st.session_state.review_result)
                if success:
                    st.success(f"Dokumen '{st.session_state.file_name}' telah ditolak dan notifikasi telah dikirim.")
                    st.session_state.review_result = None
                    st.session_state.file_name = None

st.sidebar.header("Cara Kerja")
st.sidebar.info(
    "1. **Unggah Dokumen:** Pilih file kontrak dalam format PDF, teks, atau markdown.\n" # MODIFIKASI
    "2. **Tinjau dengan AI:** Klik tombol 'Tinjau Dokumen' untuk mengirim konten ke OpenAI untuk dianalisis.\n"
    "3. **Lihat Hasil:** Hasil analisis, termasuk potensi risiko dan saran, akan ditampilkan.\n"
    "4. **Ambil Tindakan:** Pilih 'Setujui' atau 'Tolak'. Keputusan Anda akan dikirim ke sistem alur kerja (n8n) untuk tindakan lebih lanjut."
)
st.sidebar.warning("Pastikan kunci API OpenAI dan URL webhook n8n Anda telah dikonfigurasi dengan benar dalam kode.")
