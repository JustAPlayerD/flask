from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/button-click', methods=['POST'])
def button_click():
    data = request.json
    button_value = data.get('button')

    # 你可以根據按鈕的值執行對應動作
    if button_value == 'A':
        result = '你按下了 A，執行動作 1'
    elif button_value == 'B':
        result = '你按下了 B，執行動作 2'
    elif button_value == 'C':
        result = '你按下了 C，執行動作 3'
    else:
        result = '未知按鈕'

    return jsonify({'message': result})

if __name__ == '__main__':
    app.run(debug=True)
