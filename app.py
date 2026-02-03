import streamlit as st
import requests
from bs4 import BeautifulSoup
import zipfile
import io
import time
import re

# ================= 页面配置 =================
st.set_page_config(page_title="微信文章图片提取器", page_icon="📷"))

st.title(📷 公众号图片一键提取)
st.markdown(输入微信文章链接，自动打包所有高清图片下载。)

# ================= 输入区域 =================
url = st.text_input(👇 请在此粘贴文章链接, placeholder=httpsmp.weixin.qq.coms...)

# 伪装头
headers = {
    'User-Agent' 'Mozilla5.0 (Windows NT 10.0; Win64; x64) AppleWebKit537.36 (KHTML, like Gecko) Chrome91.0.4472.124 Safari537.36'
}

# ================= 核心逻辑 =================
if st.button(🚀 开始提取, type=primary)
    if not url
        st.warning(⚠️ 请先输入链接！)
    elif mp.weixin.qq.com not in url
        st.error(❌ 这似乎不是一个有效的微信公众号链接。)
    else
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        try
            status_text.info(正在连接服务器...)
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            
            status_text.info(正在解析页面...)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 定位正文
            content = soup.find(id=js_content)
            if not content
                content = soup # 降级处理
            
            # 找图
            imgs = content.find_all('img')
            valid_imgs = []
            
            # 预筛选有效图片链接
            for img in imgs
                src = img.get('data-src')
                if src
                    valid_imgs.append(src)
            
            if not valid_imgs
                st.error(未找到任何图片，可能是文章已被删除或受保护。)
                st.stop()

            # 准备内存中的 ZIP 文件
            zip_buffer = io.BytesIO()
            success_count = 0
            total = len(valid_imgs)
            
            with zipfile.ZipFile(zip_buffer, a, zipfile.ZIP_DEFLATED, False) as zf
                for i, img_url in enumerate(valid_imgs)
                    status_text.text(f正在下载第 {i+1}{total} 张图片...)
                    
                    # 格式处理：强制转 JPG
                    fmt = jpg
                    # 替换 url 参数以获取 jpg
                    if wx_fmt= in img_url
                        fmt = img_url.split(wx_fmt=)[1].split(&)[0]
                    
                    # 核心：把 webp 参数替换掉
                    img_url = img_url.replace(640from=appmsg, 640from=appmsg&tp=jpg)
                    img_url = img_url.replace(&tp=webp, &tp=jpg)
                    
                    # 如果本来就是 webp 且无法通过参数转换，强制后缀名为 jpg 也能骗过大部分查看器
                    if fmt == webp
                        fmt = jpg

                    try
                        # 下载图片二进制数据
                        img_data = requests.get(img_url, headers=headers, timeout=5).content
                        # 写入 ZIP
                        file_name = fimage_{success_count+1}.{fmt}
                        zf.writestr(file_name, img_data)
                        success_count += 1
                    except Exception as e
                        print(fSkipped {e})
                    
                    # 更新进度条
                    progress_bar.progress((i + 1)  total)
                    time.sleep(0.05) #稍微缓冲一下

            progress_bar.progress(100)
            status_text.success(f✅ 成功提取 {success_count} 张图片！)
            
            # ================= 下载按钮 =================
            st.download_button(
                label=📦 点击下载压缩包 (ZIP),
                data=zip_buffer.getvalue(),
                file_name=wechat_images.zip,
                mime=applicationzip,
                type=primary
            )
            
        except Exception as e

            st.error(f发生错误 {e})

