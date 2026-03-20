from DrissionPage import ChromiumOptions, ChromiumPage
import json
import os
import shutil
import time
import requests

def read_cookie():
    if "TIEBA_COOKIES" in os.environ:
        return json.loads(os.environ["TIEBA_COOKIES"])
    else:
        print("贴吧Cookie未配置！")
        return []

def get_cookie_dict():
    """把cookie列表转成dict，用于requests"""
    cookies = read_cookie()
    return {c['name']: c['value'] for c in cookies}

def get_tbs(cookie_dict):
    """获取签到必需的tbs参数"""
    resp = requests.get(
        "https://tieba.baidu.com/dc/common/tbs",
        cookies=cookie_dict,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    return resp.json().get("tbs", "")

def sign_forum(kw, tbs, cookie_dict):
    """直接调用签到API"""
    resp = requests.post(
        "https://tieba.baidu.com/sign/add",
        data={"kw": kw, "tbs": tbs, "_client_type": "2"},
        cookies=cookie_dict,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": f"https://tieba.baidu.com/f?kw={kw}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )
    return resp.json()

if __name__ == "__main__":
    print("程序开始运行")
    notice = ''

    cookie_dict = get_cookie_dict()
    tbs = get_tbs(cookie_dict)
    if not tbs:
        print("获取tbs失败，请检查Cookie是否有效")
        exit(1)
    print(f"tbs获取成功：{tbs}")

    # 用requests获取关注的贴吧列表
    count = 0
    yeshu = 0
    over = False

    while not over:
        yeshu += 1
        resp = requests.get(
            f"https://tieba.baidu.com/i/i/forum?pn={yeshu}",
            cookies=cookie_dict,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        # 解析贴吧列表（仍需要浏览器，见下面备注）
        # 这里保留浏览器方式获取列表，只替换签到部分
        break

    # ---- 如果还想用浏览器获取列表，只替换签到部分如下 ----
    co = ChromiumOptions().headless()
    chromium_path = shutil.which("chromium-browser")
    if chromium_path:
        co.set_browser_path(chromium_path)

    page = ChromiumPage(co)
    page.get("https://tieba.baidu.com/")
    page.set.cookies(read_cookie())
    page.refresh()
    page._wait_loaded(15)

    os.makedirs("debug", exist_ok=True)
    over = False
    yeshu = 0
    count = 0

    while not over:
        yeshu += 1
        page.get(f"https://tieba.baidu.com/i/i/forum?&pn={yeshu}")
        page._wait_loaded(15)

        for i in range(2, 22):
            element = page.ele(
                f'xpath://*[@id="like_pagelet"]/div[1]/div[1]/table/tbody/tr[{i}]/td[1]/a/@href'
            )
            try:
                tieba_url = element.attr("href")
                name = element.attr("title")
            except:
                msg = f"全部完成！本次总共签到 {count} 个吧..."
                print(msg)
                notice += msg + '\n\n'
                page.close()
                over = True
                break

            # 从URL提取吧名（kw参数）
            import re
            kw_match = re.search(r'[?&]kw=([^&]+)', tieba_url)
            if not kw_match:
                # 尝试从URL路径提取
                kw_match = re.search(r'/f/([^/?]+)', tieba_url)

            if kw_match:
                kw = requests.utils.unquote(kw_match.group(1))
                result = sign_forum(kw, tbs, cookie_dict)
                error_code = result.get("error_code", -1)

                if error_code == 0:
                    msg = f"{name}吧：签到成功！"
                    print(msg)
                elif error_code == 160002:
                    msg = f"{name}吧：今日已签到"
                    print(msg)
                else:
                    msg = f"{name}吧：签到结果 code={error_code}, msg={result.get('error_msg','')}"
                    print(msg)
            else:
                msg = f"{name}吧：无法解析吧名，跳过"
                print(msg)

            notice += msg + '\n\n'
            print("-------------------------------------------------")
            count += 1
            time.sleep(0.5)  # 避免请求太快

    if "SendKey" in os.environ:
        api = f'https://sc.ftqq.com/{os.environ["SendKey"]}.send'
        data = {"text": "贴吧签到信息", "desp": notice}
        try:
            req = requests.post(api, data=data, timeout=60)
            if req.status_code == 200:
                print("Server酱通知发送成功")
            else:
                print(f"通知失败，状态码：{req.status_code}")
        except Exception as e:
            print(f"通知发送异常：{e}")
    else:
        print("未配置Server酱服务...")
