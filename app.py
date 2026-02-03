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
    page_title="情头提取神器", 
    page_icon="👩‍❤️‍👨",
    layout="centered"
)

# ================= 2. 注入 CSS (保持之前的完美排版) =================
st.markdown("""
    <style>
        /* 顶部防遮挡 */
        .block-container {
            padding-top: 3rem !important;
            padding-bottom: 1rem !important;
        }
        
        .stCheckbox { margin-top: 5px; }
        
        /* 图片容器美化 */
        .img-container {
            border-radius: 12px; /* 圆角更大一点，更圆润 */
            overflow: hidden;
            box-shadow: 0 4px 10px rgba(255, 182, 193, 0.2); /* 淡淡的粉色阴影 */
            transition: transform 0.2s;
            border: 1px solid #ffe4e1; /* 浅粉色边框 */
        }
        .img-container:hover {
            transform: scale(1.03);
            box-shadow: 0 8px 20px rgba(255, 105, 180, 0.3);
        }
        
        /* 标题样式 */
        .custom-title {
            font-size: 24px !important;
            font-weight: 700 !important;
            margin-bottom: 8px !important;
            color: #333;
            line-height: 1.3;
        }
        .custom-subtitle {
            font-size: 15px !important;
            color: #ff6b81; /* 副标题改成温柔的粉红色 */
            margin-top: 0 !important;
            line-height: 1.4;
            font-weight: 500;
        }
        
        /* 统计条样式 */
        .stats-bar {
            background-color: #fff0f5; /* 薰衣草 blush 背景 */
            padding: 10px 15px;
            border-radius: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            border: 1px solid #ffb6c1;
        }
        .stats-text-main { font-weight: bold; color: #d63384; font-size: 16px; }
        .stats-text-sub { color: #888; font-size: 14px; }
    </style>
""", unsafe_allow_html=True)

# ================= 3. 初始化状态 =================
if 'step' not in st.session_state: st.session_state.step = 1 
if 'scraped_images' not in st.session_state: st.session_state.scraped_images = []
if 'zip_buffer' not in st.session_state: st.session_state.zip_buffer = None
if 'current_page' not in st.session_state: st.session_state.current_page = 1

ITEMS_PER_PAGE = 12

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def prev_page():
    if st.session_state.current_page > 1: st.session_state.current_page -= 1

def next_page():
    total_imgs = len(st.session_state.scraped_images)
    total_pages = math.ceil(total_imgs / ITEMS_PER_PAGE)
    if st.session_state.current_page < total_pages: st.session_state.current_page += 1

def download_one_image(img_info):
    index, url = img_info
    url = url.replace("/640?from=appmsg", "/640?from=appmsg&tp=jpg")
    url = url.replace("&tp=webp", "&tp=jpg")
    url = url.replace("wx_fmt=webp", "wx_fmt=jpg")
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200: return index, r.content
    except: pass
    return index, None

# ================= 4. 侧边栏 (Emoji 装修版) =================
with st.sidebar:
    st.markdown("### 💌 找图小助手")
    
    with st.container(border=True):
        st.markdown("""
        **1️⃣ 复制链接** 🔗  
        <span style='color:grey; font-size:0.9em'>在公众号文章右上角点 <b>...</b> 复制</span>
        
        **2️⃣ 粘贴解析** 🔎  
        <span style='color:grey; font-size:0.9em'>粘贴到右侧框框，点击解析</span>
        
        **3️⃣ 挑选最爱** 💑  
        <span style='color:grey; font-size:0.9em'>勾选喜欢的头像 (支持全选)</span>
        
        **4️⃣ 打包带走** 🎁  
        <span style='color:grey; font-size:0.9em'>一键生成压缩包，高清保存</span>
        """, unsafe_allow_html=True)
    
    st.success("💖 **甜蜜提示**\n原图直出不压缩，画质超清晰！")
    st.markdown("---")
    st.caption("Made with ❤️ for Couples")

# ================= 5. 主界面 =================
col1, col2 = st.columns([1.3, 2], gap="large")

with col1:
    if os.path.exists("heart_collage.png"):
        st.image("heart_collage.png", use_column_width=True)
    elif os.path.exists("heart_collage.jpg"):
        st.image("heart_collage.jpg", use_column_width=True)
    else:
        st.info("请上传名为 heart_collage.png 的图片")

with col2:
    # --- 标题文案修改 ---
    st.markdown("""
        <div style="margin-bottom: 20px;">
            <div class="custom-title">👩‍❤️‍👨 微信公众号·情头提取神器</div>
            <div class="custom-subtitle">💖 一键解锁甜蜜情头 · 高清原图不压缩</div>
        </div>
    """, unsafe_allow_html=True)
    
    url = st.text_input("👇 在此粘贴链接:", placeholder="https://mp.weixin.qq.com/s/...", label_visibility="collapsed")
    
    if st.button("🔍 第一步：解析美图", type="primary", use_container_width=True):
        if not url:
            st.warning("⚠️ 还没粘贴链接哦！")
        elif "mp.weixin.qq.com" not in url:
            st.error("❌ 这好像不是微信公众号的链接~")
        else:
            with st.spinner('正在收集甜蜜碎片...'):
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
                        if src and len(src) > 10: found_imgs.append(src)
                    
                    if not found_imgs:
                        st.error("😭 哎呀，没找到图片，可能文章被删啦。")
                    else:
                        st.session_state.scraped_images = found_imgs
                        st.session_state.step = 2 
                        st.session_state.zip_buffer = None
                        st.session_state.current_page = 1
                        for i in range(len(found_imgs)):
                            st.session_state[f"img_chk_{i}"] = True
                        st.rerun()
                except Exception as e:
                    st.error(f"出错啦: {e}")

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
        
        # --- 统计条 (粉色系) ---
        st.markdown(
            f"""
            <div class="stats-bar">
                <div class="stats-text-main">💕 找到 {total_items} 张美图</div>
                <div class="stats-text-sub">第 {current_p} / {total_pages} 页</div>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
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
            submitted = st.form_submit_button("🎁 生成压缩包 (提取选中图片)", type="primary", use_container_width=True)

            if submitted:
                selected_final_indices = []
                for i in range(total_items):
                    if st.session_state.get(f"img_chk_{i}", False):
                        selected_final_indices.append(i)
                
                if not selected_final_indices:
                    st.warning("⚠️ 一张都没选哦，挑几个喜欢的吧！")
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
                            if content: results[idx] = content
                            finished_count += 1
                            progress_bar.progress(finished_count / total)
                            status_text.text(f"🚀 正在极速打包: {finished_count}/{total} ...")

                    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zf:
                        for i, content in enumerate(results):
                            if content: zf.writestr(f"image_{i+1}.jpg", content)
                    
                    st.session_state.zip_buffer = zip_buffer
                    st.session_state.step = 3
                    st.rerun()

show_gallery_area()

# ================= 7. 下载按钮 =================
if st.session_state.step == 3 and st.session_state.zip_buffer:
    st.balloons()
    st.success("✨ 打包完成啦！快去使用吧！")
    
    st.download_button(
        label="📦 点击下载图片包 (ZIP)",
        data=st.session_state.zip_buffer.getvalue(),
        file_name="love_images.zip",
        mime="application/zip",
        type="primary",
        use_container_width=True
    )
    
    if st.button("🔄 再找一篇"):
        st.session_state.step = 1
        st.session_state.scraped_images = []
        st.session_state.zip_buffer = None
        st.session_state.current_page = 1
        keys_to_remove = [k for k in st.session_state.keys() if k.startswith("img_chk_")]
        for k in keys_to_remove: del st.session_state[k]
        st.rerun()
