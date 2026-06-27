from machine import Pin, PWM
from time import sleep_ms


class ServoEUK:
    """
    Classe para controle de Servo Motor (SG90, MG90S, MG996R, etc.)

    Autor: Patrulha EUREKA
    """

    def __init__(self,
                 pin,
                 freq=50,
                 min_us=500,
                 max_us=2500,
                 angle=90):

        self.pin = Pin(pin, Pin.OUT)
        self.pwm = PWM(self.pin, freq=freq)

        self.freq = freq
        self.min_us = min_us
        self.max_us = max_us

        self._angle = None
        self.write(angle)

    # -----------------------------------------------------

    def _us_to_duty(self, us):
        """
        Converte microssegundos para duty de 16 bits.
        """

        period = 1000000 / self.freq
        duty = int((us / period) * 65535)
        return duty

    # -----------------------------------------------------

    def write(self, angle):
        """
        Posiciona o servo no ângulo informado.
        """

        angle = max(0, min(180, angle))

        us = self.min_us + (self.max_us - self.min_us) * angle / 180

        self.pwm.duty_u16(self._us_to_duty(us))

        self._angle = angle

    # -----------------------------------------------------

    def read(self):
        """
        Retorna o ângulo atual.
        """

        return self._angle

    # -----------------------------------------------------

    def move(self, angle, step=1, delay=15):
        """
        Move suavemente até o ângulo desejado.
        """

        angle = max(0, min(180, angle))

        if self._angle is None:
            self.write(angle)
            return

        if angle > self._angle:
            rng = range(int(self._angle), int(angle) + 1, step)
        else:
            rng = range(int(self._angle), int(angle) - 1, -step)

        for a in rng:
            self.write(a)
            sleep_ms(delay)

    # -----------------------------------------------------

    def off(self):
        """
        Desliga o PWM.
        """

        self.pwm.deinit()

    # -----------------------------------------------------

    def center(self):
        self.write(90)

    def left(self):
        self.write(0)

    def right(self):
        self.write(180)