import asyncio
import re
from datetime import datetime
import time
import os
import json
from bilibili_api import channel_series, Credential
import bilibili_api
import httpx
from colorama import init, Fore, Back, Style
from pathlib import Path
import sys
import subprocess

SERIES_ID=4619502
BBDOWN_PATH = r".\bin\BBDown.exe"
COOKIE_PATH = r".\bin\BBDown.data"
LOG_DIR ="./log/"
LOGFILE_PATH = r".\log\log.txt"
LOG_HAPPENED=False
SETTING_PATH=r".\setting.json"
ARGUMENTS_=["LastVideoBV", "OiMode", "MultiThread", "Content", "Codec", "DownloadDir" , "LastSuccess"]
DEFAULT_ARGUMENTS__={"LastVideoBV":"BV0", "OiMode":False, "MultiThread":False, "Content": "Video", "Codec":"H.264", "DownloadDir":r".\Downloads\ " , "LastSuccess": True}

def LogWriter(Summary, Raiser, Critical=False, Detail="None"):
    global LOG_HAPPENED
    LOG_HAPPENED=True
    LogEntry = f"{'='*50}\n Critical:{str(Critical)}\n{Summary}\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n Raiser: {Raiser}\n Detail:\n {Detail}\n\n"
    try:
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR)
            
        with open(LOGFILE_PATH, "a", encoding="utf-8") as LogFile:
            LogFile.write(LogEntry)
        print("日志写入完成")
    except Exception as Exc:
        print(f"写入日志文件失败: {str(Exc)}。\n试图写入日志的内容如下，请将其提交开发者:\n{LogEntry}")
    if Critical==False:
        print("程序继续运行。如果最终运行结果与预期不一致，请将日志提交开发者。")
    else:
        print("程序停止运行。请将日志提交开发者。")
        input("按回车键退出程序:")
        sys.exit(1)

        
def ShellPrinter(Message, MessageType="Trivial"):
    SHELL_ERROR = Fore.WHITE + Back.RED
    SHELL_WARNING = Fore.WHITE + Back.YELLOW
    SHELL_INFO = Fore.WHITE + Back.BLUE
    SHELL_SUCCESS = Fore.WHITE +Back.GREEN
    SHELL_RESET = Style.RESET_ALL
    init(convert=True)
    match MessageType:
        case "Trivial":
            print(Message)
        case "Info":
            print(f"{SHELL_INFO}{Message}{SHELL_RESET}")
        case "Warning":
            print(f"{SHELL_WARNING}{Message}{SHELL_RESET}")
        case "Error":
            print(f"{SHELL_ERROR}{Message}{SHELL_RESET}")
        case "Success":
            print(f"{SHELL_SUCCESS}{Message}{SHELL_RESET}")
        case _:  # Error case
            print(Message)
            ShellPrinter("程序发生内部错误，正在将错误信息写入日志文件。","Warning")
            LogWriter (Summary="Wrong Parameter Passed", Raiser="ShellPrinter", Detail=f"Parameters: \n MessageType={MessageType}\n Message={Message}")

def ShellGetter(Message, allowed_input, input_map=[]):
    def DirValidator(Dir):
        try:
            if not os.path.exists(Dir):
                os.makedirs(Dir)
            
            if os.path.isdir(Dir):
                return True
        except:
            return False
    if allowed_input=="ValidDir":
        while True:
            ShellPrinter(Message, "Info")
            UserInput=input()
            if DirValidator(UserInput):
                return UserInput
        else:
            ShellPrinter("输入无效，请重新输入：\n", "Warning")
    
    if (len(input_map)>0 and (not len(allowed_input)==len(input_map))) or len(allowed_input)==0:
        ShellPrinter("程序发生致命内部错误，正在将错误信息写入日志文件。","Error")
        LogWriter(Summary="Internal Error", Raiser="ShellGetter", Critical=True, Detail=f"Message={Message}\n allowed_input={allowed_input}\n input_map={input_map}")
    ShellPrinter(Message, "Info")
    while True:
        UserInput = input()
        if UserInput in allowed_input:
            if input_map:
                return input_map[allowed_input.index(UserInput)]
            else:
                return UserInput
        else:
            ShellPrinter("输入无效，请重新输入：\n", "Warning")

def Settingvalidator():
    if not os.path.isfile(SETTING_PATH):
        return False
    try:
        with open(SETTING_PATH, 'r') as File:
            settings_ = json.load(File)
        
        # Check if all required keys exist
        for Key in ARGUMENTS_:
            if Key not in settings_:
                return False      
        return True
    except:
        return False
        
def SettingGetter(Key):
    if Key not in ARGUMENTS_:
        ShellPrinter("程序发生致命内部错误，正在将错误信息写入日志文件。","Warning")
        LogWriter (Summary="Wrong Parameter Passed", Raiser="SettingGetter", Detail=f"Parameters: \n Key={Key}")
    
    try:
        with open(SETTING_PATH, 'r') as File:
            Settings_ = json.load(File)
        return Settings_[Key]
    except Exception as Exp:
        ShellPrinter("读取设置时出错，将采用默认设置，正在将错误信息写入日志文件。","Warning")
        LogWriter (Summary="Error when read setting", Raiser="SettingGetter", Detail=f"Parameters: \n Key={Key}\n Error:\n {Exp}")
        return DEFAULT_ARGUMENTS__[Key]
    
def SettingSetter(Key, Value):
    if Key not in ARGUMENTS_:
        ShellPrinter("程序发生内部错误，您的设置没有被保存，正在将错误信息写入日志文件。","Warning")
        LogWriter (Summary="Wrong Parameter Passed", Raiser="SettingSetter", Detail=f"Parameters: \n Key={Key}\n Value={Value}")
    try:
        if Settingvalidator():
            with open(SETTING_PATH, 'r') as File:
                Settings_ = json.load(File)
            Settings_[Key] = Value
        else:
            Settings_ = DEFAULT_ARGUMENTS__.copy()
            Settings_[Key] = Value
        with open(SETTING_PATH, 'w') as File:
            json.dump(Settings_, File, indent=4)
    except Exception as Exp:
        ShellPrinter("保存设置时出错，您的设置没有被保存，正在将错误信息写入日志文件。","Warning")
        LogWriter (Summary="Error when writes setting", Raiser="SettingSetter", Detail=f"Parameters: \n Key={Key}\n Value={Value}\n Error:\n {Exp}")
        
def Initializer():
    Oi=False
    def BBDownLogin():
        ShellPrinter("因为B站限制未登录用户浏览内容，接下来，请用手机b站客户端扫描二维码登录。","Info")
        process = subprocess.Popen(f"{BBDOWN_PATH} login")
        process.wait()
    def CookieReader(Repeat=False):
        time.sleep(0.1)
        try:
            ShellPrinter("正在获取登陆数据")
            with open(COOKIE_PATH, 'r') as File:
                RawCookie = File.read()
                SessData = re.search(r"SESSDATA=([^;]+)",RawCookie)
                if SessData:
                    return SessData.group(1)
                else:
                    raise ValueError(f"SESSDATA Not Found! RawCookie={RawCookie}")
        except Exception as Exp:
            if not Repeat:
                ShellPrinter("未找到登陆数据，您需要重新登陆。","Warning")
                BBDownLogin()
                return CookieReader(True)
            else:
                ShellPrinter("仍然无法找到登录数据！正在将详情写入日志。","Error")
                LogWriter(Summary="Cannot find cookie",Raiser="CookieReader",Critical=True, Detail=str(Exp))
    if not Settingvalidator():
        ShellPrinter("未能读取到配置文件。您可能是第一次使用本程序，也可能是配置文件已损坏。","Info")
        BBDownLogin()
    else:
        if SettingGetter("LastSuccess")==False:
            ShellPrinter("似乎上次运行本程序时出现错误，现尝试删除默认设置。","Warning")
            try:
                os.remove(SETTING_PATH)
                ShellPrinter("已删除配置文件")
            except FileNotFoundError:
                ShellPrinter("配置文件不存在")
            except Exception as Exp:
                ShellPrinter(r"删除配置文件失败!","Error")
                LogWriter(Summary="Cannot delete setting file", Raiser="Initializer", Critical=True, Detail=Exp)
            return Initializer()
        if SettingGetter("OiMode")==True and not (SettingGetter("LastVideoBV")=="BV0"):
            Oi=ShellGetter("检测到您已将自动机设为追番模式。是否自动下载自上次运行本程序起所有埃瑟斯上传的新录播？(y/n)",["y","n"],[True,False])
    return CookieReader(),Oi

def DurationParser (Second):
    RawHours=int(Second/3600)
    RawMinutes=int(Second/60)-60*int(Second/3600)
    RawSeconds=Second-60*int(Second/60)
    return f"{RawHours:02d}:{RawMinutes:02d}:{RawSeconds:02d}"     
def VideoListGetter(SessData):
    ShellPrinter("开始获取牢埃已上传的所有录播...")
    def BapiParser(bapi_return):
        archives_=bapi_return["archives"]
        video_info_list=[]
        for Archive in archives_:
            video_info=[Archive["bvid"],Archive["duration"],Archive["title"]]
            video_info_list.append(video_info)
        return video_info_list
    try:
        UserCredential=Credential(sessdata=SessData)
        series = channel_series.ChannelSeries(id_=4619502, credential=UserCredential)
        bapi_return = asyncio.run(series.get_videos())
    except Exception as Exc:
        ShellPrinter("获取失败！正在将错误信息写入日志文件...","Error")
        LogWriter(Summary="GetVideoListFailed",Raiser="VideoListGetter",Critical=True,Detail=f"Parameter={UserCredential}\n Exception={Exc}")
    return BapiParser(bapi_return)
def VideoSelector(video_infos):
    VideoCount = len(video_infos)
    ShellPrinter(f"已获取到录播列表，共有{VideoCount}个录播:","Info")
    print("\n{:<5}|{:<15}|{:<10}|{}".format("序号", "BV号", "录播时长", "录播标题"))
    print("-" * 70)
    for i in range(VideoCount):
        print("{:<5}|{:<15}|{:<10}|{}".format(i+1, video_infos[i][0], DurationParser(video_infos[i][1]),video_infos[i][2]))
    ShellPrinter(f"以上是获取到的录播列表，共有{VideoCount}个录播。请选择要下载的录播。","Info")
    while True:
        UserInput = input(f"请输入要下载的视频的序号(用空格分隔，例如: 1 3 5\n")
        try:
            selected_indices = [int(Index) for Index in UserInput.split()]

            invalid_indices = [Index for Index in selected_indices if Index < 1 or Index > VideoCount]
            if invalid_indices:
                ShellPrinter(f"错误: {', '.join(map(str, invalid_indices))} 不是有效编号，请输入1到{VideoCount}之间的编号","Warning")
                continue
            break
            
        except ValueError:
            ShellPrinter("错误: 请输入有效的数字编号。多个视频用空格分隔，例如: 1 3 5","Warning")
    
    selected_video_infos = []
    for Index in selected_indices:
        selected_video_infos.append(video_infos[Index-1])
    ShellPrinter(f"选择完毕，共选择了{len(selected_video_infos)}个视频",)
    return selected_video_infos

def UpdateGetter(video_infos):
    LastVideoBV=SettingGetter("LastVideoBV")
    for Index in range(len(video_infos)):
        if video_infos[Index][0]==LastVideoBV:
            ShellPrinter(f"牢埃已上传了{Index}个新视频")
            return video_infos[0:Index]
    ShellPrinter(f"追番失败，请手动选择要下载哪些视频。","Warning")
    LogWriter(Summary="Oi Failed", Raiser="UpdateGetter",Critical=False,Detail=f"LastVideoBV={LastVideoBV}  VideoInfos={video_infos}")
    return VideoSelector(video_infos)
            
def DownloadArgsSelector(Oi):
    def ArgsGetter():
        CONTENT=ShellGetter("下载完整视频输入v，仅音频输入a，AI字幕输入s。",["v","a","s"],["Video","Audio","Subtitle"])
        MULTITHREAD=ShellGetter("启用多线程下载输入y，不启用输入n。启用多线程下载会提升下载速度，但可能触发b站风控导致下载失败或暂时封禁",["y","n"],[True,False])
        ShellPrinter(r"请选择视频编码:H.264/AVC，文件体积最大，兼容性更好，画质更好。AV1，文件体积最小，性能需求较高。H.265/HEVC，除非有特殊理由否则不推荐")
        ShellPrinter(r"因为牢埃太糊，b站不提供AV1和H.265/HEVC转码。视频编码强制为H.264/AVC。无需选择")
        CODEC="H.264"
        DOWNLOADDIR=ShellGetter(r"输入下载文件夹（如D:\Asuse）","ValidDir")
        OIMODE=ShellGetter("是否启用追番模式？设为追番模式后，下次打开将自动下载所有新录播。输入y启用，输入n不启用",["y","n"],[True,False])
        try:
            SettingSetter("Content",CONTENT)
            SettingSetter("MultiThread",MULTITHREAD)
            SettingSetter("DownloadDir",DOWNLOADDIR)
            SettingSetter("Codec",CODEC)
            SettingSetter("OiMode",OIMODE)
            ShellPrinter("已记住设置","Info")
        except Exception as Exp:
            ShellPrinter("未能记忆相关设置，下次使用时可能需要重新输入","Warning")
            LogWriter(Summary="Falied to write settings", Raiser="ArgsGetter",Critical=False,Detail=str(Exp))
        return [CONTENT,MULTITHREAD,CODEC,DOWNLOADDIR]
        
    if Settingvalidator():
        CONTENT=SettingGetter("Content")
        DOWNLOADDIR=SettingGetter("DownloadDir")
        MULTITHREAD=SettingGetter("MultiThread")
        CODEC=SettingGetter("Codec")
        ShellPrinter("已读取到上次的设置:")
        match CONTENT:
            case "Video":
                ShellPrinter("下载完整视频")
            case "Audio":
                ShellPrinter("仅下载音频")
            case "Subtitle":
                ShellPrinter("下载AI字幕")
        match MULTITHREAD:
            case True:
                ShellPrinter("进行多线程下载")
            case False:
                ShellPrinter("不进行多线程下载") 
        match CODEC:
            case "H.264":
                ShellPrinter(r"优先使用H.264/AVC编码")
            case "H.265":
                ShellPrinter(r"优先使用H.265/HEVC编码")
            case "AV1":
                ShellPrinter(r"优先使用AV1编码")                
        ShellPrinter(f"下载目录:{os.path.abspath(DOWNLOADDIR)}")
        if Oi==False:
            if ShellGetter("按回车键使用当前设置，按e键重新设置",["","e"],[False, True]):
                ShellPrinter("您选择重新设置。")
                return ArgsGetter()
            else:
                return [CONTENT,MULTITHREAD,CODEC,DOWNLOADDIR]
        else:
            return [CONTENT,MULTITHREAD,CODEC,DOWNLOADDIR]
    else:
        ShellPrinter("未读取到上次的设置，请您输入下载设置：","Info")
        return ArgsGetter()
            
def BBDownArgsParser(Args_):
    Paras=" "
    match Args_[0]:
        case "Video":
            Paras+=""
        case "Audio":
            Paras+=r"--audio-only "
        case "Subtitle":
            Paras+=r"--sub-only --skip-ai false "
    match Args_[1]:
        case True:
            Paras+=r"-mt true "
        case False:
            Paras+=r"-mt false "
    match Args_[2]:
        case "H.264":
            Paras+="-e avc,av1,hevc "
        case "H.265":
            Paras+="-e hevc,avc,av1 "
        case "AV1":
            Paras+="-e av1,avc,hevc "
    Paras+=r"--work-dir "+Args_[3]
    return Paras
        
def Download(selected_video_infos, Paras):
    ShellPrinter("开始下载...")
    Tick=datetime.now()
    Tock="error"
    for Index in range(len(selected_video_infos)):
        ShellPrinter(f"正在下载{selected_video_infos[Index][2]}。")
        if Index>0 and not isinstance(Tock, str):
            UsedTime=Tock-Tick
            EstimatedTime=int(UsedTime.total_seconds()*selected_video_infos[Index][1]/selected_video_infos[Index-1][1])
            ShellPrinter(f"根据上个视频下载所用时间，预估本视频下载需{DurationParser(EstimatedTime)}")
        else:
            ShellPrinter("视频下载过程可能较为漫长，请您耐心等待...可通过检测网络流量确认下载是否仍在进行。")
        Tick = datetime.now() 
        try:
            subprocess.run("chcp 65001", shell=True, capture_output=True, text=True)

            Command = f"{BBDOWN_PATH} {selected_video_infos[Index][0]} {Paras}"
            
            process = subprocess.run(Command, 
                                   shell=True, 
                                   capture_output=True, 
                                   text=True, 
                                   encoding='utf-8')

            if process.returncode != 0:
                ShellPrinter(f"下载视频{selected_video_infos[Index][2]}时出错!","Error")
                LogWriter(Summary="BBDown Abnormal Exit Code", Raiser="BBDown", Critical=False, Detail=f"Command={Command}\n ReturnCode={process.returncode}\n stdout=\n{process.stdout}\n stderr=\n{process.stderr}")
                Tock="error"
            else:
                print(f"视频 {selected_video_infos[Index][2]} 下载完成！")
                Tock=datetime.now()
            
        except Exception as Exp:
            ShellPrinter(f"下载视频 {selected_video_infos[Index][2]}时出现未知错误！","Error")
            LogWriter(Summary="Unknown Error",Rasier="Download",Critical=False,Detail=f"Command={Command} \n Exp={Exp}")
            Tock="error"
        
        time.sleep(1)
    ShellPrinter("下载完成！","Success")

def main():
    ShellPrinter("======================埃瑟斯起居注自动机v1.2======================","Success")
    ShellPrinter("作者：三册 项目地址：https://github.com/Alkaid-C/Automated-QiJuZhu","Info")
    
    if not os.path.isfile(BBDOWN_PATH):
        ShellPrinter("注意！您没有下载依赖项，或将依赖项放置在了错误的地点。请在本程序所在目录创建bin文件夹，并在文件夹内放置BBDown.exe和ffmpeg.exe")
        os.system("PAUSE")
        sys.exit(1)
    SessData, Oi = Initializer()
    video_infos = VideoListGetter(SessData)
    if Oi:
        selected_video_infos = UpdateGetter(video_infos)
    else:
        selected_video_infos = VideoSelector(video_infos)
    Download(selected_video_infos,BBDownArgsParser(DownloadArgsSelector(Oi)))
    SettingSetter("LastVideoBV",video_infos[0][0])
    if LOG_HAPPENED:
        ShellPrinter("本次运行中可能出现错误。如果下载的结果与预期不一致，请将日志提交开发者。","Warning")
        SettingSetter("LastSuccess",False)

if __name__ == "__main__":
    main()
    os.system("PAUSE")
    sys.exit(0)
    
