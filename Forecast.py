# -*- coding: utf-8 -*-
import os
import re
import sys
import glob
import json
import time
import subprocess
from datetime import datetime,timedelta,timezone
from requests_oauthlib import OAuth1Session
os.chdir(os.path.dirname(os.path.abspath(__file__)))


Settings={
    "channel" : "PARTY",
    "id" : "12345678",
    "name" : "YourCharacterName",
    "symbol" : "0123456789abcdef0123456789abcdef",
    "offset" : "+00:13:22", # "[+-]H:M:S" gl->jp offset
    "timezone" : "+09:00" # "[+-]H:M"  local timezone
}
Wait_time = 5 #s  FileCheck interval
PSO2_Dir = '.\\PHANTASYSTARONLINE2_NA'

tweet_text = "Thunderstorm Detected\n\nDetected Time(JST): {DetectTime}\nJP Offset Time(JST): {OffsetTime} ±5s\n#ngs #pso2ngs"

CONSUMER_KEY = "*************************"
CONSUMER_SECRET = "**************************************************"
ACCESS_TOKEN = "**************************************************"
ACCESS_TOKEN_SECRET = "*********************************************"
twitter = OAuth1Session(CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
twitter_api_url = "https://api.twitter.com/1.1/statuses/update.json"
DEBUG=False

if DEBUG:
    print("DEBUG = True")
    tweet_text = "Test tweet\n\n" + tweet_text
#end if

def Tweet(txt,count):
    try:
        twitter = OAuth1Session(CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
        params = {"status" : txt}
        res = twitter.post(twitter_api_url, params = params)
        if res.status_code == 200:
            print("Tweet Success.")
        else:
            print("Tweet Failed. : %d"% res.status_code)
            if count+1 < 3:
                print("Retrying")
                time.sleep((count+1)*2)
                Tweet(txt,count+1)
            #end if
        #end if
    except Exception as e:
        print(e)
        print("Tweet Failed. : %d"% res.status_code)
        if count+1 < 3:
            print("Retrying")
            time.sleep((count+1)*2)
            Tweet(txt,count+1)
        #end if
    #end try
#end Tweet

def CheckProcess():
    try:
        wmi_out = subprocess.check_output(["wmic", "process", "list", "full", "/format:list"])
    except subprocess.CalledProcessError as e:
        print("Call to `wmic` failed: {}".format(e))
        exit(1)
    #end try
    wmi_entries = []
    for task in wmi_out.strip().split("\r\r\n\r\r\n".encode()):
        wmi_entries.append(dict(e.split("=".encode(), 1) for e in task.strip().split("\r\r\n".encode())))
    #end for
    return len([row[b'Name'] for row in wmi_entries if row[b'Name'].startswith(b"pso2.exe")])>0 or DEBUG
#end CheckProcess

def OffsetTime(date):
    buf = date
    if Settings["offset"][0:1] == "+":
        buf = buf + timedelta(hours=int(Settings["offset"][1:3]),minutes=int(Settings["offset"][4:6]),seconds=int(Settings["offset"][7:9]))
    elif Settings["offset"][0:1] == "-":
        buf = buf - timedelta(hours=int(Settings["offset"][1:3]),minutes=int(Settings["offset"][4:6]),seconds=int(Settings["offset"][7:9]))
    else:
        buf = buf + timedelta(hours=int(Settings["offset"][0:2]),minutes=int(Settings["offset"][3:5]),seconds=int(Settings["offset"][6:8]))
    #end if
    return buf
#end OffsetTime

def TimeParse(date):
    buf = datetime(
        year=int(date[0:4]),month=int(date[5:7]),day=int(date[8:10]),
        hour=int(date[11:13]),minute=int(date[14:16]),second=int(date[17:20])
    )
    jp = timedelta(hours=9,minutes=0)
    if Settings["timezone"][0:1] == "+":
        tz = timedelta(hours=int(Settings["timezone"][1:3]),minutes=int(Settings["timezone"][4:6]))
        buf = buf - tz + jp
    elif Settings["timezone"][0:1] == "-":
        tz = timedelta(hours=int(Settings["timezone"][1:3]),minutes=int(Settings["timezone"][4:6]))
        buf = buf + tz + jp
    else:
        tz = timedelta(hours=int(Settings["timezone"][0:2]),minutes=int(Settings["timezone"][3:5]))
        buf = buf - tz + jp
    #end if
    return buf
#end TimeParse

match_pattern = '^\d{4}(\-\d{2}){2}T(\d{2}:){2}\d{2}\t\d+\t('+Settings["channel"]+')\t('+Settings["id"]+')\t('+Settings["name"]+')\t('+Settings["symbol"]+')$'
currentPath = ""
currentDetectCount = 0
currentFileSize = 0
init = False
print("Start")
while True:
    try:
        file_list=sorted(glob.glob(PSO2_Dir+'\\log_ngs\\SymbolChatLog*.txt'), key=lambda f: os.stat(f).st_mtime, reverse=True)
        if len(file_list)>0:
            path = file_list[0]
            size = os.path.getsize(path)
            if currentPath != path:
                currentPath = path
                currentDetectCount = 0
                currentFileSize = 0
            #end if
            if currentFileSize != size:
                currentFileSize = size
                with open(path, encoding='utf-16') as f:
                    lines = f.readlines()
                lines_strip = [line.strip() for line in lines]
                Detect = [line for line in lines_strip if re.match(match_pattern, line)]
                c = len(Detect)
                if not init:
                    init = True
                    currentDetectCount = c
                #end if
                if currentDetectCount != c:
                    if currentDetectCount < c:
                        #something process
                        
                        result = Detect[-1].split("\t")
                        # print(result)
                        DetectTime = TimeParse(result[0])
                        OffsetDetectTime = OffsetTime(DetectTime)
                        print('Detected : ' + DetectTime.strftime('%Y-%m-%d %H:%M:%S'))
                        if DEBUG == True:
                            print('Offset : ' + OffsetDetectTime.strftime('%Y-%m-%d %H:%M:%S'))
                        #end if
                        Tweet(tweet_text.format(DetectTime=DetectTime.strftime('%Y-%m-%d %H:%M:%S'),OffsetTime=OffsetDetectTime.strftime('%Y-%m-%d %H:%M:%S')),0)
                    #end if
                    currentDetectCount = c
                #end if
            #end if
        #end if
        if not CheckProcess():
            print("<pso2.exe> is not running")
            break
        #end if
        time.sleep(Wait_time)
    except KeyboardInterrupt:
        print('end')
        break
    except Exception as e:
        print(e)
    #end try
#end while
print("end process")
