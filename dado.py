#!/usr/bin/env python3
"""
DADO DIGITAL - Raspberry Pi + LCD 1602 + Claude API
Game master para juego de mesa familiar

Conexiones LCD:
  RS → GPIO 26 (pin 37)
  E  → GPIO 19 (pin 35)
  D4 → GPIO 13 (pin 33)
  D5 → GPIO 6  (pin 31)
  D6 → GPIO 5  (pin 29)
  D7 → GPIO 12 (pin 32)

Botones:
  DADO → GPIO 20 (pin 38) a GND  - tira dado normal
  RETO → GPIO 21 (pin 40) a GND  - pide reto a Claude

Salir: ambos botones apretados 2 segundos

Instalar:
  pip install RPLCD RPi.GPIO anthropic --break-system-packages
"""

import random
import time
from RPLCD.gpio import CharLCD
import RPi.GPIO as GPIO

# ── Intentar importar Claude (opcional) ─────────────
try:
    import anthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False
    print("anthropic no instalado - modo sin Claude")

# ── Config ──────────────────────────────────────────
BTN_DADO = 20   # pin 38
BTN_RETO = 21   # pin 40

CLAUDE_MODEL = "claude-haiku-4-5-20251001"

# ── LCD Setup ───────────────────────────────────────
time.sleep(3)
lcd = CharLCD(
    pin_rs=26,
    pin_e=19,
    pins_data=[13, 6, 5, 12],
    numbering_mode=GPIO.BCM,
    cols=16,
    rows=2,
)
time.sleep(0.5)
lcd.clear()
time.sleep(0.5)
lcd.clear()
time.sleep(0.2)

# ── Botones Setup ──────────────────────────────────
GPIO.setup(BTN_DADO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BTN_RETO, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# ── Funciones de botones ───────────────────────────
def btn_dado_pressed():
    return GPIO.input(BTN_DADO) == 0

def btn_reto_pressed():
    return GPIO.input(BTN_RETO) == 0

def both_pressed():
    return btn_dado_pressed() and btn_reto_pressed()

def sleep_or_exit(seconds):
    """Sleep que chequea exit cada 100ms. Retorna True si hay que salir."""
    start = time.time()
    while time.time() - start < seconds:
        if check_exit():
            return True
        time.sleep(0.1)
    return False

def check_exit():
    """Retorna True si ambos botones apretados 2 segundos"""
    if both_pressed():
        lcd_write("  Soltar para", "  seguir...")
        start = time.time()
        while both_pressed():
            elapsed = time.time() - start
            if elapsed >= 2:
                return True
            remaining = 2 - elapsed
            lcd.cursor_pos = (1, 0)
            lcd.write_string(f"  Salir: {remaining:.1f}s  ")
            time.sleep(0.1)
        return False
    return False

def wait_btn_release():
    """Espera que se suelten todos los botones"""
    while btn_dado_pressed() or btn_reto_pressed():
        time.sleep(0.05)

def wait_any_btn():
    """Espera cualquier botón. Retorna 'dado', 'reto', o 'exit'"""
    while True:
        if both_pressed():
            if check_exit():
                return "exit"
            continue
        if btn_dado_pressed():
            time.sleep(0.05)
            wait_btn_release()
            return "dado"
        if btn_reto_pressed():
            time.sleep(0.05)
            wait_btn_release()
            return "reto"
        time.sleep(0.05)

def wait_dado_btn():
    """Espera solo el botón DADO. Retorna 'dado' o 'exit'"""
    while True:
        if both_pressed():
            if check_exit():
                return "exit"
            continue
        if btn_dado_pressed():
            time.sleep(0.05)
            wait_btn_release()
            return "dado"
        time.sleep(0.05)

# ── Funciones LCD ──────────────────────────────────
def lcd_write(line1, line2=""):
    lcd.cursor_pos = (0, 0)
    lcd.write_string(line1[:16].ljust(16))
    lcd.cursor_pos = (1, 0)
    lcd.write_string((line2[:16] if line2 else "").ljust(16))

def lcd_scroll(line1, line2, delay=0.3):
    """Scroll text si es más largo que 16 chars"""
    lcd_write(line1[:16], line2[:16])
    if len(line2) > 16:
        time.sleep(1)
        for i in range(1, len(line2) - 15):
            if check_exit():
                return
            lcd.cursor_pos = (1, 0)
            lcd.write_string(line2[i:i+16])
            time.sleep(delay)
        time.sleep(1)

def lcd_message(msg):
    """Muestra un mensaje en las 2 líneas del LCD, cortando por palabra"""
    msg = msg.strip()
    if len(msg) <= 16:
        lcd_write(msg.center(16), "")
        return

    cut = msg.rfind(' ', 0, 17)
    if cut == -1:
        cut = 16

    line1 = msg[:cut].strip()
    line2 = msg[cut:].strip()

    if len(line2) <= 16:
        lcd_write(line1[:16], line2[:16])
    else:
        lcd_scroll(line1[:16], line2)

def rolling_animation():
    """Animación de dado girando"""
    spinner = ['/', '-', '\\', '|']
    delay = 0.05
    for i in range(16):
        s = spinner[i % 4]

        lcd.cursor_pos = (0, 0)
        lcd.write_string(f"  Tirando..  {s} ")

        lcd.cursor_pos = (1, 0)
        progress = int((i / 15) * 13)
        bar = "\xFF" * progress + "-" * (13 - progress)
        lcd.write_string(f" {bar}  ")

        time.sleep(delay)
        delay += 0.02

def show_dice_result(face, double=False):
    """Muestra el resultado del dado"""
    dots = {
        1: "       *        ",
        2: "   *        *   ",
        3: "  *    *    *   ",
        4: "  * *     * *   ",
        5: " * *   *   * *  ",
        6: " * *  * *  * *  ",
    }
    if double:
        lcd_write(f"  Doble! [{face}]  ", dots.get(face, ""))
    else:
        lcd_write(f"  Salio:  [ {face} ]", dots[face])

# ── Claude Reto ────────────────────────────────────
def ask_reto():
    """Pide a Claude un reto para el jugador"""
    if not CLAUDE_AVAILABLE:
        retos = [
            "Imita un animal",
            "Canta una cancion",
            "Salta en un pie",
            "Haz 5 aplausos",
            "Baila 10 segundos",
            "Di un trabalenguas",
            "Haz una mueca",
            "Cuenta hasta 20",
            "Nombra 5 colores",
            "Haz de robot",
        ]
        return random.choice(retos)

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=30,
            system=f"""Sos el game master de un juego de mesa familiar con ninos.
REGLA ESTRICTA: Responde SOLO con el reto, maximo 30 caracteres. Sin comillas, sin explicacion.
El reto debe ser algo divertido y facil que se pueda hacer en el momento.
Ejemplos: Imita un gato, Salta 3 veces, Canta algo, Baila 5 segundos
Usa espanol simple. Solo ASCII basico (sin acentos ni tildes).
Varia los retos - que sean divertidos y apropiados para ninos.""",
            messages=[{
                "role": "user",
                "content": "Dame un reto divertido y corto para un jugador."
            }]
        )
        msg = response.content[0].text.strip()
        msg = msg.encode('ascii', 'replace').decode('ascii')
        return msg[:32]
    except Exception as e:
        print(f"Error Claude: {e}")
        return "Imita un animal"

# ── Shutdown ───────────────────────────────────────
def shutdown():
    lcd_write("Hasta luego!", "Chau!")
    time.sleep(2)
    lcd.close()
    GPIO.cleanup()

# ── Juego principal ────────────────────────────────
def main():
    lcd_write("  DADO DIGITAL", "  Game Master!")
    if sleep_or_exit(2):
        shutdown()
        return

    lcd_write("DADO=tirar", "RETO=desafio!")
    if sleep_or_exit(2):
        shutdown()
        return

    while True:
        # Esperar acción
        lcd_write("Tu turno!", "DADO o RETO?")

        resp = wait_any_btn()
        if resp == "exit":
            shutdown()
            return

        if resp == "dado":
            # ── Dado normal ──
            rolling_animation()
            dado = random.randint(1, 6)
            show_dice_result(dado)
            if sleep_or_exit(2):
                shutdown()
                return

        elif resp == "reto":
            # ── Reto de Claude ──
            lcd_write("  RETO!", "Pensando...")
            reto = ask_reto()
            print(f"[Claude] Reto: {reto}")

            # Mostrar reto
            lcd_message(reto)
            if sleep_or_exit(4):
                shutdown()
                return

            # Preguntar si cumplió
            lcd_write("Lo cumplio?", "DADO=si RETO=no")

            resp2 = wait_any_btn()
            if resp2 == "exit":
                shutdown()
                return

            if resp2 == "dado":
                # Cumplió: tira dos dados
                rolling_animation()
                dado1 = random.randint(1, 6)
                dado2 = random.randint(1, 6)
                total = dado1 + dado2
                show_dice_result(total, double=True)
                print(f"Reto cumplido! {dado1}+{dado2}={total}")
                if sleep_or_exit(2):
                    shutdown()
                    return
            else:
                # No cumplió: pierde turno
                lcd_write(" No cumplio!", " Pierde turno!")
                print("Reto fallido - pierde turno")
                if sleep_or_exit(2):
                    shutdown()
                    return

        # Volver a esperar
        lcd_write("Siguiente turno", "DADO o RETO?")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrumpido")
        shutdown()
    except Exception as e:
        print(f"Error: {e}")
        try:
            shutdown()
        except:
            GPIO.cleanup()
