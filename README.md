# Dado Digital - Game Master

Un dado digital interactivo para juegos de mesa familiares, construido con Raspberry Pi, una pantalla LCD 1602 y la API de Claude como game master.

## Que hace

- **Boton DADO**: Tira un dado virtual (1-6) con animacion en el LCD
- **Boton RETO**: Claude genera un desafio divertido para el jugador (ej: "Imita un gato", "Salta 3 veces")
  - Si el jugador cumple el reto, tira dos dados como recompensa
  - Si no lo cumple, pierde el turno
- **Salir**: Mantener ambos botones presionados por 2 segundos

Si la API de Claude no esta disponible, los retos se eligen de una lista predefinida.

## Hardware

- Raspberry Pi (cualquier modelo con GPIO)
- Pantalla LCD 1602 (modo 4 bits)
- 2 botones pulsadores

### Conexiones

| LCD  | GPIO (BCM) | Pin fisico |
|------|------------|------------|
| RS   | 26         | 37         |
| E    | 19         | 35         |
| D4   | 13         | 33         |
| D5   | 6          | 31         |
| D6   | 5          | 29         |
| D7   | 12         | 32         |

| Boton | GPIO (BCM) | Pin fisico |
|-------|------------|------------|
| DADO  | 20         | 38 (a GND)|
| RETO  | 21         | 40 (a GND)|

## Instalacion

```bash
pip install RPLCD RPi.GPIO anthropic --break-system-packages
```

Para los retos con IA, configura tu API key:

```bash
export ANTHROPIC_API_KEY="tu-clave-aqui"
```

## Uso

```bash
python dado.py
```
