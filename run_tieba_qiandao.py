from DrissionPage import ChromiumOptions, ChromiumPage
import json
import os
import shutil
import time
import requests
def read_cookie():
    """读取 cookie，优先从环境变量读取"""
    if "TIEBA_COOKIES" in os.environ:
        return json.loads(os.environ["TIEBA_COOKIES"])
    else:
        print("贴吧Cookie未配置！详细请参考教程！")
        return []
def get_level_exp(page):
    """获取等级和经验，如果找不到返回'未知'"""
    level = "未知"
    exp = "未知"
    try:
        # ========== 图一：CSS 选择器方案（你验证成功的版本） ==========
        level_svg = page.ele('css:svg.level-icon')
        if level_svg:
            use_ele = level_svg.ele('css:use')
            if use_ele:
                href = use_ele.attr('xlink:href')
                level = href.replace('#level_', '') if href else '未知'
        # ========== 图二：原新旧版 XPath 方案（兜底） ==========
        if level == "未知":
            # 定位两个等级元素（不会同时存在）
            level_ele = page.ele('xpath://*[@id="pagelet_aside/pagelet/my_tieba"]//div/div[1]/div[3]/div[1]/a/div')
            level_ele_new = page.ele('xpath://div[contains(@class, "forum-suffix")]/svg[contains(@class, "level-icon")]/use')
            
            # 核心：取存在的那个元素，都不存在则为None
            exist_level_ele = level_ele or level_ele_new
            
            # 提取等级文本（适配新旧版格式）
            if exist_level_ele == level_ele:
                # 旧版：直接取文本
                level = level_ele.text.strip() if level_ele.text else "未知"
            elif exist_level_ele == level_ele_new:
                # 新版：提取属性中的等级数字
                href_val = level_ele_new.attr("xlink:href")
                level = href_val.replace("#level_", "") if href_val else "未知"
            else:
                # 都不存在
                level = "未知"
    except Exception as e:
        # 任何错误都兜底为未知
        level = "未知"
    try:
        exp_old_ele = page.ele('xpath://*[@id="pagelet_aside/pagelet/my_tieba"]/div/div[1]/div[3]/div[2]/a/div[2]/span[1]')
        exp_new_ele = page.ele('xpath://div[contains(@class, "bar-info")]/div[contains(@class, "progress-text")]')
    # 分别取文本
        exp_text_old = exp_old_ele.text if exp_old_ele else ""
        exp_text_new = exp_new_ele.text.replace("经验 ", "") if exp_new_ele else ""
        # 二选一
        exp = exp_text_old or exp_text_new
        if not exp:
            exp = "未知"
    except:
        exp = "未知"
    return level, exp
if __name__ == "__main__":
    print("程序开始运行")
    # 通知信息
    notice = ''
    co = ChromiumOptions().headless()
    chromium_path = shutil.which("chromium-browser")
    if chromium_path:
        co.set_browser_path(chromium_path)
    page = ChromiumPage(co)
    url = "https://tieba.baidu.com/"
    page.get(url)
    page.set.cookies(read_cookie())
    page.refresh()
    page._wait_loaded(15)
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
                msg = f"全部爬取完成！本次总共签到 {count} 个吧..."
                print(msg)
                notice += msg + '\n\n'
                page.close()
                over = True
                break
            page.get(tieba_url)
            page.wait.eles_loaded('xpath://*[@id="signstar_wrapper"]/a/span[1]',timeout=30)
            # ========== 优化后的核心签到逻辑 ==========
            # 统一判断签到状态（兼容新旧版）
            is_signed = False
            # 旧版签到状态
            is_sign_ele = page.ele('xpath://*[@id="signstar_wrapper"]/a/span[1]')
            if is_sign_ele and is_sign_ele.text.startswith("连续"):
                is_signed = True
            # 新版签到状态
            is_sign_ele_new = page.ele('xpath://div[contains(@class, "center") and contains(text(), "连签")]')
            if is_sign_ele_new and "连签" in is_sign_ele_new.text:
                is_signed = True
            if is_signed:
                # 已签到逻辑
                level, exp = get_level_exp(page)
                msg = f"{name}吧：已签到过！等级：{level}，经验：{exp}"
                print(msg)
                notice += msg + '\n\n'
                print("-------------------------------------------------")
            else:
                # 未签到，执行签到逻辑
                sign_success = False
                # 1. 尝试旧版签到
                try:
                    sign_btn_old = page.ele('xpath://a[@class="j_signbtn sign_btn_bright j_cansign"]', timeout=10)
                    if sign_btn_old:
                        # 移除报错的clickable，直接点击（DrissionPage的click自带等待可点击）
                        sign_btn_old.click()
                        time.sleep(2)  # 延长等待时间，确保签到请求完成
                        # 验证签到是否成功
                        page.refresh()
                        page._wait_loaded(15)
                        # 重新检查签到状态
                        new_is_sign_ele = page.ele('xpath://*[@id="signstar_wrapper"]/a/span[1]')
                        new_is_sign_ele_new = page.ele('xpath://div[contains(@class, "center") and contains(text(), "连签")]')
                        if (new_is_sign_ele and new_is_sign_ele.text.startswith("连续")) or \
                           (new_is_sign_ele_new and "连签" in new_is_sign_ele_new.text):
                            level, exp = get_level_exp(page)
                            msg = f"{name}吧：旧版签到成功！等级：{level}，经验：{exp}"
                            sign_success = True
                except Exception as e:
                    msg = f"{name}吧：旧版签到尝试失败 - {str(e)}"
                    print(msg)
                    notice += msg + '\n\n'
                # 2. 旧版失败，尝试新版签到
                if not sign_success:
                    try:
                        sign_btn_new = page.ele(
                            'xpath://div[contains(@class, "button-wrapper") and @aria-describedby]/div[contains(@class, "center") and normalize-space(text())="签到"]',
                            timeout=10
                        )
                        if sign_btn_new:
                            # 移除报错的clickable，直接点击（DrissionPage的click自带等待可点击）
                            sign_btn_new.click()
                            time.sleep(2)  # 延长等待时间，确保签到请求完成
                            # 验证签到是否成功
                            page.refresh()
                            page._wait_loaded(15)
                            new_is_sign_ele = page.ele('xpath://*[@id="signstar_wrapper"]/a/span[1]')
                            new_is_sign_ele_new = page.ele('xpath://div[contains(@class, "center") and contains(text(), "连签")]')
                            if (new_is_sign_ele and new_is_sign_ele.text.startswith("连续")) or \
                               (new_is_sign_ele_new and "连签" in new_is_sign_ele_new.text):
                                level, exp = get_level_exp(page)
                                msg = f"{name}吧：新版签到成功！等级：{level}，经验：{exp}"
                                sign_success = True
                            else:
                                msg = f"{name}吧：新版签到按钮点击后未检测到签到成功"
                        else:
                            msg = f"{name}吧：未找到新版签到按钮"
                    except Exception as e:
                        msg = f"{name}吧：新版签到尝试失败 - {str(e)}"
                # 3. 最终结果反馈
                if sign_success:
                    print(msg)
                    notice += msg + '\n\n'
                else:
                    print(msg)
                    notice += msg + '\n\n'
                print("-------------------------------------------------")
            # ========== 核心签到逻辑结束 ==========
            count += 1
            page.back()
            page._wait_loaded(10)
    if "SendKey" in os.environ:
        api = f'https://sc.ftqq.com/{os.environ["SendKey"]}.send'
        title = u"贴吧签到信息"
        data = {
        "text":title,
        "desp":notice
        }
        try:
            req = requests.post(api, data=data, timeout=60)
            if req.status_code == 200:
                print("Server酱通知发送成功")
            else:
                print(f"通知失败，状态码：{req.status_code}")
                print(api)
        except Exception as e:
            print(f"通知发送异常：{e}")
    else:
        print("未配置Server酱服务...")