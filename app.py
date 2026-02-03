import streamlit as st
import requests
from bs4 import BeautifulSoup
import zipfile
import io
import time
import os

# ================= 1. 页面配置 =================
st.set_page_config(
    page_title="微信文章图片提取器", 
    page_icon="🎨",
    layout="centered"
)

# ================= 2. 注入 CSS (美化界面) =================
st.markdown("""
    <style>
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 1rem !important;
        }
        /* 调整多选框的位置 */
        .stCheckbox {
            margin-top: 5px;
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

# --- 全选/全不选的回调函数 ---
def toggle_all():
    is_all_selected = st.session_state.select_all_key
    if 'scraped_images' in st.session_state:
        for i in range(len(st.session_state.scraped_images)):
            key_name = f"img_chk_{i}"
            st.session_state[key_name] = is_all_selected

# ================= 4. 侧边栏配置 =================
with st.sidebar:
    st.header("📖 使用教程")
    st.markdown("""
    1. **解析**：输入链接，点击“解析图片”。
    2. **选择**：勾选你想要的图片。
    3. **打包**：点击“生成压缩包”。
    4. **下载**：点击出现的“下载”按钮保存。
    """)
    st.info("💡 如果图片加载较慢，请稍等片刻。")
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
    st.markdown("## 🎨 公众号图片提取")
    st.caption("解决图片不显示问题，只下你想要的！")
    st.markdown("---")
    
    url = st.text_input("👇 在此粘贴链接:", placeholder="https://mp.weixin.qq.com/s/...", label_visibility="collapsed")
    
    # --- 按钮 1：解析图片 ---
    if st.button("🔍 第一步：解析图片", type="primary", use_container_width=True):
        if not url:
            st.warning("⚠️ 请先粘贴链接！")
        elif "mp.weixin.qq.com" not in url:
            st.error("❌ 链接格式不对，请使用微信公众号文章链接。")
        else:
            with st.spinner('正在分析网页...'):
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                    resp = requests.get(url, headers=headers, timeout=10)
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    content = soup.find(id="js_content")
                    if not content: content = soup
                    
                    imgs = content.find_all('img')
                    found_imgs = []
                    
                    for img in imgs:
                        src = img.get('data-src')
                        # 过滤掉一些太短的无效链接
                        if src and len(src) > 20: 
                            found_imgs.append(src)
                    
                    if not found_imgs:
                        st.error("未找到图片，可能是文章已删除。")
                    else:
                        st.session_state.scraped_images = found_imgs
                        st.session_state.step = 2 
                        st.session_state.zip_buffer = None
                        
                        # 解析成功时，默认全选
                        for i in range(len(found_imgs)):
                            st.session_state[f"img_chk_{i}"] = True
                            
                        st.rerun()

                except Exception as e:
                    st.error(f"解析失败: {e}")

# ================= 6. 选择与下载区域 (步骤 2) =================
if st.session_state.step >= 2 and st.session_state.scraped_images:
    st.divider()
    st.subheader(f"📸 共找到 {len(st.session_state.scraped_images)} 张图片")
    
    # --- 全选/反选控制 ---
    col_sel1, col_sel2 = st.columns([1, 4])
    with col_sel1:
        st.checkbox("全选", value=True, key="select_all_key", on_change=toggle_all)
    with col_sel2:
        st.caption("取消勾选不需要的图片，然后点击底部的生成按钮。")

    # --- 图片网格展示 ---
    with st.form("image_selection_form"):
        cols = st.columns(3)
        selected_indices = []
        
        for i, img_url in enumerate(st.session_state.scraped_images):
            col = cols[i % 3] 
            with col:
                # 优化链接预览
                preview_url = img_url.replace("tp=webp", "tp=jpg")
                
                # 🔥【核心修改点】使用 HTML + no-referrer 绕过防盗链 🔥
                st.markdown(
                    f'''
                    <img src="{preview_url}" 
                         style="width:100%; border-radius:8px; margin-bottom:5px; object-fit:cover; aspect-ratio: 1/1;" 
                         referrerpolicy="no-referrer">
                    ''', 
                    unsafe_allow_html=True
                )
                
                # 勾选框
                is_checked = st.checkbox(f"图片 {i+1}", key=f"img_chk_{i}")
                
                if is_checked:
                    selected_indices.append(i)
        
        st.markdown("---")
        submitted = st.form_submit_button("🚀 生成压缩包 (提取选中的图片)", type="primary", use_container_width=True)

        if submitted:
            if not selected_indices:
                st.warning("⚠️ 你一张图都没选哦！")
            else:
                valid_imgs_to_download = [st.session_state.scraped_images[i] for i in selected_indices]
                
                zip_buffer = io.BytesIO()
                success_count = 0
                total = len(valid_imgs_to_download)
                
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                
                progress_text = st.empty()
                progress_bar = st.progress(0)
                
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zf:
                    for i, img_url in enumerate(valid_imgs_to_download):
                        progress_text.text(f"正在下载第 {i+1}/{total} 张...")
                        
                        # 格式处理
                        fmt = "jpg"
                        img_url = img_url.replace("/640?from=appmsg", "/640?from=appmsg&tp=jpg")
                        img_url = img_url.replace("&tp=webp", "&tp=jpg")
                        img_url = img_url.replace("wx_fmt=webp", "wx_fmt=jpg")
                        
                        try:
                            img_data = requests.get(img_url, headers=headers, timeout=5).content
                            file_name = f"image_{success_count+1}.jpg"
                            zf.writestr(file_name, img_data)
                            success_count += 1
                        except:
                            pass
                        
                        progress_bar.progress((i + 1) / total)
                        time.sleep(0.05)
                
                progress_bar.progress(100)
                progress_text.text("打包完成！")
                
                st.session_state.zip_buffer = zip_buffer
                st.session_state.step = 3
                st.rerun()

# ================= 7. 下载按钮 (步骤 3) =================
if st.session_state.step == 3 and st.session_state.zip_buffer:
    st.balloons()
    st.success("✨ 压缩包已准备就绪！")
    
    st.download_button(
        label="📦 点击下载选中的图片 (ZIP)",
        data=st.session_state.zip_buffer.getvalue(),
        file_name="selected_images.zip",
        mime="application/zip",
        type="primary",
        use_container_width=True
    )
    
    if st.button("🔄 提取另一篇文章"):
        st.session_state.step = 1
        st.session_state.scraped_images = []
        st.session_state.zip_buffer = None
        # 清除所有勾选状态
        keys_to_remove = [k for k in st.session_state.keys() if k.startswith("img_chk_")]
        for k in keys_to_remove:
            del st.session_state[k]
        st.rerun()
