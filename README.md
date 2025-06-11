# fifo_ct

**fifo_ct** es un pequeño script en Python que convierte el CSV “Entrada doble” exportado desde [CoinTracking](https://cointracking.info) en un informe listo para copiar a **Renta WEB** (apartado F2), aplicando el método **FIFO global** que exige la Agencia Tributaria española.

---

## 🚀 Características

* 📂 Lee directamente el CSV *Entrada doble* español o inglés (autodetección de `,`, `;` o `\t`).
* 🔄 Combina **compras, ventas, permutas y fees** agrupadas por `Trade ID`.
* 📈 Calcula:

  * `valor_transm` → valor bruto de la transmisión (casilla 1804)
  * `coste_fifo` → coste de adquisición FIFO (casilla 1806)
  * `gastos` → comisiones deducibles (lápiz 🖉 de 1804)
* 📊 Devuelve dos CSV:

  1. **detalle** (una fila por operación)
  2. **resumen** (suma por moneda y clave F/N)
* 🔎 Permite procesar **todo el portfolio** o filtrar por un solo criptoactivo (`--crypto BTC`).
* ⚙️ Parámetros de línea de comandos: año fiscal, separador, lista de monedas a ignorar, etc.

---

## 📋 Requisitos

* Python ≥ 3.9
* pandas ≥ 2.0

```bash
pip install pandas
```

---

## 🛠️ Instalación

No necesita instalación: basta con clonar el repositorio y ejecutar el script.

```bash
git clone https://github.com/Canx/fifo_ct.git
cd fifo_ct
python fifo_ct.py -h    # muestra ayuda
```

---

## 🧑‍💻 Uso rápido

### 1 · Exporta tu CSV

En CoinTracking → **Informe → Entrada doble → Descargar CSV**.

### 2 · Ejecuta el script

```bash
# procesa todas las monedas para 2024 (CSV en español con «;")
python fifo_ct.py "CoinTracking - Entrada doble.csv" -y 2024 --sep ";"

# procesa SOLO BTC
python fifo_ct.py "CoinTracking - Entrada doble.csv" -y 2024 --crypto BTC
```

### 3 · Archivos generados

* `…fifo_2024_detalle.csv` → libro registro completo (por si lo pide la AEAT)
* `…fifo_2024_resumen.csv` → totales por moneda/clave listos para Renta WEB

---

## 📝 Copiar a Renta WEB

Para cada fila del **resumen**:

| Columna resumen   | Casilla Renta WEB                              |
| ----------------- | ---------------------------------------------- |
| `cripto`          | Denominación de la moneda virtual              |
| `clave` (`F`/`N`) | Tipo de contraprestación (F = € / N = permuta) |
| `valor_transm`    | 1804 – Valor de transmisión                    |
| `coste_fifo`      | 1806 – Valor de adquisición                    |
| `gastos`          | Lápiz 🖉 en 1804 → Gastos y tributos           |

Renta WEB calcula automáticamente la ganancia/pérdida y la traslada a la base del ahorro.

---

## 🔧 Parámetros principales

```bash
-y, --year    Año fiscal a procesar (default 2024)
--sep         Separador CSV (uno de "," «;» "\t"). Si se omite, autodetecta.
--ignore      Lista de tickers a excluir del FIFO (default "EUR").
--crypto      Procesar solo esta moneda (ej. BTC). Si se omite, procesa todas.
```

Ejemplo completo:

```bash
python fifo_ct.py entrada.csv -y 2024 --crypto ADA
```

---

## 🛡️ Descargo de responsabilidad

Este script **no es asesoramiento fiscal**. Revise siempre los resultados y consulte a un profesional si tiene dudas.

---

## 📜 Licencia

MIT License — si te resulta útil, ¡haz un *star* ⭐ y/o contribuye!
