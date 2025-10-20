from flask import Flask, jsonify
import paho.mqtt.client as mqtt
import threading

app = Flask(__name__)

# Variáveis para guardar dados
dados = {
    'temperatura': None,
    'hora': None,
    'status_portao': None
}

MQTT_BROKER = "50fc87af2076466ca85712922a9d1d9a.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USER = "cvm_admin"
MQTT_PASS = "Junior10@"

def on_connect(client, userdata, flags, rc):
    print("Conectado com código:", rc)
    client.subscribe("cvmatavelli/temperatura")
    client.subscribe("cvmatavelli/status")

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode()
    print(f"Recebido: {topic} -> {payload}")

    if topic == "cvmatavelli/temperatura":
        import json
        try:
            data = json.loads(payload)
            dados['temperatura'] = data.get('temperatura')
            dados['hora'] = data.get('hora')
        except Exception as e:
            print("Erro no JSON:", e)
    elif topic == "cvmatavelli/status":
        dados['status_portao'] = payload

mqtt_client = mqtt.Client()

mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)
mqtt_client.tls_set()  # Usa TLS
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

def mqtt_loop():
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_forever()

# Iniciar o loop MQTT numa thread separada para não travar o Flask
threading.Thread(target=mqtt_loop, daemon=True).start()

@app.route('/')
def home():
    return f"""
    <h1>Status do Portão: {dados['status_portao']}</h1>
    <h2>Temperatura: {dados['temperatura']} °C</h2>
    <p>Última atualização: {dados['hora']}</p>
    """

@app.route('/api/status')
def api_status():
    return jsonify(dados)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
