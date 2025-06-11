#!/usr/bin/env python3
"""
fifo_ct.py · Calcula valor de transmisión, coste FIFO y comisión
            para las ventas/permutas de un CSV «Entrada doble» de CoinTracking.

Uso básico:
    python fifo_ct.py "CoinTracking - Entrada doble.csv" -y 2024
Solo BTC:
    python fifo_ct.py "CoinTracking - Entrada doble.csv" -y 2024 --crypto BTC
Forzar separador (;):
    python fifo_ct.py "CoinTracking - Entrada doble.csv" -y 2024 --sep ";"
"""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd


# ────────────────────────────────
# Normaliza cabeceras del CSV
# ────────────────────────────────
def normaliza_cols(df: pd.DataFrame) -> pd.DataFrame:
    """
    - Elimina BOM y espacios.
    - Convierte la cabecera a minúsculas homogéneas.
    - Renombra al estándar interno requerido por el motor FIFO.
    """
    # 1) limpieza global
    df.columns = (
        df.columns.str.replace('\ufeff', '', regex=False)  # BOM
                  .str.strip()                             # espacios
                  .str.lower()                             # a minúsculas
    )

    # 2) diccionario de equivalencias  (TODO en minúsculas)
    rename_map = {
        "fecha de operación": "date",
        "date": "date",
        "tipo": "tipo",
        "type": "tipo",
        "cantidad": "amount",
        "amount": "amount",
        "cur.": "cur",
        "cur": "cur",
        "valor en eur en la transacción": "eur",
        "value in eur": "eur",
        "trade id": "trade_id",
        "trade_id": "trade_id",
    }

    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    faltan = {"date", "tipo", "amount", "cur", "eur", "trade_id"} - set(df.columns)
    if faltan:
        sys.exit(f"⚠️  Faltan columnas en el CSV: {', '.join(faltan)}")
    return df


# ────────────────────────────────
# Ayudantes para detectar tipo de línea
# ────────────────────────────────
def es_compra(s: str) -> bool:
    return bool(re.match(r"(compra|buy)", s, re.I))


def es_venta(s: str) -> bool:
    return bool(re.match(r"(venta|sell)", s, re.I))


def es_fee(s: str) -> bool:
    return bool(re.match(r"(comisi|fee)", s, re.I))


# ────────────────────────────────
# Motor FIFO principal
# ────────────────────────────────
def fifo_ct(
    csv_path: Path,
    year: int,
    ignorar: set[str],
    solo_crypto: str | None,
    sep: str | None,
):
    # 1) leer CSV (autodetecta separador si sep es None)
    read_kwargs = {"sep": sep} if sep else {"sep": None, "engine": "python"}
    df = pd.read_csv(csv_path, **read_kwargs)
    df = normaliza_cols(df)

    # 2) filtrar por año y limpiar valores
    df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=True)
    df = df[df["date"].dt.year == year]
    df["eur"] = (
        df["eur"]
        .replace("-", 0)
        .astype(str)
        .str.replace(",", "", regex=False)
        .astype(float)
    )
    df = df.sort_values("date")

    # 3) opcional: sólo una cripto
    if solo_crypto:
        df = df[df["cur"].str.upper() == solo_crypto.upper()]

    # 4) recorrer filas y aplicar FIFO
    inventario = defaultdict(list)  # {cripto: [[qty, coste€], …]}
    filas = []

    for _, row in df.iterrows():
        cur = row["cur"].upper()
        if cur in ignorar:
            continue

        qty, eur, tipo = row["amount"], row["eur"], row["tipo"]

        # COMPRA
        if es_compra(tipo):
            inventario[cur].append([qty, eur])

        # VENTA / PERMUTA
        elif es_venta(tipo):
            salida = -qty           # cantidad positiva que sale
            valor_transm = -eur     # € brutos recibido
            # fee en la misma operación
            fee_eur = df[
                (df["trade_id"] == row["trade_id"]) & df["tipo"].apply(es_fee)
            ]["eur"].abs().sum()

            coste_fifo = 0.0
            while salida > 1e-12 and inventario[cur]:
                lot_qty, lot_coste = inventario[cur][0]
                if lot_qty <= salida + 1e-12:
                    coste_fifo += lot_coste
                    salida -= lot_qty
                    inventario[cur].pop(0)
                else:
                    prop = salida / lot_qty
                    coste_fifo += lot_coste * prop
                    inventario[cur][0][0] = lot_qty - salida
                    inventario[cur][0][1] = lot_coste * (1 - prop)
                    salida = 0.0

            clave = (
                "F"
                if "EUR"
                in df.loc[
                    df["trade_id"] == row["trade_id"], "cur"
                ].str.upper().values
                else "N"
            )

            filas.append(
                {
                    "fecha": row["date"].date(),
                    "cripto": cur,
                    "qty": -qty,
                    "valor_transm": round(valor_transm, 2),
                    "coste_fifo": round(coste_fifo, 2),
                    "gastos": round(fee_eur, 2),
                    "ganancia": round(valor_transm - coste_fifo - fee_eur, 2),
                    "clave": clave,
                }
            )

    detalle = pd.DataFrame(filas)
    if detalle.empty:
        return detalle, detalle

    resumen = (
        detalle.groupby(["cripto", "clave"], as_index=False)
        .agg(
            valor_transm=("valor_transm", "sum"),
            coste_fifo=("coste_fifo", "sum"),
            gastos=("gastos", "sum"),
            ganancia=("ganancia", "sum"),
        )
        .sort_values(["cripto", "clave"])
    )
    return detalle, resumen


# ────────────────────────────────
# CLI
# ────────────────────────────────
def main():
    ap = argparse.ArgumentParser(
        description="FIFO para CSV «Entrada doble» de CoinTracking"
    )
    ap.add_argument("csv", help="Ruta al CSV exportado desde CoinTracking")
    ap.add_argument("-y", "--year", type=int, default=2024, help="Año fiscal (default 2024)")
    ap.add_argument(
        "--sep",
        help="Separador CSV (',' ';' '\\t'). Si se omite, autodetecta",
    )
    ap.add_argument(
        "--ignore",
        default="EUR",
        help="Tickers a ignorar (coma-separados)",
    )
    ap.add_argument(
        "--crypto",
        help="Procesa solo este criptoactivo (ej. BTC). Si se omite, procesa todos.",
    )
    args = ap.parse_args()

    detalle, resumen = fifo_ct(
        Path(args.csv),
        year=args.year,
        ignorar=set(t.strip().upper() for t in args.ignore.split(",")),
        solo_crypto=args.crypto,
        sep=args.sep,
    )

    if detalle.empty:
        print("⚠️  No se encontraron ventas/permutas que cumplan los filtros.")
        return

    print("\n── Detalle de operaciones ──")
    print(detalle.to_string(index=False))

    print("\n── Resumen por moneda ──")
    print(resumen.to_string(index=False))

    # guardar CSV
    base = Path(args.csv).with_suffix("")
    detalle.to_csv(base.with_suffix(f".fifo_{args.year}_detalle.csv"), index=False)
    resumen.to_csv(base.with_suffix(f".fifo_{args.year}_resumen.csv"), index=False)
    print(
        f"\n✔ CSV generados:\n  • {base.name}.fifo_{args.year}_detalle.csv\n  • {base.name}.fifo_{args.year}_resumen.csv"
    )


if __name__ == "__main__":
    main()

