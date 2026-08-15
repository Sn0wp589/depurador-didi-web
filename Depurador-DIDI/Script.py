import difflib
import os
import unicodedata
import pandas as pd
from openpyxl.utils import get_column_letter

INPUT_FILE = "DATA_AGREGADORES_DIDI.xlsx"
OUTPUT_FILE = "DATA_AGREGADORES_DIDI_FILTRADO.xlsx"
CUSTOM_CHMPS_BASENAME = "CHMPS_MAPPING"


def load_data(path: str) -> pd.DataFrame:
    """Carga los datos desde un archivo Excel."""
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"No se encontró el archivo: {abs_path}")

    try:
        return pd.read_excel(abs_path)
    except PermissionError as exc:
        raise PermissionError(
            f"No se puede abrir el archivo. Cierra el archivo en Excel o revisa permisos: {abs_path}"
        ) from exc


def show_summary(df: pd.DataFrame) -> None:
    """Muestra resumen básico: filas, columnas y primeras filas."""
    print("Dimensiones:", df.shape)
    print("Columnas:", df.columns.tolist())
    print("Primeras filas:")
    print(df.head(5).to_string(index=False))


def filter_data(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Filtra el DataFrame según un diccionario de condiciones.

    filters: {'columna': 'valor', 'otra_col': ['a', 'b']}
    """
    result = df.copy()
    for column, value in filters.items():
        if column not in result.columns:
            raise ValueError(f"La columna '{column}' no existe en los datos.")

        if isinstance(value, list):
            result = result[result[column].isin(value)]
        elif pd.isna(value):
            result = result[result[column].isna()]
        else:
            result = result[result[column] == value]
    return result


def sort_data(df: pd.DataFrame, sort_columns: list, ascending: bool = True) -> pd.DataFrame:
    """Ordena el DataFrame por una o varias columnas."""
    missing = [col for col in sort_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Columnas de ordenación no encontradas: {missing}")
    return df.sort_values(by=sort_columns, ascending=ascending)


def normalize_store_name(value) -> str:
    """Normaliza el valor de la columna Nombre de la tienda a KFC(<nombre>)."""
    if pd.isna(value):
        return value

    text = str(value).strip()
    if not text:
        return text

    import re

    # Buscar contenido dentro de paréntesis y mantener solo eso.
    paren = re.search(r"\(([^)]+)\)", text)
    if paren:
        store_name = paren.group(1).strip()
        return f"KFC({store_name})"

    # Si no hay paréntesis, buscar texto después de KFC y usarlo.
    match = re.search(r"KFC\s*[:\-–]?\s*(.+)$", text, flags=re.IGNORECASE)
    if match:
        store_name = match.group(1).strip()
        if store_name:
            return f"KFC({store_name})"

    # Si no se detecta patrón, devolver el texto original dentro de KFC(...)
    return f"KFC({text})"


def clean_nombre_tienda(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica la normalización a la columna Nombre de la tienda."""
    column = "Nombre de la tienda"
    if column not in df.columns:
        raise ValueError(f"La columna '{column}' no existe en los datos.")
    df = df.copy()
    df[column] = df[column].apply(normalize_store_name)
    return df


def add_prefix_to_column(df: pd.DataFrame, column: str, prefix: str) -> pd.DataFrame:
    """Agrega un prefijo a los valores de una columna específica."""
    if column not in df.columns:
        raise ValueError(f"La columna '{column}' no existe en los datos.")
    df = df.copy()
    df[column] = df[column].astype(str).apply(lambda x: prefix + x if x.strip() else x)
    return df


def extract_store_name(store_value) -> str:
    """Extrae el nombre limpio de la tienda desde el valor de Nombre de la tienda."""
    if pd.isna(store_value):
        return ""
    text = str(store_value).strip()
    if not text:
        return ""

    import re
    
    # Extraer contenido de paréntesis si existe
    match = re.search(r"\(([^)]+)\)", text)
    if match:
        name = match.group(1).strip().lower()
    else:
        # Extraer todo lo que está después de KFC
        match = re.search(r"KFC\s*[:\-–]?\s*(.+)$", text, flags=re.IGNORECASE)
        if match:
            name = match.group(1).strip().lower()
        else:
            name = text.lower()
            
    # Eliminar la palabra "postres" o "postre" para que coincida con las reglas normales
    name = re.sub(r'\bpostres?\b', '', name, flags=re.IGNORECASE)
    
    # Limpiar guiones o espacios extra que hayan quedado sueltos
    name = re.sub(r'^\s*[:\-–]\s*|\s*[:\-–]\s*$', '', name)
    return name.strip()



def normalize_text(text: str) -> str:
    """Normaliza texto para comparaciones: sin acentos, sin signos, minúsculas."""
    if pd.isna(text):
        return ""
    value = str(text).strip().lower()
    value = unicodedata.normalize("NFD", value)
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in value)
    value = " ".join(value.split())
    return value


def find_custom_chmps_file() -> str | None:
    """Busca un archivo de mapeo CHMPS en la carpeta actual."""
    for candidate in os.listdir("."):
        candidate_norm = candidate.lower()
        if candidate_norm.startswith(CUSTOM_CHMPS_BASENAME.lower()) and (
            candidate_norm.endswith(".xlsx")
            or candidate_norm.endswith(".xls")
            or candidate_norm.endswith(".csv")
        ):
            return candidate
    return None


def load_custom_chmps_mapping(path: str | None = None) -> dict[str, str]:
    """Carga un archivo de mapeo personalizado de Nombre de la tienda a chmps."""
    if path is None:
        path = find_custom_chmps_file()
    if path is None or not os.path.exists(path):
        return {}

    if path.lower().endswith(".csv"):
        df = pd.read_csv(path)
    else:
        df = pd.read_excel(path)

    name_columns = find_columns_by_keywords(df.columns.tolist(), ["nombre", "tienda", "store", "rest", "name"])
    code_columns = find_columns_by_keywords(df.columns.tolist(), ["chmps", "codigo", "code", "57k"])
    if not name_columns or not code_columns:
        raise ValueError(
            f"El archivo de mapeo '{path}' debe contener columnas de nombre y chmps. Columnas encontradas: {df.columns.tolist()}"
        )

    name_col = name_columns[0]
    code_col = code_columns[0]
    mapping = {}
    for name, code in zip(df[name_col].astype(str), df[code_col].astype(str)):
        name_norm = normalize_text(name)
        if name_norm and str(code).strip():
            mapping[name_norm] = str(code).strip()
    return mapping


def find_columns_by_keywords(columns: list[str], keywords: list[str]) -> list[str]:
    """Encuentra columnas cuyo nombre coincide parcialmente con palabras clave."""
    lower_cols = [str(col).lower() for col in columns]
    result = []
    for keyword in keywords:
        for col, lower_col in zip(columns, lower_cols):
            if keyword in lower_col and col not in result:
                result.append(col)
    return result


def find_chmps_columns(df: pd.DataFrame) -> tuple[str | None, str | None]:
    """Encuentra las columnas de nombre y código para el mapeo chmps."""
    columns = df.columns.tolist()
    code_candidates = find_columns_by_keywords(
        columns,
        [
            "rest. champs",
            "rest champs",
            "champs",
            "chmps",
            "57k",
            "codigo",
            "code",
            "id",
        ],
    )
    name_candidates = find_columns_by_keywords(
        columns,
        [
            "rest. name",
            "rest name",
            "nombre de la tienda",
            "restaurante",
            "tienda",
            "local",
            "name",
        ],
    )

    if "M" in columns and "L" in columns:
        return "L", "M"

    if code_candidates and name_candidates:
        for code_col in code_candidates:
            for name_col in name_candidates:
                if code_col != name_col:
                    return code_col, name_col
        return code_candidates[0], name_candidates[0]

    possible_code_cols = [col for col in columns if df[col].astype(str).str.match(r"^57K\d{3,}$").any()]
    possible_name_cols = [col for col in columns if df[col].astype(str).str.contains(r"[A-Za-z ]+").any()]
    if possible_code_cols and possible_name_cols:
        for code_col in possible_code_cols:
            for name_col in possible_name_cols:
                if code_col != name_col:
                    return code_col, name_col
        return possible_code_cols[0], possible_name_cols[0]

    return None, None


def build_chmps_mapping(df: pd.DataFrame, name_col: str, code_col: str) -> dict:
    """Construye un diccionario de restaurante -> código chmps."""
    mapping = dict(zip(df[name_col].astype(str), df[code_col].astype(str)))
    return {normalize_text(k): v for k, v in mapping.items() if k and v}


def get_best_fuzzy_match(store_key: str, mapping: dict, min_ratio: float = 0.65) -> str | None:
    """Devuelve el código chmps con el nombre más parecido al store_key."""
    normalized_key = normalize_text(store_key)
    if not normalized_key:
        return None

    best_ratio = 0.0
    best_code = None
    for candidate, code in mapping.items():
        candidate_norm = normalize_text(candidate)
        if not candidate_norm:
            continue

        if normalized_key == candidate_norm or normalized_key in candidate_norm or candidate_norm in normalized_key:
            return code

        ratio = difflib.SequenceMatcher(None, normalized_key, candidate_norm).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_code = code

    return best_code if best_ratio >= min_ratio else None


def find_similar_store_groups(df: pd.DataFrame, store_col: str = "Nombre de la tienda") -> dict[str, list[str]]:
    """Encuentra nombres de tienda que se normalizan igual y podrían ser duplicados."""
    groups: dict[str, set[str]] = {}
    for name in df[store_col].dropna().astype(str).unique():
        norm = normalize_text(name)
        if not norm:
            continue
        groups.setdefault(norm, set()).add(name)
    return {norm: sorted(values) for norm, values in groups.items() if len(values) > 1}


def report_similar_store_groups(df: pd.DataFrame, store_col: str = "Nombre de la tienda") -> pd.DataFrame:
    """Genera un reporte de nombres similares y sus chmps asociados."""
    similar_groups = find_similar_store_groups(df, store_col=store_col)
    rows = []
    for norm_name, names in similar_groups.items():
        for name in names:
            subset = df[df[store_col].astype(str) == name]
            chmps_values = sorted(subset["chmps"].dropna().astype(str).unique())
            rows.append({
                "Nombre normalizado": norm_name,
                "Nombre original": name,
                "Chmps distintos": "; ".join(chmps_values) if chmps_values else pd.NA,
                "Cantidad filas": len(subset),
            })
    return pd.DataFrame(rows)


def suggest_chmps_for_blank_rows(df: pd.DataFrame, mapping: dict, store_col: str = "Nombre de la tienda") -> pd.DataFrame:
    """Genera sugerencias de chmps para filas con valor vacío."""
    blanks = df[df["chmps"].isna()].copy()
    if blanks.empty:
        return blanks

    mapping_norm = {normalize_text(k): v for k, v in mapping.items()}
    known_norm = list(mapping_norm.keys())
    rows = []
    for _, row in blanks.iterrows():
        store_val = str(row[store_col])
        store_norm = normalize_text(store_val)
        suggestion = None
        suggestion_norm = None
        ratio = None
        if store_norm:
            if store_norm in mapping_norm:
                suggestion_norm = store_norm
                suggestion = mapping_norm[store_norm]
                ratio = 1.0
            else:
                close = difflib.get_close_matches(store_norm, known_norm, n=1, cutoff=0.50)
                if close:
                    suggestion_norm = close[0]
                    suggestion = mapping_norm[close[0]]
                    ratio = difflib.SequenceMatcher(None, store_norm, close[0]).ratio()

        rows.append({
            "Nombre de la tienda": store_val,
            "Nombre normalizado": store_norm,
            "Rest. Name": row.get("Rest. Name", pd.NA),
            "Rest. Champs": row.get("Rest. Champs", pd.NA),
            "Sugerencia chmps": suggestion,
            "Sugerencia normalizada": suggestion_norm,
            "Similitud": round(ratio, 2) if ratio is not None else pd.NA,
        })
    return pd.DataFrame(rows)


def combine_date_time(df: pd.DataFrame, date_col: str, time_col: str, output_col: str = "Fecha Hora", drop_originals: bool = False) -> pd.DataFrame:
    """Combina fecha y hora en un solo campo con formato YYYY-MM-DD HH:MM."""
    if date_col not in df.columns or time_col not in df.columns:
        raise ValueError(f"Las columnas '{date_col}' y/o '{time_col}' no existen en los datos.")

    df = df.copy()

    def parse_date(series: pd.Series) -> pd.Series:
        if pd.api.types.is_datetime64_any_dtype(series):
            return series.dt.strftime("%Y-%m-%d")
        if pd.api.types.is_numeric_dtype(series):
            converted = pd.to_datetime(series, unit="d", origin="1899-12-30", errors="coerce")
            if converted.notna().any():
                return converted.dt.strftime("%Y-%m-%d")

        series_str = series.astype(str).str.strip()
        series_str = series_str.replace({"": pd.NA, "nan": pd.NA, "NaT": pd.NA})

        parse_formats = [
            "%Y-%m-%d", "%Y/%m/%d",
            "%m-%d-%Y", "%m/%d/%Y",
            "%d-%m-%Y", "%d/%m/%Y",
        ]
        for fmt in parse_formats:
            parsed = pd.to_datetime(series_str, errors="coerce", format=fmt)
            if parsed.notna().any():
                return parsed.dt.strftime("%Y-%m-%d")

        # Manejo de fechas en formato MM-DD o MM/DD sin año.
        has_mmdd = series_str.str.match(r"^\d{1,2}[-/]\d{1,2}$", na=False)
        if has_mmdd.any():
            normalized = series_str.str.replace("-", "/", regex=False)
            fixed_year = 2026
            parsed_mmdd = pd.to_datetime(normalized + f"/{fixed_year}", format="%m/%d/%Y", errors="coerce")
            if parsed_mmdd.notna().any():
                return parsed_mmdd.dt.strftime("%Y-%m-%d")

        parsed = pd.to_datetime(series_str, errors="coerce", dayfirst=False)
        return parsed.dt.strftime("%Y-%m-%d")

    def parse_time(series: pd.Series) -> pd.Series:
        if pd.api.types.is_datetime64_any_dtype(series):
            return series.dt.strftime("%H:%M")
        if pd.api.types.is_timedelta64_dtype(series):
            return (series.dt.total_seconds() // 60).astype(int).apply(
                lambda minutes: f"{int(minutes // 60):02d}:{int(minutes % 60):02d}"
            )
        if pd.api.types.is_numeric_dtype(series):
            converted = pd.to_timedelta(series, unit="d", errors="coerce")
            if converted.notna().any():
                minutes = (converted.dt.total_seconds() // 60).astype('Int64')
                return minutes.apply(
                    lambda minutes: f"{int(minutes // 60):02d}:{int(minutes % 60):02d}" if pd.notna(minutes) else pd.NA
                )

        parsed = pd.to_datetime(series, errors="coerce", format="%H:%M")
        if parsed.notna().any():
            return parsed.dt.strftime("%H:%M")
        parsed = pd.to_datetime(series, errors="coerce", format="%H:%M:%S")
        if parsed.notna().any():
            return parsed.dt.strftime("%H:%M")

        return pd.to_datetime(series, errors="coerce").dt.strftime("%H:%M")

    fecha_formatted = parse_date(df[date_col])
    hora_formatted = parse_time(df[time_col])

    valid_mask = fecha_formatted.notna() & hora_formatted.notna()
    combined = pd.Series([pd.NA] * len(df), index=df.index, dtype="object")
    if valid_mask.any():
        combined_dates = fecha_formatted[valid_mask].str.cat(hora_formatted[valid_mask], sep=" ")
        parsed = pd.to_datetime(combined_dates, errors="coerce", dayfirst=False)
        combined.loc[valid_mask] = parsed.dt.strftime("%Y-%m-%d %H:%M")

    df[output_col] = combined

    if drop_originals:
        cols = [c for c in df.columns if c not in [date_col, time_col]]
        if output_col not in cols:
            cols.append(output_col)
        df = df.loc[:, cols]

    return df


def build_order_create_week(df: pd.DataFrame, fecha_hora_col: str = "Fecha Hora") -> pd.Series:
    """Construye el valor AAAA-SS a partir de una columna de fecha y hora."""
    if fecha_hora_col not in df.columns:
        raise ValueError(f"La columna '{fecha_hora_col}' no existe en los datos.")

    parsed = pd.to_datetime(df[fecha_hora_col], errors="coerce")
    iso = parsed.dt.isocalendar()
    week_series = pd.Series(pd.NA, index=df.index, dtype="object")
    valid = parsed.notna()
    if valid.any():
        week_series.loc[valid] = (
            iso.loc[valid, 'year'].astype('Int64').astype(str)
            + '-'
            + iso.loc[valid, 'week'].astype('Int64').astype(str).str.zfill(2)
        )
    return week_series


def save_data(df: pd.DataFrame, path: str) -> None:
    """Guarda el DataFrame filtrado en Excel y ajusta el ancho de las columnas."""
    try:
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Sheet1")
            worksheet = writer.sheets["Sheet1"]
            for idx, col in enumerate(df.columns, start=1):
                column_data = df.iloc[:, idx - 1].astype(str)
                max_length = max(
                    column_data.map(len).max(),
                    len(str(col))
                ) + 2
                worksheet.column_dimensions[get_column_letter(idx)].width = max_length
        print(f"Datos guardados en: {path}")
    except PermissionError:
        raise PermissionError(
            f"No se puede guardar el archivo porque está abierto o bloqueado: {path}.\n" \
            "Cierra el archivo en Excel y vuelve a ejecutar el script."
        )


def main() -> None:
    df = load_data(INPUT_FILE)
    print("Todas las columnas del archivo:", df.columns.tolist())
    df = clean_nombre_tienda(df)
    
    # 1. Resolver Fecha y Hora
    hora_cols = [c for c in df.columns if "realiz" in c.lower() and "hora" in c.lower()]
    if hora_cols:
        df["Fecha Hora"] = pd.to_datetime(df[hora_cols[0]], errors="coerce").dt.strftime("%Y-%m-%d %H:%M")
    elif "Fecha" in df.columns and "Hora" in df.columns:
        df = combine_date_time(df, date_col="Fecha", time_col="Hora", drop_originals=True)
    else:
        posibles_fechas = [c for c in df.columns if "fecha" in c.lower()]
        posibles_horas = [c for c in df.columns if "hora" in c.lower()]
        if posibles_fechas and posibles_horas:
            df = combine_date_time(df, date_col=posibles_fechas[0], time_col=posibles_horas[0], drop_originals=True)
        else:
            raise ValueError(f"No se pudieron detectar columnas de fecha/hora. Columnas encontradas: {df.columns.tolist()}")

    code_col, name_col = find_chmps_columns(df)
    custom_mapping = load_custom_chmps_mapping()
    if custom_mapping:
        mapping = custom_mapping
        print(f"Usando mapeo personalizado para chmps.")
    else:
        if code_col and name_col:
            mapping = build_chmps_mapping(df, name_col=name_col, code_col=code_col)
            print(f"Usando columnas {name_col} -> {code_col} para chmps")
        else:
            mapping = {}
            print("No se encontró mapeo automático para chmps. Necesito conocer los nombres de las columnas de referencia.")

    print("Mapeo chmps detectado (primeros 10):", dict(list(mapping.items())[:10]))

    # Eliminar columnas irrelevantes
    df = df.drop(columns=["Núm. de id. de la tienda", "Día", "Etiqueta de calificaciones del usuario"], errors="ignore")

    # 2. Resolver ID de Pedido
    pedido_cols = [c for c in df.columns if "pedido" in c.lower() and ("núm" in c.lower() or "id" in c.lower())]
    col_pedido_real = pedido_cols[0] if pedido_cols else "Núm. de pedido"
    if col_pedido_real in df.columns:
        df["Núm. de pedido sin prefijo"] = df[col_pedido_real].astype(str)
        df = add_prefix_to_column(df, column=col_pedido_real, prefix="id_")
        df = df.rename(columns={col_pedido_real: "Núm. de pedido"})
    else:
        df["Núm. de pedido"] = "SIN_ID"
        df["Núm. de pedido sin prefijo"] = "SIN_ID"

    # Agregar nueva columna "chmps" basada en columna B
    def get_chmps_value(row):
        store_key = extract_store_name(row["Nombre de la tienda"])
        if not store_key:
            return pd.NA

        normalized_key = normalize_text(store_key)
        if normalized_key in mapping:
            return mapping[normalized_key]

        # Si existen columnas M/L u otras detectadas, intentar match en la misma fila.
        if code_col and name_col:
            row_name_key = extract_store_name(row[name_col])
            if row_name_key and (row_name_key == store_key or row_name_key in store_key or store_key in row_name_key):
                return row[code_col]

        for rest, code in mapping.items():
            if rest in normalized_key or normalized_key in rest:
                return code

        # Fallback fuzzy: si los nombres sólo varían por tildes, errores menores o texto incompleto.
        fuzzy_code = get_best_fuzzy_match(store_key, mapping)
        if fuzzy_code:
            return fuzzy_code

        return pd.NA

    df["chmps"] = df.apply(get_chmps_value, axis=1)

    similar_groups = find_similar_store_groups(df, store_col="Nombre de la tienda")
    if similar_groups:
        print("\nNombres de tienda similares detectados (posibles duplicados):")
        for norm, names in list(similar_groups.items())[:20]:
            print(f" - {norm}: {names}")
        similar_report = report_similar_store_groups(df, store_col="Nombre de la tienda")
        print(f"Se detectaron {len(similar_report)} registros de tiendas similares con chmps asignado.")

    blank_suggestions = suggest_chmps_for_blank_rows(df, mapping)
    if not blank_suggestions.empty:
        print(f"\nFilas con chmps en blanco detectadas: {len(blank_suggestions)}")
        print(blank_suggestions.head(20).to_string(index=False))

    # Agregar columnas vacías requeridas en el resultado final
    df["country_code"] = "COL"
    df["order_create_week"] = build_order_create_week(df, "Fecha Hora")

    # Duplicar la columna de pedido sin prefijo para la columna C, dejando el original con id_.
    df["Núm. de pedido sin id"] = df["Núm. de pedido sin prefijo"]
    df = df.drop(columns=["Núm. de pedido sin prefijo"])

    if "Nivel de calificaciones del usuario" in df.columns:
        df["Nivel de calificaciones del usuario"] = pd.to_numeric(df["Nivel de calificaciones del usuario"], errors="coerce")
        df["Nivel de calificaciones del usuario"] = df["Nivel de calificaciones del usuario"].apply(
            lambda x: int(x / 100) if pd.notnull(x) and x >= 100 else (int(x) if pd.notnull(x) else x)
        )

    desired_order = [
        "Núm. de pedido",
        "chmps",
        "Núm. de pedido sin id",
        "Nombre de la tienda",
        "country_code",
        "Fecha Hora",
        "Nivel de calificaciones del usuario",
        "Contenido de calificaciones del usuario",
        "order_create_week",
    ]

    # Reordenar las columnas y mantener sólo las columnas finales esperadas.
    df_filtrado = df.reindex(columns=desired_order)
    df_filtrado.columns = [
        "order_id",
        "chmps",
        "order_id_short",
        "shop_name",
        "country_code",
        "order_create_time_local",
        "rating_stars",
        "rating_comment",
        "order_create_week",
    ]

    show_summary(df_filtrado)

    print(
        "\nTransformación aplicada automáticamente, columnas E y F eliminadas del origen, columnas reordenadas y se agregaron "
        "country_code y order_create_week vacías."
    )

    save_data(df_filtrado, OUTPUT_FILE)


if __name__ == "__main__":
    main() 