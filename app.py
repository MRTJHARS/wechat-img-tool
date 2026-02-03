import streamlit as st
import requests
from bs4 import BeautifulSoup
import zipfile
import io
import time
import os
import math
import concurrent.futures # 引入多线程库，这是速度起飞的关键

# ================= 1. 页面配置 =================
st.set_page_config(
    page_title="微信文章图片提取器", 
    page_icon="⚡", # 换个闪电图标，代表快
    layout="centered"
)

# ================= 2. 注入 CSS =================
st.markdown("""
    <style>
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 1rem !important;
        }
        .stCheckbox {
            margin-top: 5px;
        }
        /* 分页按钮样式 */
        div[data-testid="column"] button {
            width: 100%;
        }
    </style>
""", unsafe_allow_html=True)

# ================= 3. 初始化 Session State =================
if 'step' not in st.session_state:
    st.session_state.step = 1 
if 'scraped_images' not in st.session_state:
    st.session_state.scraped_images = []
if 'zip_buffer' not in st.session_state:
    st.session_state.zip_buffer = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1

# 每页显示 12 张（保持你喜欢的布局）
ITEMS_PER_PAGE = 12

# --- 全选/全不选回调 ---
def toggle_all():
    is_all_selected = st.session_state.select_all_key
    # 这里的循环速度很快，几乎不耗时
    if 'scraped_images' in st.session_state:
        for i in range(len(st.session_state.scraped_images)):
            key_name = f"img_chk_{i}"
            st.session_state[key_name] = is_all_selected

# --- 翻页回调 ---
def prev_page():
    if st.session_state.current_page > 1:
        st.session_state.current_page -= 1

def next_page():
    total_imgs = len(st.session_state.scraped_images)
    total_pages = math.ceil(total_imgs / ITEMS_PER_PAGE)
    if st.session_state.current_page < total_pages:
        st.session_state.current_page += 1

# --- 核心：单张图片下载函数 (用于多线程) ---
def download_one_image(img_info):
    index, url, headers = img_info
    
    # 格式处理
    url = url.replace("/640?from=appmsg", "/640?from=appmsg&tp=jpg")
    url = url.replace("&tp=webp", "&tp=jpg")
    url = url.replace("wx_fmt=webp", "wx_fmt=jpg")
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
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
    2. **选择**：勾选图片 (支持全选)。
    3. **打包**：点击生成 (🚀多线程极速版)。
    4. **下载**：保存 ZIP 包。
    """)
    st.info("⚡ **极速模式已开启**\n采用多线程并发下载，速度提升 500%！")
    st.markdown("---")
    st.caption("Made with ❤️ TJH")

# ================= 5. 主界面布局 =================
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
    st.caption("分页预览 + 多线程极速下载")
    st.markdown("---")
    
    url = st.text_input("👇 在此粘贴链接:", placeholder="https://mp.weixin.qq.com/s/...", label_visibility="collapsed")
    
    if st.button("🔍 第一步：解析图片", type="primary", use_container_width=True):
        if not url:
            st.warning("⚠️ 请先粘贴链接！")
        elif "mp.weixin.qq.com" not in url:
            st.error("❌ 链接格式不对。")
        else:
            with st.spinner('正在光速分析网页...'):
                try:
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                    resp = requests.get(url, headers=headers, timeout=10)
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    content = soup.find(id="js_content")
                    if not content: content = soup
                    
                    imgs = content.find_all('img')
                    found_imgs = []
                    
                    for img in imgs:
                        src = img.get('data-src')
                        if src and len(src) > 20: 
                            found_imgs.append(src)
                    
                    if not found_imgs:
                        st.error("未找到图片。")
                    else:
                        st.session_state.scraped_images = found_imgs
                        st.session_state.step = 2 
                        st.session_state.zip_buffer = None
                        st.session_state.current_page = 1
                        
                        # 默认全选
                        for i in range(len(found_imgs)):
                            st.session_state[f"img_chk_{i}"] = True
                            
                        st.rerun()
                except Exception as e:
                    st.error(f"解析失败: {e}")

# ================= 6. 选择与下载区域 =================
if st.session_state.step >= 2 and st.session_state.scraped_images:
    st.divider()
    
    total_items = len(st.session_state.scraped_images)
    total_pages = math.ceil(total_items / ITEMS_PER_PAGE)
    current_p = st.session_state.current_page
    
    start_idx = (current_p - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    current_batch = st.session_state.scraped_images[start_idx:end_idx]
    
    st.subheader(f"📸 共 {total_items} 张 (第 {current_p}/{total_pages} 页)")
    
    # --- 分页控制栏 ---
    c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1])
    with c1:
        st.checkbox("全选 (包含所有页)", value=True, key="select_all_key", on_change=toggle_all)
    with c2:
        st.button("⬅️ 上一页", on_click=prev_page, disabled=(current_p == 1), use_container_width=True)
    with c3:
        st.markdown(f"<div style='text-align: center; line-height: 2.5;'>{current_p} / {total_pages}</div>", unsafe_allow_html=True)
    with c4:
        st.button("下一页 ➡️", on_click=next_page, disabled=(current_p == total_pages), use_container_width=True)

    # --- 图片网格 ---
    with st.form("image_selection_form"):
        cols = st.columns(3)
        for i, img_url in enumerate(current_batch):
            global_index = start_idx + i
            col = cols[i % 3] 
            with col:
                preview_url = img_url.replace("tp=webp", "tp=jpg")
                # 加上 loading="lazy" 进一步优化浏览器渲染速度
                st.markdown(
                    f'''<img src="{preview_url}" loading="lazy" style="width:100%; border-radius:8px; margin-bottom:5px; object-fit:cover; aspect-ratio: 1/1;" referrerpolicy="no-referrer">''', 
                    unsafe_allow_html=True
                )
                st.checkbox(f"图片 {global_index+1}", key=f"img_chk_{global_index}")
        
        st.markdown("---")
        submitted = st.form_submit_button("🚀 生成压缩包 (极速版)", type="primary", use_container_width=True)

        # ================= 7. 多线程下载逻辑 (核心加速) =================
        if submitted:
            selected_final_indices = []
            for i in range(total_items):
                if st.session_state.get(f"img_chk_{i}", False):
                    selected_final_indices.append(i)
            
            if not selected_final_indices:
                st.warning("⚠️ 请至少选择一张图片！")
            else:
                # 准备下载任务列表
                tasks = []
                headers = {'User-Agent': 'Mozilla/5.0'}
                valid_urls = [st.session_state.scraped_images[i] for i in selected_final_indices]
                
                # 构造任务数据：(序号, URL, Headers)
                for idx, url in enumerate(valid_urls):
                    tasks.append((idx, url, headers))

                zip_buffer = io.BytesIO()
                total = len(tasks)
                
                # 进度条
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # --- 开始多线程下载 ---
                # max_workers=8 表示同时开启 8 个线程下载
                results = [None] * total
                finished_count = 0
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                    # 提交所有任务
                    future_to_url = {executor.submit(download_one_image, task): task for task in tasks}
                    
                    for future in concurrent.futures.as_completed(future_to_url):
                        idx, content = future.result()
                        if content:
                            results[idx] = content # 按顺序存好
                        
                        finished_count += 1
                        # 更新进度条
                        progress = finished_count / total
                        progress_bar.progress(progress)
                        status_text.text(f"⚡ 正在极速下载: {finished_count}/{total} 张...")

                # --- 写入 ZIP ---
                status_text.text("正在打包...")
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zf:
                    for i, content in enumerate(results):
                        if content:
                            file_name = f"image_{i+1}.jpg"
                            zf.writestr(file_name, content)
                
                status_text.text("✅ 打包完成！")
                st.session_state.zip_buffer = zip_buffer
                st.session_state.step = 3
                st.rerun()

# ================= 8. 下载按钮 =================
if st.session_state.step == 3 and st.session_state.zip_buffer:
    st.balloons()
    st.success("✨ 极速打包完成！")
    
    st.download_button(
        label="📦 点击下载 (ZIP)",
        data=st.session_state.zip_buffer.getvalue(),
        file_name="fast_images.zip",
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
