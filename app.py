from flask import Flask, jsonify, render_template_string, request, redirect, url_for
import paho.mqtt.client as mqtt
import threading
import json
from collections import deque

app = Flask(__name__)

# Dados para guardar estado e histórico (últimas 10 temperaturas)
dados = {
    'temperatura': None,
    'hora': None,
    'status_portao': None,
    'historico_temperaturas': deque(maxlen=10)  # lista limitada a 10 itens
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

# Página HTML com template embutido e estilo
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Centro Veterinário Matavelli</title>
<style>
  body {
    font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
    margin: 0; background: #f0f4f7; color: #333;
  }
  header {
    background: #2e7d32;
    color: white;
    display: flex;
    align-items: center;
    padding: 10px 20px;
  }
  header img {
    height: 40px;
    margin-right: 15px;
  }
  header h1 {
    font-size: 1.8rem;
    margin: 0;
  }
  main {
    max-width: 700px;
    margin: 30px auto;
    background: white;
    padding: 25px 30px;
    border-radius: 10px;
    box-shadow: 0 0 15px rgb(0 0 0 / 0.1);
  }
  h2 {
    color: #2e7d32;
    margin-bottom: 10px;
  }
  .status {
    font-weight: bold;
    padding: 10px 15px;
    border-radius: 5px;
    display: inline-block;
    margin-bottom: 20px;
  }
  .status.aberto {
    background: #388e3c;
    color: white;
  }
  .status.fechado {
    background: #c62828;
    color: white;
  }
  .temperatura {
    font-size: 2rem;
    margin: 10px 0 5px;
  }
  .hora {
    color: #666;
    margin-bottom: 20px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 15px;
  }
  th, td {
    padding: 8px 12px;
    border-bottom: 1px solid #ddd;
    text-align: left;
  }
  th {
    background-color: #f2f2f2;
  }
  button {
    background-color: #2e7d32;
    color: white;
    border: none;
    padding: 12px 25px;
    border-radius: 7px;
    cursor: pointer;
    font-size: 1rem;
  }
  button:hover {
    background-color: #276527;
  }
  footer {
    text-align: center;
    margin-top: 40px;
    font-size: 0.9rem;
    color: #aaa;
  }
  @media (max-width: 480px) {
    main {
      margin: 15px;
      padding: 20px;
    }
    header h1 {
      font-size: 1.3rem;
    }
  }
</style>
</head>
<body>
<header>
  <img src="https://via.placeholder.com/50" alt="Logo Clínica" />
  <h1>Centro Veterinário Matavelli</h1>
</header>
<main>
  <h2>Status do Portão</h2>
  {% if status_portao %}
    <div class="status {{ 'aberto' if status_portao.lower() == 'aberto' else 'fechado' }}">
      {{ status_portao }}
    </div>
  {% else %}
    <p>Status indisponível</p>
  {% endif %}

  <h2>Temperatura Atual</h2>
  {% if temperatura is not none %}
    <div class="temperatura">{{ "%.2f"|format(temperatura) }} °C</div>
    <div class="hora">Última atualização: {{ hora }}</div>
  {% else %}
    <p>Temperatura indisponível</p>
  {% endif %}

  <h2>Histórico das Últimas 10 Temperaturas</h2>
  {% if historico %}
    <table>
      <thead>
        <tr><th>Temperatura (°C)</th><th>Hora</th></tr>
      </thead>
      <tbody>
        {% for item in historico %}
          <tr>
            <td>{{ "%.2f"|format(item.temperatura) }}</td>
            <td>{{ item.hora }}</td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  {% else %}
    <p>Nenhum dado disponível</p>
  {% endif %}

  <form action="{{ url_for('toggle_portao') }}" method="post" style="margin-top: 30px;">
    <button type="submit">Abrir / Fechar Portão</button>
  </form>
</main>
<footer>
  &copy; 2025 Centro Veterinário Matavelli
</footer>
</body>
</html>
"""

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
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
