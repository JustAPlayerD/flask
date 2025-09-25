import requests
from bs4 import BeautifulSoup
from flask import Flask, request, redirect, url_for, render_template
import re
import email.message
import smtplib
import os

# 取得render中的環境參數
getemailpass = os.environ.get("EMAIL_PASSWORD")
fromemail = os.environ.get("EMAIL_FROM")
toemail = os.environ.get("EMAIL_TO")
# 發票對獎網頁
BASE_URL = 'https://www.etax.nat.gov.tw'

app = Flask(__name__)
# 為裝飾器指定根URL，並且啟用methods中的GET和POST處理HTTP的請求
@app.route("/", methods=["GET", "POST"])
def index():
    # 執行取得匯率副程式取得匯率資料
    CRdata = currency_rate()
    try:
        # 抓發票資料
        data = get_latest_invoice_numbers()
    except Exception as e:
        data = []  # 如果爬資料失敗，至少保持空結構
    # data為dictionary，因此將資料拆開放入三個矩陣
    numbers = []
    periods = []
    redeem_periods = []
    for item in data:
        numbers.extend(item['numbers'])
        periods.append(item['period'])
        redeem_periods.append(item.get('redeem_period', ''))

    # -------- 安全處理：確保 numbers 至少有 8 個元素 --------
    # 你的模板裡至少會用到 invoice[0]~invoice[7]
    while len(numbers) < 20:
        numbers.append("")
    # -------- 安全處理：確保 periods/redeem_periods 對齊 --------
    while len(periods) < 1:
        periods.append("")
    while len(redeem_periods) < 1:
        redeem_periods.append("")
    reply = []
    # 控制html中回報寄信成功的方塊是否顯示
    success = False
    # 處理html傳入的表單
    if request.method == "POST":
        # 取得表單名稱
        action = request.form.get("action")
        # 回傳的為發票兌獎器的表單
        if action == "check":
            # 取得在表單內容
            input = request.form.get("inputinvoice")
            month = int(request.form.get("month"))
            # 執行對發票副程式，返回結果字串
            reply = invoice_check(input, numbers, month)
        # 回傳的為寄信的表單
        elif action == "comment":
            # 取得在表單內容
            name = request.form.get("Name")
            comment = request.form.get("Comment")
            # 執行寄信副程式
            send_email(name, comment)
            # 回報寄信成功的方塊顯示
            success = True
    # 回傳給html的資料
    return render_template("onepage.html",
    # 匯率資料
    crt = CRdata,
    # 各期發票號碼，各期月份字串，各期兌獎期間字串
    invoice = numbers,
    issue = periods,
    redeem = redeem_periods,
    # 寄信成功的方塊是否顯示，執行對發票副程式後返回的結果字串
    success=success, reply = reply)

# 對發票副程式
def invoice_check(number, invoice, month):
    # month為0~2，0為最新一期
    # invoice含有15組號碼，每期5組，最新一期在前面
    ns = invoice[0+5*month]
    n1 = invoice[1+5*month]
    n2 = [invoice[2+5*month], invoice[3+5*month], invoice[4+5*month]]
    # 判斷是否為8位數字
    if len(number) != 8:
        return '輸入錯誤，請重新輸入。'
    # 執行對獎
    try:
        if number == ns:
            return '中獎! 特別獎1000萬'
        elif number == n1:
            return '中獎! 特獎200萬'
        else:
            for i in n2:
                if number == i:
                    return '中獎! 頭獎20萬'
                elif number[-7:] == i[-7:]:
                    return '中獎! 二獎4萬'
                elif number[-6:] == i[-6:]:
                    return '中獎! 三獎1萬'
                elif number[-5:] == i[-5:]:
                    return '中獎! 四獎4千'
                elif number[-4:] == i[-4:]:
                    return '中獎! 五獎1千'
                elif number[-3:] == i[-3:]:
                    return '中獎! 六獎2百'
            return '沒中...'
    except:
        return '輸入錯誤，請重新輸入。'

# 取得中獎期別與網址副程式
def extract_invoice_links():
    url = f'{BASE_URL}/etw-main/ETW183W1/'
    response = requests.get(url, timeout=10)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')
    rows = soup.find_all('tr')
    target_numbers = ['2', '4', '6']
    links = []

    for row in rows:
        th = row.find('th', scope='row')
        if th and th.text.strip() in target_numbers:
            td = row.find('td')
            if td:
                a = td.find('a')
                if a and 'href' in a.attrs:
                    href = a['href']
                    if "ETW183W2" not in href:   # ⛔ 過濾掉清冊
                        continue

                    full_url = href if href.startswith('http') else BASE_URL + href
                    links.append(full_url)

    return links
# 新程式覆蓋
def extract_invoice_links():
    url = f'{BASE_URL}/etw-main/ETW183W1/'
    response = requests.get(url, timeout=10)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')
    rows = soup.find_all('tr')
    target_numbers = ['2', '4', '6']
    links = []

    for row in rows:
        th = row.find('th', scope='row')
        if th and th.text.strip() in target_numbers:
            td = row.find('td')
            if td:
                a = td.find('a')
                if a and 'href' in a.attrs:
                    href = a['href']
                    if "ETW183W2" not in href:   # ⛔ 過濾掉清冊
                        continue

                    full_url = href if href.startswith('http') else BASE_URL + href
                    links.append(full_url)

    return links
# 爬取各期網頁副程式
def extract_invoice_detail(url):
    # 擷取中獎號碼（紅字8碼）與兌獎期間
    response = requests.get(url)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')

    # 擷取8位數字
    # 找到<td>且屬性含有color : red、1.6em和bold。
    red_cells = soup.find_all('td', style=re.compile(r'color\s*:\s*red.*1\.6em.*bold'))
    numbers = []
    for td in red_cells:
        # 取得<td>其中的完整且為數字的8個字
        numbers += re.findall(r'\b\d{8}\b', td.get_text())
    # 只取前5組8位數字，避免取到不是發票號碼的數字
    numbers = list(dict.fromkeys(numbers))[:5]

    # 擷取兌獎期間
    redeem_text = ''
    # 找到<td>
    tds = soup.find_all('td')
    for td in tds:
        # 找到文字中含有'領獎期間'的<td>
        if '領獎期間' in td.text:
            # 取得文字
            text = td.get_text()
            # 找到'領獎期間自(某年某月某日)起至(某年某月某日)止'的字串
            # 分為兩組以()為一組將字串存起來
            match = re.search(r'領獎期間自(\d+年\d+月\d+日)起至(\d+年\d+月\d+日)止', text)
            if match:
                # 兩組內容為啟始時間和結束時間的字串
                redeem_text = f"{match.group(1)} ~ {match.group(2)}"
            break

    return numbers, redeem_text

def get_latest_invoice_numbers():
    links = extract_invoice_links()
    all_data = []

    for link in links:
        nums = fetch_invoice_numbers(link)
        all_data.append({
            "numbers": nums,
            "period": link.split("_")[-1],  # 從網址取期別 (11405 代表114年05-06月)
        })
    return all_data

# 寄信副程式
def send_email(name, comment):
    smtp_server = 'smtp.gmail.com'
    smtp_port = 465
    sender_email = fromemail
    app_password = getemailpass
    msg = email.message.EmailMessage()
    msg["From"] = sender_email
    msg["To"] = toemail
    msg["Subject"] = f"來自 {name} 的訊息"
    msg.set_content(f"留言內容：\n{comment}")
    sever = smtplib.SMTP_SSL(smtp_server, smtp_port)
    sever.login(sender_email, app_password)
    sever.send_message(msg)
    sever.quit()
    return 0

# 取得匯率副程式
def currency_rate():
    url = 'https://rate.bot.com.tw/xrt/flcsv/0/day'
    # 將匯率資料整理成一個二維的list，類似二維矩陣
    # 總計19種貨幣共19行，每行各列包含貨幣名稱和相關買入賣出等資料共21列
    try:
        rate = requests.get(url, timeout=10)
        rate.encoding = 'utf-8'
        rt = rate.text
        # 以'\n'為區隔區分出各列
        rts = rt.split('\n')
        cr_split = []
        # 第一列不取
        for i in range(1, len(rts)-1):
            # 每行各列以'，'為區隔
            cr_split.append(rts[i].split(','))
        return cr_split
    except requests.exceptions.RequestException as e:
        # 網站沒資料時回傳空資料，避免 Flask crash
        return [[""] * 12] * 19  # 保留至少12行19列空資料

if __name__ == "__main__":

    app.run(debug=True)




