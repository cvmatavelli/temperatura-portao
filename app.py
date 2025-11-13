from flask import Flask, jsonify, render_template_string, request, redirect, url_for, session
import paho.mqtt.client as mqtt
import threading
import json
from collections import deque

app = Flask(__name__)
app.secret_key = "cmv"  # troque por algo aleatório e forte!
LOGIN_PASSWORD = "cvm10@"  # senha para acesso (troque também!)

# Dados para guardar estado e histórico (últimas 10 temperaturas)
dados = {
    'temperatura': None,
    'hora': None,
    'status_portao': None,
    'historico_temperaturas': deque(maxlen=10)
}

MQTT_BROKER = "50fc87af2076466ca85712922a9d1d9a.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USER = "cvm_admin"
MQTT_PASS = "Junior10@"

mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    print("Conectado com código:", rc)
    client.subscribe("cvmatavelli/temperatura")
    client.subscribe("cvmatavelli/status")

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode()
    print(f"Recebido: {topic} -> {payload}")

    if topic == "cvmatavelli/temperatura":
        try:
            data = json.loads(payload)
            temperatura = data.get('temperatura')
            hora = data.get('hora')
            dados['temperatura'] = temperatura
            dados['hora'] = hora
            if temperatura is not None and hora is not None:
                dados['historico_temperaturas'].appendleft({'temperatura': temperatura, 'hora': hora})
        except Exception as e:
            print("Erro no JSON:", e)
    elif topic == "cvmatavelli/status":
        dados['status_portao'] = payload

mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)
mqtt_client.tls_set()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

def mqtt_loop():
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_forever()

threading.Thread(target=mqtt_loop, daemon=True).start()

# ==========================
#     AUTENTICAÇÃO
# ==========================
@app.before_request
def require_login():
    if request.endpoint not in ('login', 'static'):
        if not session.get('logged_in'):
            return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        senha = request.form.get('senha')
        if senha == LOGIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('home'))
        else:
            return render_template_string("""
                <div style='text-align:center;margin-top:20vh;font-family:sans-serif;'>
                    <h2 style='color:red;'>Senha incorreta!</h2>
                    <form method="post">
                        <input type="password" name="senha" placeholder="Digite a senha">
                        <button type="submit">Entrar</button>
                    </form>
                </div>
            """)
    return render_template_string("""
        <div style='display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;'>
            <h2>🔒 Acesso Restrito</h2>
            <form method="post">
                <input type="password" name="senha" placeholder="Digite a senha" style="padding:10px;margin:5px;font-size:1rem;">
                <button type="submit" style="padding:10px 20px;background:#2e7d32;color:white;border:none;border-radius:5px;">Entrar</button>
            </form>
        </div>
    """)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==========================
#    INTERFACE PRINCIPAL
# ==========================
HTML_TEMPLATE = """ (seu HTML completo aqui, igual ao atual) """

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE,
                                  status_portao=dados['status_portao'],
                                  temperatura=dados['temperatura'],
                                  hora=dados['hora'],
                                  historico=list(dados['historico_temperaturas']))

@app.route('/toggle', methods=['POST'])
def toggle_portao():
    if mqtt_client.is_connected():
        mqtt_client.publish("cvmatavelli/comando", "toggle")
        print("Comando toggle enviado ao MQTT")
    else:
        print("MQTT não conectado - comando não enviado")
    if dados['status_portao']:
        if dados['status_portao'].lower() == 'aberto':
            dados['status_portao'] = 'Fechado'
        else:
            dados['status_portao'] = 'Aberto'
    else:
        dados['status_portao'] = 'Aberto'
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

