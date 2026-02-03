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

# ================= 2. 注入 CSS (优化渲染性能) =================
st.markdown("""
    <style>
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 1rem !important;
        }
        /* 这里的设置让点击复选框更灵敏 */
        .stCheckbox {
            margin-top: 5px;
        }
        div[data-testid="column"] button {
            width: 100%;
        }
        /* 图片容器优化 */
        .img-container {
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid #f0f0f0;
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

# 每页 12 张
ITEMS_PER_PAGE = 12

# 伪装头
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

# --- 单张图片下载 ---
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
    st.header("📖 使用教程")
    st.markdown("""
    1. **解析**：粘贴链接，点击解析。
    2. **选择**：勾选图片 (无需等待，点完再提交)。
    3. **打包**：点击生成 (🚀多线程)。
    4. **下载**：保存 ZIP 包。
    """)
    st.info("⚡ **极速响应模式**\n已优化勾选延迟，操作更跟手！")
    st.markdown("---")
    st.caption("Made with ❤️ TJH")

# ================= 5. 主界面 =================
col1, col2 = st.columns([1.2, 2], gap="medium")

with col1:
    if os.path.exists("heart_collage.png"):
        st.image("heart_collage.png", use_column_width=True)
    elif os.path.exists("heart_collage.jpg"):
        st.image("heart_collage.jpg", use_column_width=True)
    else:
        st.info("请上传名为 heart_collage.png 的图片")

with col2:
    st.markdown("## ⚡ 公众号图片提取")
    st.caption("极速勾选 + 多线程下载")
    st.markdown("---")
    
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
                        # 默认全选所有图片
                        for i in range(len(found_imgs)):
                            st.session_state[f"img_chk_{i}"] = True
                        st.rerun()
                except Exception as e:
                    st.error(f"解析失败: {e}")

# ================= 6. 局部刷新区域 (核心优化) =================

@st.fragment
def show_gallery_area():
    if st.session_state.step >= 2 and st.session_state.scraped_images:
        st.divider()
        
        total_items = len(st.session_state.scraped_images)
        total_pages = math.ceil(total_items / ITEMS_PER_PAGE)
        current_p = st.session_state.current_page
        
        start_idx = (current_p - 1) * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        current_batch = st.session_state.scraped_images[start_idx:end_idx]
        
        st.subheader(f"📸 共 {total_items} 张 (第 {current_p}/{total_pages} 页)")
        
        # --- 顶部按钮栏 (用按钮代替全选框，速度更快) ---
        c1, c2, c3, c4, c5 = st.columns([1, 1, 0.2, 1, 1])
        
        # 批量操作只针对“当前页”，这样计算量极小，反应极快
        if c1.button("✅ 全选本页", use_container_width=True):
            for i in range(len(current_batch)):
                st.session_state[f"img_chk_{start_idx + i}"] = True
            st.rerun()
            
        if c2.button("⬜ 清空本页", use_container_width=True):
            for i in range(len(current_batch)):
                st.session_state[f"img_chk_{start_idx + i}"] = False
            st.rerun()
            
        # 翻页控制
        c4.button("⬅️ 上一页", on_click=prev_page, disabled=(current_p == 1), use_container_width=True)
        c5.button("下一页 ➡️", on_click=next_page, disabled=(current_p == total_pages), use_container_width=True)

        # --- 图片网格 (放在 Form 里是 0 延迟的关键) ---
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
                    # 这里的勾选框在 Form 里，点击是瞬间反应的，不会触发刷新
                    st.checkbox(f"图片 {global_index+1}", key=f"img_chk_{global_index}")
            
            st.markdown("---")
            # 只有点了这个按钮，才会发请求给服务器，所以前面随便勾选都不卡
            submitted = st.form_submit_button("🚀 生成压缩包 (提取勾选图片)", type="primary", use_container_width=True)

            if submitted:
                selected_final_indices = []
                for i in range(total_items):
                    if st.session_state.get(f"img_chk_{i}", False):
                        selected_final_indices.append(i)
                
                if not selected_final_indices:
                    st.warning("⚠️ 请至少选择一张图片！")
                else:
                    # --- 多线程下载 ---
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
