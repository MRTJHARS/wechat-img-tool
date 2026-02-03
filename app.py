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
    page_icon="📷",
    layout="centered"
)

# ================= 2. 侧边栏：使用教程 (保持不变) =================
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
    st.caption("Made with ❤️ TJH")

# ================= 3. 主界面布局 (左图右字) =================
col1, col2 = st.columns([1, 2])

with col1:
    # 🔥 这里替换了原来的机器人，改为显示爱心拼图
    # 代码会自动检测您是否上传了 heart_collage.png
    if os.path.exists("heart_collage.png"):
        st.image("heart_collage.png", use_column_width=True)
    elif os.path.exists("heart_collage.jpg"):
        st.image("heart_collage.jpg", use_column_width=True)
    else:
        # 如果还没上传图片，显示一个提示
        st.info("请上传名为 heart_collage.png 的图片")

with col2:
    # 🔥 这里保留了您习惯的原始标题
    st.title("🎨 公众号图片一键提取")
    st.markdown("##### 粘贴微信文章链接，一键打包高清原图！")

st.markdown("---")

# ================= 4. 输入区域 =================
url = st.text_input("👇在此粘贴链接:", placeholder="https://mp.weixin.qq.com/s/...", help="请确保链接是微信公众号文章")

# ================= 5. 核心逻辑 (保持不变) =================
if st.button("🚀 开始提取", type="primary"):
    if not url:
        st.warning("⚠️ 还没输入链接呢！")
    elif "mp.weixin.qq.com" not in url:
        st.error("❌ 这看起来不像是一个微信公众号链接哦。")
    else:
        with st.spinner('🔍 正在在那庞大的互联网里挖掘图片...'):
            try:
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
                
                for img in imgs:
                    src = img.get('data-src')
                    if src:
                        valid_imgs.append(src)
                
                if not valid_imgs:
                    st.error("😭 哎呀，没找到图片，可能是文章被删了。")
                    st.stop()

                # 准备 ZIP
                zip_buffer = io.BytesIO()
                success_count = 0
                total = len(valid_imgs)
                
                progress_bar = st.progress(0)
                
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zf:
                    for i, img_url in enumerate(valid_imgs):
                        # 格式处理：强制转 JPG
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
                        time.sleep(0.02) 

                progress_bar.progress(100)
                time.sleep(0.5)
                
                # 🎉 成功特效：依然保留放气球
                st.balloons()
                
                st.success(f"✨ 搞定！成功捕获 {success_count} 张高清美图！")
                
                st.download_button(
                    label="📦 点击下载 ZIP 压缩包",
                    data=zip_buffer.getvalue(),
                    file_name="wechat_images.zip",
                    mime="application/zip",
                    type="primary"
                )
                
            except Exception as e:
                st.error(f"💥 发生了一点小意外: {e}")
