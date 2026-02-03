import streamlit as st
import requests
from bs4 import BeautifulSoup
import zipfile
import io
import time
import os
import math

# ================= 1. 页面配置 =================
st.set_page_config(
    page_title="微信文章图片提取器", 
    page_icon="🎨",
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
        /* 分页按钮样式微调 */
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

# 每页显示多少张图片（建议 12 张，速度最快）
ITEMS_PER_PAGE = 12

# --- 全选/全不选回调 ---
def toggle_all():
    # 即使只显示 12 张，全选依然控制所有图片的状态
    is_all_selected = st.session_state.select_all_key
    if 'scraped_images' in st.session_state:
        for i in range(len(st.session_state.scraped_images)):
            key_name = f"img_chk_{i}"
            st.session_state[key_name] = is_all_selected

# --- 翻页回调 ---
def prev_page():
    if st.session_state.current_page > 1:
        st.session_state.current_page -= 1

def next_page():
    # 计算总页数
    total_imgs = len(st.session_state.scraped_images)
    total_pages = math.ceil(total_imgs / ITEMS_PER_PAGE)
    if st.session_state.current_page < total_pages:
        st.session_state.current_page += 1

# ================= 4. 侧边栏 =================
with st.sidebar:
    st.header("📖 使用教程")
    st.markdown("""
    1. **解析**：输入链接，点击“解析图片”。
    2. **选择**：勾选你想要的图片（支持分页浏览）。
    3. **打包**：点击“生成压缩包”。
    4. **下载**：点击出现的“下载”按钮保存。
    """)
    st.info("💡 **分页模式**已开启，全选操作会瞬间响应！")
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
    st.caption("极速分页版：告别卡顿，丝滑体验！")
    st.markdown("---")
    
    url = st.text_input("👇 在此粘贴链接:", placeholder="https://mp.weixin.qq.com/s/...", label_visibility="collapsed")
    
    if st.button("🔍 第一步：解析图片", type="primary", use_container_width=True):
        if not url:
            st.warning("⚠️ 请先粘贴链接！")
        elif "mp.weixin.qq.com" not in url:
            st.error("❌ 链接格式不对，请使用微信公众号文章链接。")
        else:
            with st.spinner('正在分析网页...'):
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
                        st.error("未找到图片，可能是文章已删除。")
                    else:
                        st.session_state.scraped_images = found_imgs
                        st.session_state.step = 2 
                        st.session_state.zip_buffer = None
                        st.session_state.current_page = 1 # 重置回第一页
                        
                        # 解析成功默认全选
                        for i in range(len(found_imgs)):
                            st.session_state[f"img_chk_{i}"] = True
                            
                        st.rerun()
                except Exception as e:
                    st.error(f"解析失败: {e}")

# ================= 6. 选择与下载区域 (步骤 2) =================
if st.session_state.step >= 2 and st.session_state.scraped_images:
    st.divider()
    
    # --- 计算分页数据 ---
    total_items = len(st.session_state.scraped_images)
    total_pages = math.ceil(total_items / ITEMS_PER_PAGE)
    current_p = st.session_state.current_page
    
    # 获取当前页的图片切片
    start_idx = (current_p - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    current_batch = st.session_state.scraped_images[start_idx:end_idx]
    
    st.subheader(f"📸 共 {total_items} 张图片 (第 {current_p} / {total_pages} 页)")
    
    # --- 顶部控制栏 (全选 + 分页器) ---
    c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1])
    with c1:
        # 全选按钮
        st.checkbox("全选 (包含所有页)", value=True, key="select_all_key", on_change=toggle_all)
    with c2:
        st.button("⬅️ 上一页", on_click=prev_page, disabled=(current_p == 1), use_container_width=True)
    with c3:
        # 显示页码（居中显示有点难，直接用 markdown）
        st.markdown(f"<div style='text-align: center; line-height: 2.5;'>{current_p} / {total_pages}</div>", unsafe_allow_html=True)
    with c4:
        st.button("下一页 ➡️", on_click=next_page, disabled=(current_p == total_pages), use_container_width=True)

    # --- 图片网格 (只渲染当前页的 12 张) ---
    with st.form("image_selection_form"):
        cols = st.columns(3)
        
        # 统计所有选中的图片索引（用于提交）
        # 注意：这里我们不能只看当前页的，要看 session_state 里所有的
        
        # 渲染当前页
        for i, img_url in enumerate(current_batch):
            global_index = start_idx + i # 算出它在总列表里的真实索引
            
            col = cols[i % 3] 
            with col:
                preview_url = img_url.replace("tp=webp", "tp=jpg")
                st.markdown(
                    f'''<img src="{preview_url}" style="width:100%; border-radius:8px; margin-bottom:5px; object-fit:cover; aspect-ratio: 1/1;" referrerpolicy="no-referrer">''', 
                    unsafe_allow_html=True
                )
                
                # 绑定全局唯一的 Key
                st.checkbox(f"图片 {global_index+1}", key=f"img_chk_{global_index}")
        
        st.markdown("---")
        submitted = st.form_submit_button("🚀 生成压缩包 (提取所有勾选图片)", type="primary", use_container_width=True)

        if submitted:
            # 收集所有选中的图片（遍历 Session State）
            selected_final_indices = []
            for i in range(total_items):
                if st.session_state.get(f"img_chk_{i}", False):
                    selected_final_indices.append(i)
            
            if not selected_final_indices:
                st.warning("⚠️ 你一张图都没选哦！")
            else:
                valid_imgs_to_download = [st.session_state.scraped_images[i] for i in selected_final_indices]
                
                zip_buffer = io.BytesIO()
                success_count = 0
                total = len(valid_imgs_to_download)
                
                headers = {'User-Agent': 'Mozilla/5.0'}
                progress_text = st.empty()
                progress_bar = st.progress(0)
                
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zf:
                    for i, img_url in enumerate(valid_imgs_to_download):
                        progress_text.text(f"正在下载第 {i+1}/{total} 张...")
                        
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
        label="📦 点击下载 (ZIP)",
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
        st.session_state.current_page = 1
        keys_to_remove = [k for k in st.session_state.keys() if k.startswith("img_chk_")]
        for k in keys_to_remove:
            del st.session_state[k]
        st.rerun()
