from machine import Pin, PWM
from time import sleep_ms


class ServoEUK:
    VELOCIDADE_MIN = 1
    VELOCIDADE_MAX = 20

    def __init__(self,
                 pin,
                 freq=50,
                 min_us=500,
                 max_us=2500):

        self.freq = freq
        self.min_us = min_us
        self.max_us = max_us

        self.pwm = PWM(Pin(pin), freq=freq)

        self.angulo = 90

        # Inicia na velocidade máxima
        self.velocidade = ServoEUK.VELOCIDADE_MAX

        self.write(self.angulo)

    # ----------------------------------------------------

    def _us_to_duty(self, us):
        periodo = 1000000 / self.freq
        return int((us / periodo) * 65535)

    # ----------------------------------------------------

    def _angulo_to_us(self, angulo):
        return self.min_us + (self.max_us - self.min_us) * angulo / 180

    # ----------------------------------------------------

    def write(self, angulo):

        angulo = max(0, min(180, angulo))

        us = self._angulo_to_us(angulo)

        self.pwm.duty_u16(self._us_to_duty(us))

        self.angulo = angulo

    # ----------------------------------------------------

    def setVelocidade(self, velocidade):
        """
        Define a velocidade do servo.

        1 = Muito lento
        20 = Máxima velocidade
        """

        velocidade = max(self.VELOCIDADE_MIN,
                         min(self.VELOCIDADE_MAX, velocidade))

        self.velocidade = velocidade

    # ----------------------------------------------------

    def getVelocidade(self):
        return self.velocidade

    # ----------------------------------------------------

    def mover(self, destino):

        destino = max(0, min(180, destino))

        if destino == self.angulo:
            return

        passo = self.velocidade

        if destino > self.angulo:

            while self.angulo < destino:

                self.angulo += passo

                if self.angulo > destino:
                    self.angulo = destino

                self.write(self.angulo)

                sleep_ms(20)

        else:

            while self.angulo > destino:

                self.angulo -= passo

                if self.angulo < destino:
                    self.angulo = destino

                self.write(self.angulo)

                sleep_ms(20)

    # ----------------------------------------------------

    def center(self):
        self.mover(90)

    def left(self):
        self.mover(0)

    def right(self):
        self.mover(180)

    # ----------------------------------------------------

    def desligar(self):
        self.pwm.deinit()