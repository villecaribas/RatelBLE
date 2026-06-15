import bluetooth
from machine import Pin
import time
from time import sleep, sleep_ms
from micropython import const
from Buzzer_eureka import BuzzerPTK, musicas

from boot import *
from RatelServo import RatelServo

_IRQ_CONECTOU = const(1)
_IRQ_DESCONECTOU = const(2)
_IRQ_CHEGOU_DADOS = const(3)

# Flag para habilitar o BLE
_FLAG_READ = const(0x0002)
_FLAG_WRITE_NO_RESPONSE = const(0x0004)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)

# Defina o serviço e característica
_LED_UUID = bluetooth.UUID('12345678-1234-5678-1234-56789ABCDEF0')  # Serviço UUID personalizado
_LED_CHAR = (bluetooth.UUID('12345678-1234-5678-1234-56789ABCDEF1'),  # Característica UUID
             _FLAG_READ | _FLAG_WRITE | _FLAG_NOTIFY,)
_LED_SERVICE = (_LED_UUID, (_LED_CHAR,),)



servo = RatelServo(32)  # Conecte o servo ao pino 32 (ajuste conforme necessário)
buzzer = BuzzerPTK(26)  # Conecte o buzzer ao pino 26 (ajuste conforme necessário)
# UUIDs para o serviço e característica (use UUIDs personalizados ou padrões)

class BLEServer:
    def __init__(self, name):
        self._ble = bluetooth.BLE()
        self._ble.active(True)
        self._ble.irq(self._irq)
        ((self._handle,),) = self._ble.gatts_register_services((_LED_SERVICE,))
        self._connections = set()
        self._advertise(name)
        print("\n\n\033[1;34m"+name+"\033[0m está pronto para missão.\n")

    def _advertise(self, name):
        name_bytes = bytes(name, 'utf-8')[:26]
        adv_data = (
            b'\x02\x01\x06' +
            bytes((len(name_bytes) + 1, 0x09)) +
            name_bytes
        )
        self._ble.config(gap_name=name)
        self._ble.gap_advertise(100000, adv_data=adv_data)

    def enviar(self, mensagem):
            """
            Envia uma mensagem para todos os clientes Bluetooth conectados.
            Usa BLE Notify.
            """

            if not self._connections:
                print("\033[1;31mNenhum cliente conectado para enviar dados.\033[0m")
                return False

            if isinstance(mensagem, str):
                dados = mensagem.encode("utf-8")
            else:
                dados = mensagem

            for conn_handle in self._connections.copy():
                try:
                    self._ble.gatts_notify(conn_handle, self._handle, dados)
                    print(f"\033[1;32m(→ {mensagem}) enviado para cliente BLE.\033[0m")
                except Exception as e:
                    print(f"\033[1;31mErro ao enviar para cliente {conn_handle}: {e}\033[0m")
                    try:
                        self._connections.remove(conn_handle)
                    except:
                        pass

            return True


    def _irq(self, event, data):
        if event == _IRQ_CONECTOU:
            conn_handle, _, _ = data
            self._connections.add(conn_handle)
            print("\033[1;33mConexao OK!!\33[0m")
            
        elif event == _IRQ_DESCONECTOU:
            print("\033[1;31mConexao FECHADA!!\33[0m")
            conn_handle, _, _ = data
            self._connections.remove(conn_handle)            
            self._advertise(nomeDoLino)  # Reanuncia
            print("\033[1;34m"+nomeDoLino+"\033[0m está pronto reconectar.")

        elif event == _IRQ_CHEGOU_DADOS:
            conn_handle, value_handle = data
            value = self._ble.gatts_read(self._handle)
            cmd = value.decode('utf-8').strip()

            ## Processa o comando recebido
            if cmd == "PING":
                print(f"(← {cmd}) recebido, respondendo PONG")
                self.enviar("PONG")
            if cmd.startswith("servo"):
                try:
                    _, angle_str = cmd.split()
                    angle = int(angle_str)
                    if 0 <= angle <= 180:
                        servo.set_angle(angle)
                        print(f"(← {cmd}) recebido, servo ajustado para {angle}°")
                        self.enviar(f"Servo ajustado para {angle}°")
                    else:
                        print(f"(← {cmd}) valor de ângulo inválido: {angle}")
                        self.enviar("Erro: Ângulo deve ser entre 0 e 180")
                except Exception as e:
                    print(f"(← {cmd}) comando de servo inválido: {e}")
                    self.enviar("Erro: Comando de servo inválido")
# ━━━━━━━━━━━━━━━━━━━━━━━━━━┓
# Murilo - Buzzer e músicas ┃
# ━━━━━━━━━━━━━━━━━━━━━━━━━━┻━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
            elif cmd == "LISTAR":
                nomes = list(musicas.keys())
                resposta = "Músicas: " + ", ".join(nomes)
                print(f"(← {cmd}) listando músicas")
                self.enviar(resposta)

            elif cmd.startswith("TOCAR "):
                nome = cmd[6:].strip().lower()  # Pega tudo após "TOCAR "
                if nome in [k.lower() for k in musicas.keys()]:  
                    print(f"(← {cmd}) tocando '{nome}'")
                    self.enviar(f"Tocando: {nome}")
                    buzzer.play(nome.lower())
                else:
                    print(f"(← {cmd}) música '{nome}' não encontrada")
                    self.enviar(f"Não encontrada: {nome}")

            elif cmd == "PARAR":
                print(f"(← {cmd}) parando buzzer")
                buzzer.stop()
                self.enviar("Parado")
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
            else:
                print(f"(← {cmd}) não reconhecido)")

# Inicia o servidor
ble_server = BLEServer(nomeDoLino)

# Ville EUREKA!!
#pietro eureka
# Murilo EUREKA!!
#mariana
# Não tem mais ninguém, só o Lino mesmo. E ele é o melhor de todos, claro! :D


# Loop principal para manter o programa rodando
while True:
    time.sleep(1)
