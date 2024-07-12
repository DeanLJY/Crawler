import re
from markdownify import MarkdownConverter
import requests
from fastapi import FastAPI, Request
from selenium_page import get_page_source
app = FastAPI()
import uvicorn

ESCAPE_CLASS = ['foot','bottom', 'tool', 'skip','header','bread','banner', 'nav', 'menu', 'button', 'material', 'dialog', 'tabindex', 'language', 'img', 'image', 'share', 'btn','search', 'lang']
ESCAPE_ID =  ['foot','bottom', 'tool', 'skip','header','bread','banner', 'nav', 'menu', 'button', 'material', 'dialog', 'tabindex', 'language', 'img', 'image', 'share', 'btn','search', 'lang']

def chomp0(text):
    prefix = ' ' if text and text[0] == ' ' else ''
    suffix = ' ' if text and text[-1] == ' ' else ''
    text = text.strip()
    return (prefix, suffix, text)

# 过滤掉 id class 中一般的菜单 顶部 底部 菜单 等无意义项
def escape_element(el, text):
    if el.has_attr('class'):
        classes = ' '.join([clz.replace(' ', '') for clz in el['class']])
        # 特殊处理 比如：class=''header' 但是里面的内容 可能是 问答 这种情况 就要排除掉
        if any(element in classes for element in ESCAPE_CLASS):
            if ('?' in text or '？' in text):
                return text
            return ''
    if el.has_attr('id'):
        _id = el['id']
        if any(element in _id for element in ESCAPE_CLASS):
            return ''
    return text
    
def skip_display_none(el, text):
    if el.has_attr('style'):
        _style = el['style']
        _style=_style.replace(' ', '')
        if 'display:none' in _style:
            return ''
    return text

class CustomConverter(MarkdownConverter):
    
    def convert_div(self, el, text, convert_as_inline):
        text = escape_element(el, text)
        return text
        
    def convert_nav(self, el, text, convert_as_inline):
        return ""
    def convert_footer(self, el, text, convert_as_inline):
        return ""
    
    def convert_select(self, el, text, convert_as_inline):
        return ""

    def convert_button(self, el, text, convert_as_inline):
        return ""

    def convert_label(self, el, text, convert_as_inline):
        return ""

    def convert_title(self, el, text, convert_as_inline):
        return ""
    
    def convert_table(self, el, text, convert_as_inline):
        # 多个表格连在一起情况 加上分隔符
        text = skip_display_none (el, text)
        return text + '\n---\n' 
    
    def convert_li(self, el, text, convert_as_inline):
        
        if el.has_attr('class'):
            classes = ' '.join(el['class'])
            if any(element in classes for element in ESCAPE_CLASS):
                return '' 
        
        parent = el.parent
        # 特殊处理 代码块中的序号
        if 'class' in parent.attrs and 'pre-numbering' in parent.attrs['class']:
            return ''
        if parent is not None and parent.name == 'ol':
            if parent.get("start"):
                start = int(parent.get("start"))
            else:
                start = 1
            bullet = '%s.' % (start + parent.index(el))
        else:
            depth = -1
            while el:
                if el.name == 'ul':
                    depth += 1
                el = el.parent
            bullets = self.options['bullets']
            bullet = bullets[depth % len(bullets)]
            if text is None or len(text.strip()) == 0:
                return ''
        return '%s %s\n' % (bullet, (text or '').strip())

    def convert_a(self, el, text, convert_as_inline):
        # 处理前后换行的情况
        if el.next_sibling == '\n':
            return ''
        parent = el.parent
        # 处理被<li><div>包裹的a标签
        ignore_list = ["ul", "i", "a", "br"]
        if (el.next_sibling is None or el.next_sibling.name is None or el.next_sibling.name in ignore_list) and \
                (el.previousSibling is None or el.previousSibling.name is None or el.previousSibling.name in ignore_list) and \
                (parent.name == 'li' or parent.name == 'div'):
            return ''
        prefix, suffix, text = chomp0(text)
        if not text:
            return ''
        if el.has_attr('class'):
            classes = ' '.join(el['class'])
            # 过滤一般干扰项的a标签中出现class，  排除掉 父级标签是td
            if any(element in classes for element in ESCAPE_CLASS) and not parent.name == 'td':
                return ''
        return text


@app.post("/url2md")
async def queryHtmlText(request: Request):
    params = await request.json()
    url = params.get("url")
    wait = params.get("wait", 5)
    print('url', url)
    print('wait', wait)
    if wait == 0:
        response = requests.get(url)
        if response.status_code == 200:
            response.encoding = 'utf-8-sig'
            html_content = response.text
            ret = md(html_content, strip=['img'])
            ret = post_process_html(ret)
            return {
                "response": ret,
                "status": 200
            }
        else:
            return {
                "response": "获取网页失败",
                "status": 500
            }
    else:
        html_content = get_page_source(url, wait)
        if html_content is None or len(html_content) == 0:
            return {
                "response": "获取网页失败",
                "status": 500
            }
        else:
            ret = md(html_content, strip=['img'])
            ret = post_process_html(ret)
            return {
                "response": ret,
                "status": 200
            }


@app.post("/html2md")
async def html2md(request: Request):
    params = await request.json()
    html = params.get("html")
    ret = md(html, strip=['img'])
    ret = post_process_html(ret)
    return {
        "response": ret,
        "status": 200
    }


def post_process_html(md_content):
    lines = md_content.split('\n')
    new_lines = []
    for line in lines:
        # 如果该行全是 * + | 等符号 直接去掉
        line0 = line.replace('*', '').replace('+', '').replace('|', '').replace('=', '').strip()
        if len(line0) > 0:
            line0 = filter_repeat_line(line)
        # 去掉重复的行
        if len(line0) > 0 and line0 not in new_lines:
            new_lines.append(line0)
    return "\n".join(new_lines)


def filter_repeat_line(line_text):
    sub_words = []
    for word in line_text:
        if word not in sub_words:
            sub_words.append(word)
    if len(sub_words) > 2 or len(line_text) % len(sub_words) > 0:
        return line_text
    sub = ''.join(sub_words)
    times = len(line_text) / len(sub_words)
    if times > 3 and sub * int(times) == line_text:
        return ""
    return line_text


def md(html, **options):
    html = html.replace('<div class="clearBoth"></div>', '')
    mdresult = CustomConverter(**options).convert(html)
    return re.sub("\n+", "\n", mdresult)


def test():
    url = r'https://www.censtatd.gov.hk/tc/press_release_detail.html?id=-4924'
    # url = r'https://www.fdc.gov.hk/tc/whatson_detail.php?id=2024031212212477871'
    url = r'https://www.news.gov.hk/chi/2024/06/20240605/20240605_214725_788.html?type=category&name=clarification'
    # url = r'https://www.afa-academy.com/zh/20231110_tc/'
    # url = r'https://www.info.gov.hk/gia/general/202407/02/P2024070200448.htm'
    # url = r'https://www.edb.gov.hk/sc/about-edb/info/pledge/index.html'
    # url = r'https://www.emsd.gov.hk/sc/gas_safety/lpg_vehicle_scheme/publications/general/results_of_lpg_sample_analysis/index.html#'
    url = r'https://www.edb.gov.hk/sc/curriculum-development/curriculum-area/gifted/resources_and_support/school_network/detail_info.html'
    url = r'https://www.immd.gov.hk/hks/contactus/control_points.html'
    url = r'https://www.gov.hk/sc/nonresidents/visarequire/visasentrypermits/applystudy.htm'
    url = r'https://www.police.gov.hk/ppp_sc/11_useful_info/cert_no_crime.html'
    url = r'https://www.bd.gov.hk/sc/building-works/alterations-and-additions/index.html'
    url = r'https://www.housingauthority.gov.hk/sc/business-partnerships/quality-housing/quality-housing-seminar/index.html'
    html_content = get_page_source(url, 5)
    # print(html_content)
    ret = md(html_content, strip=['img'])
    ret = post_process_html(ret)
    print(ret)

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8085, log_level="info")
    # test()