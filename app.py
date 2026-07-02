import streamlit as st
import requests
from bs4 import BeautifulSoup
from PIL import Image
import io
import time
from urllib.parse import urljoin
import re

st.set_page_config(page_title="Tải tài liệu từ Tập huấn", page_icon="📚", layout="wide")

st.title("📚 Tải tài liệu từ Tập huấn")
st.markdown("Nhập URL trang sách để tải tất cả trang và gộp thành file PDF")

# Initialize session state
if 'images' not in st.session_state:
    st.session_state.images = []
if 'pdf_bytes' not in st.session_state:
    st.session_state.pdf_bytes = None
if 'error' not in st.session_state:
    st.session_state.error = None
if 'book_title' not in st.session_state:
    st.session_state.book_title = 'tai_lieu_taphuan'

def extract_title(html_content):
    """Extract book title from the page"""
    soup = BeautifulSoup(html_content, 'html.parser')
    # Find the title span element
    title_elem = soup.find('span', class_='tw-hidden md:tw-block tw-text-20 tw-font-semibold tw-text-content-primary tw-truncate tw-w-3/4')
    if title_elem:
        title = title_elem.get_text(strip=True)
        # Sanitize title for filename
        title = re.sub(r'[^\w\s-]', '', title)
        return title.strip() or 'tai_lieu_taphuan'
    return 'tai_lieu_taphuan'

def extract_image_urls(html_content, base_url):
    """Extract image URLs from the specific HTML structure - only real pages"""
    soup = BeautifulSoup(html_content, 'html.parser')
    reader_div = soup.find('div', id='reader')
    
    if not reader_div:
        return []
    
    image_urls = []
    
    # Pattern to match page image URLs: ...-page-N-...
    page_pattern = re.compile(r'-page-\d+-')
    
    # Find all page-content divs
    page_contents = reader_div.find_all('div', class_='page-content')
    
    for page in page_contents:
        img = page.find('img')
        if img:
            # Try data-src first (lazy load), then src
            src = img.get('data-src') or img.get('src')
            if src:
                # Clean up the URL (remove backticks if present)
                src = src.strip('`').strip()
                
                # Skip blank pages only
                if 'blank_book_page' in src.lower():
                    continue
                
                # Only include images that match the page pattern
                if page_pattern.search(src):
                    full_url = urljoin(base_url, src)
                    image_urls.append(full_url)
    
    return image_urls

def download_images(image_urls, progress_bar, status_text):
    """Download all images with progress tracking"""
    images = []
    total = len(image_urls)
    
    for i, url in enumerate(image_urls):
        try:
            status_text.text(f"Đang tải trang {i+1}/{total}...")
            response = requests.get(url, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            
            img = Image.open(io.BytesIO(response.content))
            # Convert to RGB if needed (for PDF compatibility)
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            images.append(img)
            
            progress_bar.progress((i + 1) / total)
            
        except Exception as e:
            st.warning(f"Không thể tải trang {i+1}: {str(e)}")
            continue
    
    return images

def images_to_pdf(images):
    """Convert list of PIL images to PDF bytes"""
    if not images:
        return None
    
    pdf_buffer = io.BytesIO()
    # Save first image as PDF, append others
    images[0].save(
        pdf_buffer,
        format='PDF',
        save_all=True,
        append_images=images[1:] if len(images) > 1 else []
    )
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()

# Input form
with st.form("url_form"):
    url_input = st.text_input(
        "URL trang sách",
        placeholder="https://olm.vn/training/... hoặc https://cdn3.olm.vn/...",
        help="Nhập URL trang chứa sách (ví dụ: https://olm.vn/training/detail/12345)"
    )
    submitted = st.form_submit_button("🔍 Lấy sách", type="primary", use_container_width=True)

if submitted and url_input:
    st.session_state.error = None
    st.session_state.images = []
    st.session_state.pdf_bytes = None
    
    try:
        with st.spinner("Đang tải trang web..."):
            response = requests.get(url_input, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
        
        # Extract base URL for relative paths
        from urllib.parse import urlparse
        parsed = urlparse(url_input)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # Extract book title
        st.session_state.book_title = extract_title(response.text)
        
        # Extract image URLs
        image_urls = extract_image_urls(response.text, base_url)
        
        if not image_urls:
            st.session_state.error = "Không tìm thấy ảnh nào trong cấu trúc trang này. Vui lòng kiểm tra URL."
        else:
            st.success(f"✅ Tìm thấy {len(image_urls)} trang ảnh")
            
            # Show preview of first few URLs
            with st.expander("Xem danh sách URL ảnh"):
                for i, url in enumerate(image_urls[:10]):
                    st.code(f"{i+1}. {url}")
                if len(image_urls) > 10:
                    st.info(f"... và {len(image_urls) - 10} trang khác")
            
            # Download images with progress
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            images = download_images(image_urls, progress_bar, status_text)
            
            if images:
                st.session_state.images = images
                status_text.text("Đang tạo file PDF...")
                
                pdf_bytes = images_to_pdf(images)
                st.session_state.pdf_bytes = pdf_bytes
                
                progress_bar.progress(1.0)
                status_text.text("✅ Hoàn tất!")
                st.success(f"Đã tạo PDF từ {len(images)} trang")
            else:
                st.session_state.error = "Không tải được ảnh nào."
                
    except requests.RequestException as e:
        st.session_state.error = f"Lỗi kết nối: {str(e)}"
    except Exception as e:
        st.session_state.error = f"Lỗi: {str(e)}"

# Display error if any
if st.session_state.error:
    st.error(st.session_state.error)

# Download button
if st.session_state.pdf_bytes:
    st.divider()
    st.subheader("📥 Tải về")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info(f"Sẵn sàng tải: {len(st.session_state.images)} trang | Kích thước: {len(st.session_state.pdf_bytes) / 1024 / 1024:.2f} MB")
    with col2:
        st.download_button(
            label="📄 Tải file PDF",
            data=st.session_state.pdf_bytes,
            file_name=f"{st.session_state.book_title}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )

# Footer
st.divider()
st.caption("Công cụ tải tài liệu từ OLm.vn | Hỗ trợ cấu trúc div#reader > .page-content > img")