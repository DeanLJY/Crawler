from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# 加载谷歌浏览器驱动
chrome_options = Options()

# linux下运行记得加上这些参数 ----------------------------
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('lang=zh_CN.UTF-8')
# -----------------------------------------------------


def get_page_source(url, wait):
    # 加载chromedriver -------------------------------------------------
    # windows 下的 chromedriver 默认加载路径是当前路径下的 chromedriver.exe
    # linux 下的 chromedriver 默认加载路径是 /usr/bin/chromedriver
    # 当然也可以通过 executable_path 自定义
    driver = webdriver.Chrome(options=chrome_options)
    # -----------------------------------------------------------------
    driver.get(url)
    try:
        # 打开网页
        wait = WebDriverWait(driver, wait)
        wait.until(EC.presence_of_element_located((By.ID, 'aaaaaabc')))
    except Exception:
        text = driver.page_source
        #print(text.decode('UTF-8'))
        return text
    finally:
        # 关闭浏览器
        driver.quit()
