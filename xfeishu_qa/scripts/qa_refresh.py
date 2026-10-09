# -*- coding: utf-8 -*-
"""用 refresh_token 刷新 user_access_token，失败则提示重新授权。"""
import winreg, json, io, sys, os, urllib.request, urllib.error

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
TMP = os.environ.get("FEISHU_QA_HOME", r"D:\TRAE\claude_work\feishu_qa")
os.makedirs(TMP, exist_ok=True)
TF = os.path.join(TMP, "user_token.json")

k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment")
APP_ID, _ = winreg.QueryValueEx(k, "APP_ID")
APP_SECRET, _ = winreg.QueryValueEx(k, "APP_SECRET")

old = json.load(open(TF))
req = urllib.request.Request("https://accounts.feishu.cn/oauth/v3/token",
    data=json.dumps({"grant_type": "refresh_token", "client_id": APP_ID,
                     "client_secret": APP_SECRET,
                     "refresh_token": old["refresh_token"]}).encode(),
    headers={"Content-Type": "application/json; charset=utf-8"})
try:
    r = json.loads(urllib.request.urlopen(req, timeout=30).read())
except urllib.error.HTTPError as e:
    r = {"_http": e.code, "_body": e.read().decode("utf-8", "replace")}

if r.get("code") == 0:
    json.dump(r, open(TF, "w"), ensure_ascii=False)
    print("[ok] token 已刷新  expires_in:", r.get("expires_in"), " scope:", r.get("scope"))
else:
    print("[fail] 刷新失败:", json.dumps(r, ensure_ascii=False)[:800])
    print("       需重新跑 feishu_oauth_qa.py 走浏览器授权")
