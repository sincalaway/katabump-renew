#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import subprocess
import requests
from seleniumbase import SB

# 从环境变量获取账号密码和 TG 配置
EMAIL        = os.environ.get("KATABUMP_EMAIL") or ""
PASSWORD     = os.environ.get("KATABUMP_PASSWORD") or ""
TG_CHAT_ID   = os.environ.get("TG_CHAT_ID") or ""
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN") or ""

BASE_URL = "https://dashboard.katabump.com"

# Telegram 推送模块
def send_tg_message(status_icon, status_text, time_left=""):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        print("ℹ️ 未配置 TG_BOT_TOKEN 或 TG_CHAT_ID，跳过 Telegram 推送。")
        return

    local_time = time.gmtime(time.time() + 8 * 3600)
    current_time_str = time.strftime("%Y-%m-%d %H:%M:%S", local_time)

    if '@' in EMAIL:
        name, domain = EMAIL.split('@', 1)
        masked_email = f"{name[:2]}****{name[-2:]}@{domain}" if len(name) > 4 else f"{name}@{domain}"
    else:
        masked_email = EMAIL[:2] + '****'

    text = f"🇫🇷 katabump 续期通知\n\n{status_icon} {status_text}\n👤 续期账户: {masked_email}\n⏱️ 时间: {current_time_str}"
    try:
        r = requests.post(f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage", 
                         json={"chat_id": TG_CHAT_ID, "text": text}, timeout=10)
        if r.status_code == 200:
            print("📩 Telegram 通知发送成功！")
        else:
            print(f"⚠️ Telegram 发送失败: {r.text}")
    except Exception as e:
        print(f"⚠️ Telegram 异常: {e}")

# 页面注入脚本
_EXPAND_JS = """
(function() {
    var ts = document.querySelector('input[name="cf-turnstile-response"]');
    if (!ts) return 'no-turnstile';
    var el = ts;
    for (var i = 0; i < 20; i++) {
        el = el.parentElement;
        if (!el) break;
        var s = window.getComputedStyle(el);
        if (s.overflow === 'hidden' || s.overflowX === 'hidden' || s.overflowY === 'hidden')
            el.style.overflow = 'visible';
        el.style.minWidth = 'max-content';
    }
    document.querySelectorAll('iframe').forEach(function(f){
        if (f.src && f.src.includes('challenges.cloudflare.com')) {
            f.style.width = '320px'; f.style.height = '80px';
            f.style.minWidth = '320px';
            f.style.visibility = 'visible'; f.style.opacity = '1';
        }
    });
    return 'done';
})()
"""

_EXISTS_JS = """(function(){ return document.querySelector('input[name="cf-turnstile-response"]') !== null; })()"""
_SOLVED_JS = """(function(){ var i = document.querySelector('input[name="cf-turnstile-response"]'); return !!(i && i.value && i.value.length > 20); })()"""
_WININFO_JS = """(function(){ return { sx: window.screenX || 0, sy: window.screenY || 0, oh: window.outerHeight, ih: window.innerHeight }; })()"""

# ALTCHA 相关 JS
_ALTCHA_EXPAND_JS = """
(function() {
    var modal = document.querySelector('div.modal.show') || document;
    var iframes = modal.querySelectorAll('iframe');
    for (var i = 0; i < iframes.length; i++) {
        var r = iframes[i].getBoundingClientRect();
        if (r.width > 0 && r.height > 0) {
            iframes[i].style.width = '300px'; iframes[i].style.height = '150px';
            iframes[i].style.minWidth = '300px'; iframes[i].style.minHeight = '150px';
            iframes[i].style.visibility = 'visible'; iframes[i].style.opacity = '1';
            var el = iframes[i];
            for (var j = 0; j < 10; j++) {
                el = el.parentElement;
                if (!el) break;
                el.style.overflow = 'visible';
            }
            var r2 = iframes[i].getBoundingClientRect();
            return { cx: Math.round(r2.x + 30), cy: Math.round(r2.y + r2.height / 2) };
        }
    }
    return null;
})()
"""

_ALTCHA_SOLVED_JS = """
(function(){
    var modal = document.querySelector('div.modal.show') || document;
    var inputs = modal.querySelectorAll('input[type="hidden"]');
    for (var i = 0; i < inputs.length; i++) {
        var n = (inputs[i].name || '').toLowerCase();
        if ((n.includes('altcha') || n.includes('captcha')) && inputs[i].value && inputs[i].value.length > 20) return true;
    }
    var cbs = modal.querySelectorAll('input[type="checkbox"]');
    for (var j = 0; j < cbs.length; j++) {
        if (cbs[j].disabled) return true;
    }
    var w = modal.querySelector('[data-state="verified"],.altcha--verified,.altcha-verified');
    if (w) return true;
    return false;
})()
"""

def js_fill_input(sb, selector: str, text: str):
    safe_text = text.replace('\\', '\\\\').replace('"', '\\"')
    sb.execute_script(f"""
    (function(){{ 
        var el = document.querySelector('{selector}');
        if (!el) return;
        var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
        if (nativeInputValueSetter) nativeInputValueSetter.call(el, "{safe_text}");
        else el.value = "{safe_text}";
        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
    }})()
    """)

def _activate_window():
    for cls in ["chrome", "chromium", "Chromium", "Chrome", "google-chrome"]:
        try:
            r = subprocess.run(["xdotool", "search", "--onlyvisible", "--class", cls], capture_output=True, text=True, timeout=3)
            wids = [w for w in r.stdout.strip().split("\n") if w.strip()]
            if wids:
                subprocess.run(["xdotool", "windowactivate", "--sync", wids[0]], timeout=3, stderr=subprocess.DEVNULL)
                time.sleep(0.2)
                return
        except: pass
    try:
        subprocess.run(["xdotool", "getactivewindow", "windowactivate"], timeout=3, stderr=subprocess.DEVNULL)
    except: pass

def _xdotool_click(x: int, y: int):
    _activate_window()
    try:
        subprocess.run(["xdotool", "mousemove", "--sync", str(x), str(y)], timeout=3, stderr=subprocess.DEVNULL)
        time.sleep(0.15)
        subprocess.run(["xdotool", "click", "1"], timeout=2, stderr=subprocess.DEVNULL)
    except:
        os.system(f"xdotool mousemove {x} {y} click 1 2>/dev/null")

# ==================== 加强版 Turnstile 处理 ====================
def handle_turnstile(sb) -> bool:
    print("🔍 处理 Cloudflare Turnstile 验证...")
    time.sleep(4)

    if sb.execute_script(_SOLVED_JS):
        print("✅ 已静默通过")
        return True

    for _ in range(5):
        try: sb.execute_script(_EXPAND_JS)
        except: pass
        time.sleep(1)

    for attempt in range(10):
        if sb.execute_script(_SOLVED_JS):
            print(f"✅ Turnstile 通过（第 {attempt+1} 次）")
            return True

        print(f"🖱️ 第 {attempt + 1} 次调用 uc_gui_click_captcha...")
        try:
            sb.uc_gui_click_captcha()
        except Exception as e:
            print(f"⚠️ 调用异常: {e}")

        for _ in range(25):
            time.sleep(0.4)
            if sb.execute_script(_SOLVED_JS):
                print(f"✅ Turnstile 通过")
                return True

        print(f"⚠️ 第 {attempt + 1} 次未通过，重试...")
        time.sleep(2)

    print("  ❌ Turnstile 10 次均失败")
    sb.save_screenshot("turnstile_fail_final.png")
    return False

# 账户登录
def login(sb) -> bool:
    print(f"🌐 打开登录页面: {BASE_URL}/auth/login")
    sb.uc_open_with_reconnect(BASE_URL + "/auth/login", reconnect_time=10)
    time.sleep(6)

    print("⏳ 等待 Cloudflare 验证通过...")
    for i in range(30):
        page_src = sb.get_page_source() or ""
        if 'input[name="email"]' in page_src.lower():
            print(f"✅ Cloudflare 验证已通过（{i+1}s）")
            break
        time.sleep(1)

    try:
        sb.wait_for_element('input[name="email"]', timeout=20)
    except:
        print("❌ 页面未加载出登录表单")
        sb.save_screenshot("login_load_fail.png")
        return False

    print("📧 填写邮箱...")
    js_fill_input(sb, 'input[name="email"]', EMAIL)
    time.sleep(0.5)
    print("🔑 填写密码...")
    js_fill_input(sb, 'input[name="password"]', PASSWORD)
    time.sleep(1)

    print("⏳ 等待 Turnstile 验证框出现...")
    ts_found = False
    for i in range(12):
        if sb.execute_script(_EXISTS_JS):
            ts_found = True
            print(f"✅ 检测到 Turnstile（{i+1}s）")
            break
        time.sleep(1)

    if ts_found:
        if not handle_turnstile(sb):
            print("❌ 登录界面的 Turnstile 验证失败")
            sb.save_screenshot("login_turnstile_fail.png")
            return False

    print("🖱️ 提交登录...")
    sb.press_keys('input[name="password"]', '\n')
    time.sleep(8)

    cur_url = sb.get_current_url().split('?')[0].lower()
    if cur_url.startswith(f"{BASE_URL}/dashboard"):
        print("✅ 登录成功！")
        return True

    print(f"❌ 登录失败 (URL: {sb.get_current_url()})")
    sb.save_screenshot("login_failed.png")
    return False

# ===== 自动续期流程（保留你原来的完整逻辑）=====
def _read_alert(sb):
    try:
        el = sb.find_element("div.alert", timeout=4)
        return (el.text or "").strip()
    except:
        return ""

def _goto_server_detail(sb) -> bool:
    print("\n🖥️  正在进入服务器续期页...")
    time.sleep(5)
    alert_text = _read_alert(sb)
    if alert_text and "can't renew" in alert_text.lower():
        print(f"ℹ️  页面顶部提示: {alert_text}")
        send_tg_message("ℹ️", "⚠️ 未到续期时间", alert_text)
        return False

    selectors = ['a[href*="/servers/edit?id="]', 'td a[href*="/servers/edit"]', 'table a[href*="/servers/edit"]', 'table td a']
    see_link = None
    for sel in selectors:
        try:
            see_link = sb.find_element(sel, timeout=8)
            break
        except: continue

    if see_link is None:
        try:
            for a in sb.find_elements("a"):
                if (a.text or "").strip().lower() == "see":
                    see_link = a
                    break
        except: pass

    if see_link is None:
        sb.save_screenshot("servers_page_fail.png")
        return False

    see_link.click()
    time.sleep(5)
    return True

def _open_renew_modal(sb) -> bool:
    print("\n🔄 查找 Renew 按钮...")
    try:
        renew_btn = sb.find_element('button[data-bs-target="#renew-modal"]', timeout=10)
    except:
        try:
            renew_btn = sb.find_element('button.btn.btn-outline-primary', timeout=5)
        except:
            print("  ❌ 未找到 Renew 按钮")
            return False

    sb.execute_script("var btn = document.querySelector('button[data-bs-target=\"#renew-modal\"]') || document.querySelector('button.btn.btn-outline-primary'); if(btn) btn.scrollIntoView({behavior:'smooth',block:'center'});")
    time.sleep(0.8)
    renew_btn.click()
    time.sleep(3)
    try:
        sb.find_element('div.modal.show', timeout=5)
        return True
    except:
        return False

def _solve_altcha(sb) -> bool:
    print("\n🔐 处理 ALTCHA 人机验证...")
    time.sleep(2)
    if sb.execute_script(_ALTCHA_SOLVED_JS):
        print("✅ ALTCHA 已自动通过")
        return True

    coords = None
    try:
        coords = sb.execute_script(_ALTCHA_EXPAND_JS)
    except: pass

    for attempt in range(3):
        if sb.execute_script(_ALTCHA_SOLVED_JS):
            print(f"✅ ALTCHA 验证通过（第 {attempt + 1} 轮）")
            return True

        if coords:
            try:
                wi = sb.execute_script(_WININFO_JS)
                bar = wi["oh"] - wi["ih"]
                ax = coords["cx"] + wi["sx"]
                ay = coords["cy"] + wi["sy"] + bar
                _xdotool_click(ax, ay)
            except: pass

        sb.execute_script("""
            (function(){
                var modal = document.querySelector('div.modal.show');
                if (!modal) return;
                var iframes = modal.querySelectorAll('iframe');
                for (var i = 0; i < iframes.length; i++) {
                    iframes[i].click();
                }
                var cbs = modal.querySelectorAll('input[type="checkbox"]');
                for (var k = 0; k < cbs.length; k++) {
                    if (!cbs[k].disabled) cbs[k].click();
                }
            })()
        """)

        for _ in range(8):
            time.sleep(1)
            if sb.execute_script(_ALTCHA_SOLVED_JS):
                return True

    print("  ❌ ALTCHA 3 轮均失败")
    return False

def _submit_renew(sb):
    print("🖱️ 点击 Renew 提交...")
    try:
        submit = sb.find_element('div.modal.show button.btn-primary', timeout=5)
        submit.click()
    except:
        sb.execute_script("var m = document.querySelector('div.modal.show'); if(m){ var bs = m.querySelectorAll('button'); for(var i=0;i<bs.length;i++) if(/renew/i.test(bs[i].textContent)) bs[i].click(); }")
    time.sleep(3)

def _check_renew_result(sb):
    print("\n📋 检查续期结果...")
    alert_text = _read_alert(sb)
    if not alert_text:
        time.sleep(3)
        alert_text = _read_alert(sb)
    if alert_text:
        low = alert_text.lower()
        if "can't renew" in low:
            send_tg_message("⏳", "未到续期时间", alert_text)
        elif any(k in low for k in ["renewed", "success", "extended"]):
            send_tg_message("✅", "续期成功", alert_text)
        else:
            send_tg_message("ℹ️", "续期操作已执行", alert_text)
    else:
        send_tg_message("ℹ️", "续期操作已执行", "未检测到明确提示")

def renew_server(sb):
    print("\n" + "#" * 25)
    print("  开始自动续期流程")
    print("#" * 25)

    if not _goto_server_detail(sb): return
    if not _open_renew_modal(sb): return

    altcha_ok = _solve_altcha(sb)
    if not altcha_ok:
        print("⚠️ ALTCHA 未完全通过，仍尝试提交...")

    _submit_renew(sb)
    _check_renew_result(sb)

# 主函数
def main():
    print("#" * 25)
    print("   katabump 自动登录续期")
    print("#" * 25)

    IS_PROXY = os.environ.get("IS_PROXY", "false").lower() == "true"
    proxy_str = os.environ.get("PROXY_SERVER", "").strip() or "socks5://127.0.0.1:1080"
    sb_kwargs = {"uc": True, "headless": False}

    if IS_PROXY:
        print(f"🔗 挂载代理: {proxy_str}")
        sb_kwargs["proxy"] = proxy_str
    else:
        print("🌐 未使用代理，直连访问")

    with SB(**sb_kwargs) as sb:
        try:
            sb.open("https://api.ip.sb/ip")
            print(f"📍 当前出口IP: {sb.get_text('body')}")
        except: pass

        if login(sb):
            renew_server(sb)
        else:
            print("\n❌ 登录失败，终止后续续期操作。")
            send_tg_message("❌", "登录失败", "Turnstile验证失败")

if __name__ == "__main__":
    main()
