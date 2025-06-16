import requests
from bs4 import BeautifulSoup
from flask import Flask, request, redirect, url_for, render_template
import re
import email.message
import smtplib
import os

getemailpass = os.environ.get("EMAIL_PASSWORD")
fromemail = os.environ.get("EMAIL_FROM")
toemail = os.environ.get("EMAIL_TO")

BASE_URL = 'https://www.etax.nat.gov.tw'

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():

    CRdata = currency_rate()

    success = False

    if request.method == "POST":
        name = request.form.get("Name")
        comment = request.form.get("Comment")
        send_email(name, comment)
        success = True

    data = get_latest_invoice_numbers()
    numbers = []
    periods = []
    redeem_periods = []

    for item in data:
        numbers.extend(item['numbers'])
        periods.append(item['period'])
        redeem_periods.append(item.get('redeem_period', ''))

    numbers += [''] * (15 - len(numbers)) # 3期總共15組號碼
    periods += [''] * (3 - len(periods)) # 3期年和月份
    redeem_periods += [''] * (3 - len(redeem_periods)) # 3期兌換期間字串

    return render_template("onepage.html",
    crt1 = CRdata[1].split(','), crt2 = CRdata[2].split(','), crt3 = CRdata[3].split(','),
    crt4 = CRdata[4].split(','), crt5 = CRdata[5].split(','), crt6 = CRdata[6].split(','),
    crt7 = CRdata[7].split(','), crt8 = CRdata[8].split(','), crt9 = CRdata[9].split(','),
    crt10 = CRdata[10].split(','), crt11 = CRdata[11].split(','), crt12 = CRdata[12].split(','),
    crt13 = CRdata[13].split(','), crt14 = CRdata[14].split(','), crt15 = CRdata[15].split(','),
    crt16 = CRdata[16].split(','), crt17 = CRdata[17].split(','), crt18 = CRdata[18].split(','),
    crt19 = CRdata[19].split(','),
    invoice11 = numbers[0], invoice12 = numbers[1],
    invoice13 = numbers[2], invoice14 = numbers[3], invoice15 = numbers[4],
    invoice21 = numbers[5], invoice22 = numbers[6],
    invoice23 = numbers[7], invoice24 = numbers[8], invoice25 = numbers[9],
    invoice31 = numbers[10], invoice32 = numbers[11],
    invoice33 = numbers[12], invoice34 = numbers[13], invoice35 = numbers[14],
    issue1 = periods[0], issue2 = periods[1], issue3 = periods[2],
    redeem1 = redeem_periods[0], redeem2 = redeem_periods[1], redeem3 = redeem_periods[2],
    success=success)

def invoice_check():
    url = 'https://invoice.etax.nat.gov.tw/'
    web = requests.get(url, timeout=10)
    web.raise_for_status()
    web.encoding = 'utf-8'
    soup = BeautifulSoup(web.text, "html.parser")
    td = soup.select('.container-fluid')[0].select('.etw-tbiggest')
    ns = td[0].getText()
    n1 = td[1].getText()
    n2 = [td[2].getText()[-8:], td[3].getText()[-8:], td[4].getText()[-8:]]
    return ns,n1,n2

def extract_invoice_links():
    """擷取表單 2、4、6 的中獎期別與網址"""
    url = f'{BASE_URL}/etw-main/ETW183W1/'
    response = requests.get(url)
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
                    text = a.get_text(strip=True)
                    full_url = href if href.startswith('http') else BASE_URL + href
                    links.append((text, full_url))
    return links

def extract_invoice_detail(url):
    """擷取中獎號碼（紅字8碼）與兌獎期間"""
    response = requests.get(url)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')

    # 擷取紅色 8 碼號碼
    red_cells = soup.find_all('td', style=re.compile(r'color\s*:\s*red.*1\.6em.*bold'))
    numbers = []
    for td in red_cells:
        numbers += re.findall(r'\b\d{8}\b', td.get_text())
    numbers = list(dict.fromkeys(numbers))[:5]  # 去重、取前 5 組

    # 擷取兌獎期間
    redeem_text = ''
    tds = soup.find_all('td')
    for td in tds:
        if '領獎期間' in td.text:
            text = td.get_text()
            match = re.search(r'領獎期間自(\d+年\d+月\d+日)起至(\d+年\d+月\d+日)止', text)
            if match:
                redeem_text = f"{match.group(1)} ~ {match.group(2)}"
            break

    return numbers, redeem_text

def get_latest_invoice_numbers():
    """主功能：擷取表單2, 4, 6的期別與中獎號碼"""
    result = []
    links = extract_invoice_links()
    for label, link in links:
        numbers, redeem_period = extract_invoice_detail(link)
        result.append({
            'period': label,
            'numbers': numbers,
            'redeem_period': redeem_period
        })
    return result

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

def currency_rate():
    url = 'https://rate.b0ot.com.tw/xrt/flcsv/0/day'
    url2 = 'https://rate.bot.com.tw/xrt?Lang=zh-TW'
    try:
        rate = requests.get(url, timeout=10)
        rate.encoding = 'utf-8'
        rt = rate.text
        rts = rt.split('\n')
        return rts
    except requests.exceptions.RequestException:
        try:
            html = requests.get(url2, timeout=10)
            soup = BeautifulSoup(html.text, 'html.parser')
            rows = soup.select('table.table tbody tr')
            results = ["幣別,0,現金買入,0,0,0,0,0,0,0,0,0,現金賣出"]  # 模擬CSV表頭

            for row in rows:
                tds = row.find_all('td')
                if len(tds) >= 5:
                    currency_name = tds[0].find('div', class_='visible-phone').text.strip()
                    cash_buy = tds[1].text.strip()
                    cash_sell = tds[2].text.strip()
                    results.append(f"{currency_name},0,{cash_buy},0,0,0,0,0,0,0,0,0,{cash_sell}")
            return results
        except requests.exceptions.RequestException as e:
            # 回傳預設資料，避免 Flask crash
            return [""] * 20  # 保留至少20列空資料

if __name__ == "__main__":
    app.run(debug=True)