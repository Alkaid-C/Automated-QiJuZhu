# -*- coding: utf-8 -*-
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import re
import time
import os
import logging
import sys
from datetime import datetime
from PIL import Image
from colorama import init, Fore, Back, Style  

BBDOWN_PATH = r".\bin\BBDown.exe"
LOG_DIR ="./log/"
LOGFILE_PATH = r".\log\log.txt"
URL = r"https://space.bilibili.com/3546831533378448/lists/4619502?type=series"
PATTERN = r'https?://(?:www\.)?bilibili\.com/video/BV[0-9a-zA-Z]{10}'
SHELL_ERROR = Fore.WHITE + Back.RED
SHELL_WARNING = Fore.WHITE + Back.YELLOW
SHELL_INFO = Fore.WHITE + Back.BLUE
SHELL_ACTION = Fore.WHITE +Back.GREEN
SHELL_RESET = Style.RESET_ALL
IMAGE_PATH="./qrcode.png"

def WriteLog(message, video_id="Unknown"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] 视频ID: {video_id}\n{message}\n{'='*50}\n"
    
    try:
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR)
            
        with open(LOGFILE_PATH, "a", encoding="utf-8") as log_file:
            log_file.write(log_entry)
    except Exception as e:
        print(f"{SHELL_ERROR}写入日志文件失败: {str(e)}{SHELL_ERROR}")

def GetVideoList(url=URL):
    os.environ['WDM_LOG_LEVEL'] = '0'
    logging.getLogger('selenium').setLevel(logging.ERROR)
    
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--silent")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-webgl")
    
    try:
        print("因为B站限制未登录用户浏览内容，请您在即将打开的网页中登录，以便程序获取视频内容。登陆后请回到本界面")
        print("程序将于5秒后打开Chrome浏览器登录界面。")
        print("{SHELL_ACTION}请在浏览器中登录B站账号{SHELL_RESET}")
        print("登录成功后，请输入'y'继续")
        time.sleep(5)
        service = Service(log_path=os.devnull)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.get("https://passport.bilibili.com/login")
        
        user_input = input(f"{SHELL_ACTION}您是否已成功登录B站？(y/n):{SHELL_RESET}").lower()
        if user_input == 'y':
            print("登录确认，继续执行...")
        else:
            print("退出程序...")
            time.sleep(5)
            driver.quit()
            sys.exit() 
        
        print(f"{SHELL_INFO}正在获取最近的录播列表...{SHELL_RESET}")
        driver.get(url)
        time.sleep(5)
        html_content = driver.page_source
        
        all_links = re.findall(PATTERN, html_content)
        unique_links = list(set(all_links))
        
        if len(unique_links) != 30:
            print(f"{SHELL_WARNING}注意！录播链接提取可能出错，程序继续运行...{SHELL_RESET}")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_dump = os.path.join(LOG_DIR, f"FetchedWebPage_{timestamp}.html")
            with open(html_dump, "w", encoding="utf-8") as f:
                f.write(html_content)
            WriteLog(f"视频链接提取可能出错，提取到了{len(unique_links)}个链接")
               
        driver.quit()
        
        return unique_links
    
    except Exception as e:
        print(f"{SHELL_ERROR}提取录播链接时出现外部错误: {e}{SHELL_RESET}")
        WriteLog(f"提取录播链接时出现外部错误: {e}")
        if 'driver' in locals():
            driver.quit()
        return []

def GetVideoInfo(video_id):
    results = []
    i=1
    for item in video_id:
        print(f"正在获取第{i}个视频的信息...")
        i+=1
        try:
            subprocess.run("chcp 65001", shell=True, capture_output=True, text=True)

            cmd = f".\\bin\\BBDown.exe {item} -info"
            process = subprocess.run(cmd, 
                                   shell=True, 
                                   capture_output=True, 
                                   text=True, 
                                   encoding='utf-8')

            if process.returncode != 0:
                print(f"{SHELL_ERROR}获取视频{item}的信息时出错!{SHELL_RESET}")
                WriteLog(f"调用BBDown获取视频{item}的信息时出错!返回代码为{process.returncode}，详细返回如下", item)
                WriteLog(process.stdout, item)
                WriteLog(process.stderr, item)
                continue
            
            output = process.stdout
            match = re.search(r'.*视频标题: (.+?)(?:\r?\n|$)', output)
            if match:
                title = match.group(1).strip()
                results.append([item, title])
            else:
                results.append([item, "无标题"])
                print(f"{SHELL_WARNING}无法找到视频 {item} 的标题，程序继续运行{SHELL_RESET}")
                WriteLog(f"无法找到视频 {item} 的标题", item)
                WriteLog(process.stdout, item)
                WriteLog(process.stderr, item)
            
        except Exception as e:
            results.append([item, "获取失败"])
            print(f"{SHELL_ERROR}获取视频{item}的信息时出现未知错误: {str(e)}{SHELL_RESET}")
            WriteLog(f"获取视频{item}的信息时出现未知错误: {str(e)}", item)
        
        time.sleep(1)
    
    return results

def SelectVideo(video_info):
    display_count = min(30, len(video_info))

    print("\n{:<5} {:<15} {}".format("序号", "BV号", "视频标题"))
    print("-" * 70)
    for i in range(display_count):
        bv_id = video_info[i][0]
        title = video_info[i][1]
        print("{:<5} {:<15} {}".format(i+1, bv_id, title))

    while True:
        user_input = input(f"\n{SHELL_ACTION}请输入要下载的视频的序号(用空格分隔，例如: 1 3 5。你也可输入N直接退出程序，或输入E保留日志并退出程序（如果你认为获取的视频信息有错）: {SHELL_RESET}")
        
        if user_input.upper() == 'N':
            print("已选择退出，程序即将中止...")
            time.sleep(5)
            sys.exit() 
        if user_input.upper() == 'E':
            print("已选择退出，程序即将记录日志并中止...")
            WriteLog("用户在选择下载列表时退出")
            WriteLog(str(video_info))
            time.sleep(5)
            sys.exit() 
        
        try:
            selected_indices = [int(x) for x in user_input.split()]

            invalid_indices = [idx for idx in selected_indices if idx < 1 or idx > display_count]
            if invalid_indices:
                print(f"错误: {', '.join(map(str, invalid_indices))} 不是有效编号，请输入1到{display_count}之间的编号")
                continue
            break
            
        except ValueError:
            print("错误: 请输入有效的数字编号。多个视频用空格分隔，例如: 1 3 5。你也可输入N直接退出程序，或输入E保留日志并退出程序（如果你认为获取的视频信息有错）:")
    
    selected_bv_ids = []
    for idx in selected_indices:
        selected_bv_ids.append(video_info[idx-1][0])
    return selected_bv_ids

def Download(download_id):
    flag = ""
    while True:
        user_input = input(f"\n{SHELL_ACTION}下载完整视频请输入v，仅下载音频输入a，仅下载AI字幕输入s，退出程序输入n: {SHELL_RESET}")
        if user_input.lower() == 'v':
            flag = " "
            break
        elif user_input.lower() == 'a':
            flag = " --audio-only"
            break
        elif user_input.lower() == "s":
            flag = " --sub-only --skip-ai False"
            break
        elif user_input.lower() == "n":
            print("已选择退出，程序即将中止...")
            time.sleep(5)
            sys.exit() 
        else:
            print("输入无效，请重新输入。")
    
    flag2 = ""
    while True:
        user_input = input(f"\n{SHELL_ACTION}请指定下载文件夹，如D:\\Videos: {SHELL_RESET}")
        try:
            if not os.path.exists(user_input):
                os.makedirs(user_input)
                print(f"已创建文件夹: {user_input}")
            
            if os.path.isdir(user_input):
                flag2 = user_input
                break
            else:
                print("这不是有效的文件夹路径，请重新输入")
        except Exception as e:
            print(f"无法创建此文件夹: {str(e)}，请检查是否是有效的文件夹路径")
    
    i=1
    for item in download_id:
        print(f"正在下载第{i}个视频，您共选择了{len(download_id)}个视频。")
        print("视频下载过程可能较为漫长，请您耐心等待...可通过检测网络流量确认下载是否仍在进行。")
        try:
            subprocess.run("chcp 65001", shell=True, capture_output=True, text=True)

            cmd = f".\\bin\\BBDown.exe {item}{flag} --work-dir \"{flag2}\""
            
            process = subprocess.run(cmd, 
                                   shell=True, 
                                   capture_output=True, 
                                   text=True, 
                                   encoding='utf-8')

            if process.returncode != 0:
                print(f"{SHELL_ERROR}下载视频{item}时出错!{SHELL_RESET}")
                WriteLog(f"调用BBDown下载视频{item}的信息时出错!返回代码为{process.returncode}，详细返回如下", item)
                WriteLog(process.stdout, item)
                WriteLog(process.stderr, item)
            else:
                print(f"视频 {item} 下载完成！")
            
        except Exception as e:
            print(f"下载视频{item}时出现未知错误: {str(e)}")
            WriteLog(f"下载视频{item}时出现未知错误: {str(e)}", item)
        
        time.sleep(1)
    
    return 0

def main():
    init(convert=True)
    print(f"{SHELL_INFO}埃瑟斯起居注自动机{SHELL_RESET}")
    print(f"{SHELL_INFO}作者：三册 版本：v1.0{SHELL_RESET}")
    print("=" * 50)
    
    user_input=input(f"\n{SHELL_ACTION}您是第一次使用本程序吗？是输入y，不是输入n：{SHELL_RESET}")
    if user_input=='y':
        print("接下来您将需要登录两次。这是因为B站限制未登录用户浏览内容，以及我技术水平太菜导致的。首先，稍后将弹出一个二维码，请用手机客户端扫描登录,然后关闭该二维码，回到本窗口。")
        user_input=input(f"\n{SHELL_ACTION}请输入y确认，输入任意字符退出:{SHELL_RESET}")
        time.sleep(0.5)
        if user_input=='y':
            cmd=r".\bin\BBDown.exe login"
            process = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,)
            ready = False
            while ready == False:
                try:
                    with open(IMAGE_PATH, "rb") as f:
                        pass
                    ready = True
                except (IOError, PermissionError):
                    time.sleep(0.1)
            time.sleep(0.1)
            image = Image.open(IMAGE_PATH)
            image.show()
            print(f"{SHELL_ACTION}已打开图像；也可从文件目录中手动找到qrcode.png并手动打开。扫描登录后会自动执行下一步{SHELL_RESET}")
            process.wait()
        else:
            sys.exit()
    
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    
    Trashlist=os.listdir(LOG_DIR)
    for Trash in Trashlist:
        os.remove(os.path.join(LOG_DIR, Trash))
    
    video_id = GetVideoList()
    if not video_id:
        print("未获取到任何视频链接，程序退出")
        sys.exit(1)
        
    print(f"成功获取到最近{len(video_id)} 个视频链接。接下来，将获取视频信息...")
    video_info = GetVideoInfo(video_id)
    
    if not video_info:
        print("无法获取视频信息，程序退出")
        sys.exit(1)
        
    download_id = SelectVideo(video_info)
    if download_id:
        print(f"您选择了 {len(download_id)} 个视频进行下载")
        print(f"{SHELL_INFO}开始下载{SHELL_RESET}")
        Download(download_id)
        print("所有下载任务已完成！")
    else:
        print("未选择任何视频下载，程序退出")
    
    input("按任意键退出...")

if __name__ == "__main__":
    main()