from machine import Pin
from time import sleep


class Ratelled:
    def __init__(self, pino=2):
        """
        Inicializa o LED.
        pino: GPIO onde o LED está conectado.
        No ESP32 normalmente o LED interno usa GPIO 2.
        """
        self.led = Pin(pino, Pin.OUT)

    def ligar(self):
        """Liga o LED"""
        self.led.on()

    def desligar(self):
        """Desliga o LED"""
        self.led.off()

    def alternar(self):
        """Inverte o estado do LED"""
        self.led.value(not self.led.value())

    def piscar(self, vezes=5, intervalo=0.5):
        """
        Faz o LED piscar.
        vezes: quantidade de piscadas
        intervalo: tempo entre ligar/desligar
        """
        for _ in range(vezes):
            self.ligar()
            sleep(intervalo)

            self.desligar()
            sleep(intervalo)