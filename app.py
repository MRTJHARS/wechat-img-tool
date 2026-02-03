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
        img {
            border-radius: 8px;
        }
        /* 调整多选框的样式，让它跟图片挨得近一点 */
        .stCheckbox {
            margin-top: -10px;
        }
    </style>
""", unsafe_allow_html=True)

# ================= 3. 初始化 Session State (关键步骤) =================
# 我们需要用变量记住用户到了哪一步，以及抓取到了哪些图片
if 'step' not in st.session_state:
    st.session_state.step = 1 # 1=输入网址, 2=选择图片, 3=下载完成
if 'scraped_images' not in st.session_state:
    st.session_state.scraped_images = [] # 存储抓取到的所有图片链接
if 'zip_buffer' not in st.session_state:
    st.session_state.zip_buffer = None # 存储制作好的压缩包

# ================= 4. 侧边栏配置 =================
with st.sidebar:
    st.header("📖 使用教程")
    st.markdown("""
    1. **解析**：输入链接，点击“解析图片”。
    2. **选择**：勾选你想要的图片（默认全选）。
    3. **打包**：点击“生成压缩包”。
    4. **下载**：点击出现的“下载”按钮保存。
    """)
    st.info("💡 图片预览加载可能需要几秒钟，请耐心等待。")
    st.markdown("---")
    st.caption("Made with ❤️")

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
    st.caption("先解析，再挑选，只下你想要的！")
    st.markdown("---")
    
    # 输入框
    url = st.text_input("👇 在此粘贴链接:", placeholder="https://mp.weixin.qq.com/s/...", label_visibility="collapsed")
    
    # --- 按钮 1：解析图片 ---
    # 只有在第一步（或者想重新解析时）显示这个按钮
    if st.button("🔍 第一步：解析图片", type="primary", use_container_width=True):
        if not url:
            st.warning("⚠️ 请先粘贴链接！")
        elif "mp.weixin.qq.com" not in url:
            st.error("❌ 链接格式不对，请使用微信公众号文章链接。")
        else:
            with st.spinner('正在分析网页...'):
                try:
                    # 爬虫逻辑
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
                        # 简单的过滤：排除太小的图标，通常文章图片链接比较长
                        if src and len(src) > 20: 
                            found_imgs.append(src)
                    
                    if not found_imgs:
                        st.error("未找到图片，可能是文章已删除。")
                    else:
                        # 成功！存入 Session State
                        st.session_state.scraped_images = found_imgs
                        st.session_state.step = 2 # 进入下一步
                        st.session_state.zip_buffer = None # 清空旧的下载包
                        st.rerun() # 刷新页面显示新内容

                except Exception as e:
                    st.error(f"解析失败: {e}")

# ================= 6. 选择与下载区域 (步骤 2) =================
if st.session_state.step >= 2 and st.session_state.scraped_images:
    st.divider()
    st.subheader(f"📸 共找到 {len(st.session_state.scraped_images)} 张图片")
    
    # --- 全选/反选控制 ---
    col_sel1, col_sel2 = st.columns([1, 4])
    with col_sel1:
        # 这个checkbox用来控制默认状态
        select_all = st.checkbox("全选", value=True)
    with col_sel2:
        st.caption("取消勾选不需要的图片，然后点击底部的生成按钮。")

    # --- 图片网格展示 ---
    # 使用表单(Form)来包裹选择区，避免每次勾选都刷新页面
    with st.form("image_selection_form"):
        # 创建一个 3 列的网格
        cols = st.columns(3)
        selected_indices = []
        
        # 遍历所有图片链接
        for i, img_url in enumerate(st.session_state.scraped_images):
            col = cols[i % 3] # 决定放在第几列
            with col:
                # 1. 显示缩略图 (为了速度，直接用原链接，微信图片一般有防盗链，但在Streamlit里通常能显示)
                # 优化：把 tp=webp 改为 tp=jpg 以便预览
                preview_url = img_url.replace("tp=webp", "tp=jpg")
                st.image(preview_url, use_column_width=True)
                
                # 2. 显示勾选框
                # key是非常重要的，保证每个框独立
                is_checked = st.checkbox(f"图片 {i+1}", value=select_all, key=f"img_chk_{i}")
                if is_checked:
                    selected_indices.append(i)
        
        st.markdown("---")
        # --- 按钮 2：确认并提取 ---
        submitted = st.form_submit_button("🚀 生成压缩包 (提取选中的图片)", type="primary", use_container_width=True)

        if submitted:
            if not selected_indices:
                st.warning("⚠️ 你一张图都没选哦！")
            else:
                # 开始下载选中的图片
                # 这里的逻辑和之前一样，只是增加了筛选
                valid_imgs_to_download = [st.session_state.scraped_images[i] for i in selected_indices]
                
                zip_buffer = io.BytesIO()
                success_count = 0
                total = len(valid_imgs_to_download)
                
                # 在表单提交后，我们需要显示进度条。
                # 注意：Streamlit 表单内更新UI稍微有点限制，我们尽量简化反馈
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                # 创建一个占位符显示进度
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
                
                # 将结果存入 session state，以便在表单外部显示下载按钮
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
    
    # 允许用户重新开始
    if st.button("🔄 提取另一篇文章"):
        st.session_state.step = 1
        st.session_state.scraped_images = []
        st.session_state.zip_buffer = None
        st.rerun()
