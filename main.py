from time import sleep, sleep_ms
from machine import Pin
from micropython import const
from Buzzer_eureka import BuzzerPTK, musicas

from boot import *
from RatelServo import RatelServo

servo = RatelServo(32)
buzzer = BuzzerPTK(26)

_IRQ_CONECTOU = const(1)
_IRQ_DESCONECTOU = const(2)
_IRQ_CHEGOU_DADOS = const(3)

_FLAG_READ = const(0x0002)
_FLAG_WRITE_NO_RESPONSE = const(0x0004)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)

_LED_UUID = bluetooth.UUID('12345678-1234-5678-1234-56789ABCDEF0')
_LED_CHAR = (bluetooth.UUID('12345678-1234-5678-1234-56789ABCDEF1'),
             _FLAG_READ | _FLAG_WRITE | _FLAG_NOTIFY,)
_LED_SERVICE = (_LED_UUID, (_LED_CHAR,),)


class BLEServer:
    def __init__(self, name):
        self._ble = bluetooth.BLE()
        self._ble.active(True)
        self._ble.irq(self._irq)
        ((self._handle,),) = self._ble.gatts_register_services((_LED_SERVICE,))
        self._connections = set()
        self._advertise(name)
        print("\n\n\033[1;34m" + name + "\033[0m está pronto para missão.\n")

    def _advertise(self, name):
        name = bytes(name, 'utf-8')
        self._ble.gap_advertise(100, adv_data=b'\x02\x01\x06' + chr(len(name) + 1) + '\x09' + name)

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
            self._advertise(nomeDoLino)
            print("\033[1;34m" + nomeDoLino + "\033[0m está pronto reconectar.")

        elif event == _IRQ_CHEGOU_DADOS:
            conn_handle, value_handle = data
            value = self._ble.gatts_read(self._handle)
            cmd = value.decode('utf-8').strip()

            if cmd == "PING":
                print(f"(← {cmd}) recebido, respondendo PONG")
                self.enviar("PONG")

            elif cmd.startswith("servo"):  # CORRIGIDO: era "if", agora é "elif"
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
            elif cmd == "MUSICAS.LISTAR":
                nomes = list(musicas.keys())
                resposta = "Músicas: " + ", ".join(nomes)
                print(f"(← {cmd}) listando músicas")
                self.enviar(resposta)

            elif cmd.startswith("MUSICAS.TOCAR "):
                nome = cmd[14:].strip().lower()
                if nome in [k.lower() for k in musicas.keys()]:
                    print(f"(← {cmd}) tocando '{nome}'")
                    self.enviar(f"Tocando: {nome}")
                    buzzer.play(nome.lower())
                else:
                    print(f"(← {cmd}) música '{nome}' não encontrada")
                    self.enviar(f"Não encontrada: {nome}")

            elif cmd.startswith("MUSICAS.TOCAR."):
                try:
                    # Formato: MUSICAS.TOCAR.<nome>:<params>:<notas>
                    # Exemplo:  MUSICAS.TOCAR.Axel:o=5,d=8,b=125:16g,16g,a#...
                    resto = cmd[15:]  # CORRIGIDO: era 14, agora é 15 — remove "MUSICAS.TOCAR."
                    partes = resto.split(":", 2)

                    if len(partes) != 3:
                        raise ValueError("Formato inválido. Use: MUSICAS.TOCAR.<nome>:<params>:<notas>")

                    nome_custom = partes[0].strip()
                    params_str  = partes[1].strip()
                    notes_str   = partes[2].strip()

                    bpm         = 120
                    default_dur = 16
                    default_oct = 5

                    for param in params_str.split(","):
                        param = param.strip()
                        if param.startswith("b="):
                            bpm = int(param[2:])
                        elif param.startswith("d="):
                            default_dur = int(param[2:])
                        elif param.startswith("o="):
                            default_oct = int(param[2:])

                    print(f"(← {cmd}) tocando música personalizada '{nome_custom}' "
                          f"(bpm={bpm}, dur={default_dur}, oct={default_oct})")
                    self.enviar(f"Tocando: {nome_custom}")
                    buzzer.play(notes_str, bpm, default_dur, default_oct)

                except Exception as e:
                    print(f"(← {cmd}) erro ao processar música personalizada: {e}")
                    self.enviar(f"Erro: {e}")

            elif cmd == "MUSICAS.PARAR":
                print(f"(← {cmd}) parando buzzer")
                buzzer.stop()
                self.enviar("Parado")
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
            else:
                print(f"(← {cmd}) não reconhecido")


# Inicia o servidor
ble_server = BLEServer(nomeDoLino)

# Ville EUREKA!!
# pietro eureka
# Murilo EUREKA!!
# mariana
# Não tem mais ninguém, só o Lino mesmo. E ele é o melhor de todos, claro! :D
# <O>