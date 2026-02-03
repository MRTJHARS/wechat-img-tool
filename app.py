import streamlit as st
import requests
from bs4 import BeautifulSoup
import zipfile
import io
import time
import os

# ================= 1. 页面基础配置 =================
st.set_page_config(
    page_title="微信文章图片提取器", 
    page_icon="❤️",
    layout="centered"
)

# ================= 2. 侧边栏：使用教程 =================
with st.sidebar:
    st.header("📖 使用教程")
    st.markdown("""
    1. 打开微信公众号文章。
    2. 点击右上角 **...** 复制链接。
    3. 粘贴到右侧输入框。
    4. 点击 **开始提取**。
    5. 等待下载完成后点击 **下载压缩包**。
    6. **iPhone用户**：
       - 点下载 -> 在“文件”App打开。
       - 点击 ZIP 包自动解压。
       - 进文件夹全选图片 -> 存入相册。
    """)
    st.info("💡 提示：所有图片会自动转为 JPG 格式，方便手机查看。")
    st.markdown("---")
    st.caption("Made with ❤️")

# ================= 3. 主界面布局 (左图右字) =================
col1, col2 = st.columns([1, 2])

with col1:
    # 🔥 这里展示您的爱心拼图
    # 请确保 GitHub 上有一张名为 heart_collage.png 的图片
    # 如果您的图片是 jpg 格式，请将下面的 .png 改为 .jpg
    if os.path.exists("heart_collage.png"):
        st.image("heart_collage.png", use_column_width=True)
    elif os.path.exists("heart_collage.jpg"):
        st.image("heart_collage.jpg", use_column_width=True)
    else:
        # 如果还没上传图片，显示一个默认的文字提示，防止报错
        st.warning("请上传名为 heart_collage.png 的图片到 GitHub")

with col2:
    st.title("❤️ 美好回忆提取器")
    st.markdown("##### 粘贴文章链接，一键永久保存珍贵照片！")

st.markdown("---")

# ================= 4. 输入区域 =================
url = st.text_input("👇 在此粘贴链接:", placeholder="https://mp.weixin.qq.com/s/...", help="请确保链接是微信公众号文章")

# ================= 5. 核心提取逻辑 =================
if st.button("🚀 开始提取", type="primary"):
    if not url:
        st.warning("⚠️ 还没输入链接呢！")
    elif "mp.weixin.qq.com" not in url:
        st.error("❌ 这看起来不像是一个微信公众号链接哦。")
    else:
        # 显示加载状态
        with st.spinner('🔍 正在在那庞大的互联网里挖掘图片...'):
            try:
                # 伪装成浏览器
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                resp = requests.get(url, headers=headers, timeout=10)
                resp.raise_for_status()
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                content = soup.find(id="js_content")
                if not content:
                    content = soup 
                
                imgs = content.find_all('img')
                valid_imgs = []
                
                # 筛选有效图片
                for img in imgs:
                    src = img.get('data-src')
                    if src:
                        valid_imgs.append(src)
                
                if not valid_imgs:
                    st.error("😭 哎呀，没找到图片，可能是文章被删了。")
                    st.stop()

                # 准备 ZIP 压缩包
                zip_buffer = io.BytesIO()
                success_count = 0
                total = len(valid_imgs)
                
                # 进度条
                progress_bar = st.progress(0)
                
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zf:
                    for i, img_url in enumerate(valid_imgs):
                        # === 格式处理核心逻辑 ===
                        # 强制把 webp 转换为 jpg
                        img_url = img_url.replace("/640?from=appmsg", "/640?from=appmsg&tp=jpg")
                        img_url = img_url.replace("&tp=webp", "&tp=jpg")
                        img_url = img_url.replace("wx_fmt=webp", "wx_fmt=jpg")
                        
                        try:
                            # 下载图片
                            img_data = requests.get(img_url, headers=headers, timeout=5).content
                            # 强制命名为 .jpg
                            file_name = f"image_{success_count+1}.jpg"
                            zf.writestr(file_name, img_data)
                            success_count += 1
                        except:
                            pass
                        
                        # 更新进度
                        progress_bar.progress((i + 1) / total)
                        time.sleep(0.02) 

                progress_bar.progress(100)
                time.sleep(0.5)
                
                # 🎉 成功特效：放气球！
                st.balloons()
                
                st.success(f"✨ 搞定！成功捕获 {success_count} 张高清美图！")
                
                # 下载按钮
                st.download_button(
                    label="📦 点击下载 ZIP 压缩包",
                    data=zip_buffer.getvalue(),
                    file_name="memories_images.zip",
                    mime="application/zip",
                    type="primary"
                )
                
            except Exception as e:
                st.error(f"💥 发生了一点小意外: {e}")
