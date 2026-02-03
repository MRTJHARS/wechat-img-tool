import streamlit as st
import requests
from bs4 import BeautifulSoup
import zipfile
import io
import time
import os
import math
import concurrent.futures

# ================= 1. 页面配置 =================
st.set_page_config(
    page_title="微信文章图片提取器", 
    page_icon="⚡",
    layout="centered"
)

# ================= 2. 注入 CSS (修复显示不全问题) =================
st.markdown("""
    <style>
        /* 1. 修复顶部遮挡：增加顶部内边距 */
        .block-container {
            padding-top: 3rem !important; /* 从 1.5rem 改回 3rem，防止被顶部栏遮挡 */
            padding-bottom: 1rem !important;
        }
        
        /* 2. 复选框优化 */
        .stCheckbox {
            margin-top: 5px;
        }
        
        /* 3. 图片容器 */
        .img-container {
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            transition: transform 0.2s;
        }
        .img-container:hover {
            transform: scale(1.02);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        /* 4. 标题样式修复 (防止切字) */
        .custom-title {
            font-size: 24px !important; /* 稍微调小一点，确保能放下 */
            font-weight: 700 !important;
            margin-bottom: 8px !important;
            color: #0f1116;
            line-height: 1.3; /* 增加行高，防止文字重叠 */
        }
        .custom-subtitle {
            font-size: 15px !important;
            color: #555;
            margin-top: 0 !important;
            line-height: 1.4;
        }
        
        /* 5. 统计条样式 */
        .stats-bar {
            background-color: #f0f2f6;
            padding: 10px 15px;
            border-radius: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            border: 1px solid #e0e0e0;
        }
        .stats-text-main {
            font-weight: bold;
            color: #333;
            font-size: 16px;
        }
        .stats-text-sub {
            color: #666;
            font-size: 14px;
        }
    </style>
""", unsafe_allow_html=True)

# ================= 3. 初始化状态 =================
if 'step' not in st.session_state:
    st.session_state.step = 1 
if 'scraped_images' not in st.session_state:
    st.session_state.scraped_images = []
if 'zip_buffer' not in st.session_state:
    st.session_state.zip_buffer = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1

ITEMS_PER_PAGE = 12

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# --- 翻页函数 ---
def prev_page():
    if st.session_state.current_page > 1:
        st.session_state.current_page -= 1

def next_page():
    total_imgs = len(st.session_state.scraped_images)
    total_pages = math.ceil(total_imgs / ITEMS_PER_PAGE)
    if st.session_state.current_page < total_pages:
        st.session_state.current_page += 1

# --- 下载函数 ---
def download_one_image(img_info):
    index, url = img_info
    url = url.replace("/640?from=appmsg", "/640?from=appmsg&tp=jpg")
    url = url.replace("&tp=webp", "&tp=jpg")
    url = url.replace("wx_fmt=webp", "wx_fmt=jpg")
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return index, r.content
    except:
        pass
    return index, None

# ================= 4. 侧边栏 =================
with st.sidebar:
    st.markdown("### 📚 使用指南")
    
    with st.container(border=True):
        st.markdown("""
        **1. 复制链接** <span style='color:grey; font-size:0.9em'>点击文章右上角 <b>...</b> 复制链接</span>
        
        **2. 粘贴解析** <span style='color:grey; font-size:0.9em'>粘贴到输入框，点击解析</span>
        
        **3. 极速挑选** <span style='color:grey; font-size:0.9em'>勾选喜欢的图片 (支持全选)</span>
        
        **4. 一键打包** <span style='color:grey; font-size:0.9em'>点击生成，高速下载原图</span>
        """, unsafe_allow_html=True)
    
    st.success("⚡ **极速模式已就绪**\n多线程并发下载，速度提升 500%！")
    st.markdown("---")
    st.caption("Made with ❤️ TJH")

# ================= 5. 主界面 =================
col1, col2 = st.columns([1.3, 2], gap="large")

with col1:
    if os.path.exists("heart_collage.png"):
        st.image("heart_collage.png", use_column_width=True)
    elif os.path.exists("heart_collage.jpg"):
        st.image("heart_collage.jpg", use_column_width=True)
    else:
        st.info("请上传 heart_collage.png")

with col2:
    # --- 标题区 (已修复遮挡) ---
    st.markdown("""
        <div style="margin-bottom: 20px;">
            <div class="custom-title">⚡ 微信公众号·极速取图</div>
            <div class="custom-subtitle">🚀 一键保存美好瞬间 · 高清原图不压缩</div>
        </div>
    """, unsafe_allow_html=True)
    
    url = st.text_input("👇 在此粘贴链接:", placeholder="https://mp.weixin.qq.com/s/...", label_visibility="collapsed")
    
    if st.button("🔍 第一步：解析图片", type="primary", use_container_width=True):
        if not url:
            st.warning("⚠️ 请先粘贴链接！")
        elif "mp.weixin.qq.com" not in url:
            st.error("❌ 链接格式不对。")
        else:
            with st.spinner('正在分析网页...'):
                try:
                    resp = requests.get(url, headers=HEADERS, timeout=10)
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    content = soup.find(id="js_content")
                    if not content: content = soup
                    
                    imgs = content.find_all('img')
                    found_imgs = []
                    for img in imgs:
                        src = img.get('data-src')
                        if src and len(src) > 10: 
                            found_imgs.append(src)
                    
                    if not found_imgs:
                        st.error("未找到图片。")
                    else:
                        st.session_state.scraped_images = found_imgs
                        st.session_state.step = 2 
                        st.session_state.zip_buffer = None
                        st.session_state.current_page = 1
                        for i in range(len(found_imgs)):
                            st.session_state[f"img_chk_{i}"] = True
                        st.rerun()
                except Exception as e:
                    st.error(f"解析失败: {e}")

# ================= 6. 局部刷新区域 =================

@st.fragment
def show_gallery_area():
    if st.session_state.step >= 2 and st.session_state.scraped_images:
        st.markdown("---")
        
        total_items = len(st.session_state.scraped_images)
        total_pages = math.ceil(total_items / ITEMS_PER_PAGE)
        current_p = st.session_state.current_page
        
        start_idx = (current_p - 1) * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        current_batch = st.session_state.scraped_images[start_idx:end_idx]
        
        # --- 统计条 ---
        st.markdown(
            f"""
            <div class="stats-bar">
                <div class="stats-text-main">📸 已捕获 {total_items} 张美图</div>
                <div class="stats-text-sub">第 {current_p} / {total_pages} 页</div>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        # --- 按钮栏 ---
        c1, c2, c3, c4, c5 = st.columns([1, 1, 0.2, 1, 1])
        
        if c1.button("✅ 全选本页", use_container_width=True):
            for i in range(len(current_batch)):
                st.session_state[f"img_chk_{start_idx + i}"] = True
            st.rerun()
            
        if c2.button("⬜ 清空本页", use_container_width=True):
            for i in range(len(current_batch)):
                st.session_state[f"img_chk_{start_idx + i}"] = False
            st.rerun()
            
        c4.button("⬅️ 上一页", on_click=prev_page, disabled=(current_p == 1), use_container_width=True)
        c5.button("下一页 ➡️", on_click=next_page, disabled=(current_p == total_pages), use_container_width=True)

        # --- 图片网格 ---
        with st.form("image_selection_form", border=False):
            cols = st.columns(3)
            for i, img_url in enumerate(current_batch):
                global_index = start_idx + i
                col = cols[i % 3] 
                with col:
                    preview_url = img_url.replace("tp=webp", "tp=jpg")
                    st.markdown(
                        f'''<div class="img-container"><img src="{preview_url}" loading="lazy" style="width:100%; display:block; aspect-ratio: 1/1; object-fit: cover;" referrerpolicy="no-referrer"></div>''', 
                        unsafe_allow_html=True
                    )
                    st.checkbox(f"图片 {global_index+1}", key=f"img_chk_{global_index}")
            
            st.markdown("---")
            submitted = st.form_submit_button("🚀 生成压缩包 (提取勾选图片)", type="primary", use_container_width=True)

            if submitted:
                selected_final_indices = []
                for i in range(total_items):
                    if st.session_state.get(f"img_chk_{i}", False):
                        selected_final_indices.append(i)
                
                if not selected_final_indices:
                    st.warning("⚠️ 请至少选择一张图片！")
                else:
                    tasks = []
                    valid_urls = [st.session_state.scraped_images[i] for i in selected_final_indices]
                    for idx, url in enumerate(valid_urls):
                        tasks.append((idx, url))

                    zip_buffer = io.BytesIO()
                    total = len(tasks)
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    results = [None] * total
                    finished_count = 0
                    
                    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                        future_to_url = {executor.submit(download_one_image, task): task for task in tasks}
                        for future in concurrent.futures.as_completed(future_to_url):
                            idx, content = future.result()
                            if content:
                                results[idx] = content
                            finished_count += 1
                            progress_bar.progress(finished_count / total)
                            status_text.text(f"⚡ 正在下载: {finished_count}/{total} 张...")

                    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zf:
                        for i, content in enumerate(results):
                            if content:
                                zf.writestr(f"image_{i+1}.jpg", content)
                    
                    st.session_state.zip_buffer = zip_buffer
                    st.session_state.step = 3
                    st.rerun()

show_gallery_area()

# ================= 7. 下载按钮 =================
if st.session_state.step == 3 and st.session_state.zip_buffer:
    st.balloons()
    st.success("✨ 极速打包完成！")
    
    st.download_button(
        label="📦 点击下载 (ZIP)",
        data=st.session_state.zip_buffer.getvalue(),
        file_name="images.zip",
        mime="application/zip",
        type="primary",
        use_container_width=True
    )
    
    if st.button("🔄 提取另一篇文章"):
        st.session_state.step = 1
        st.session_state.scraped_images = []
        st.session_state.zip_buffer = None
        st.session_state.current_page = 1
        keys_to_remove = [k for k in st.session_state.keys() if k.startswith("img_chk_")]
        for k in keys_to_remove:
            del st.session_state[k]
        st.rerun()
