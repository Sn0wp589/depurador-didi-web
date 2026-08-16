from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pandas as pd
import io
import sys
import os

# Asegurar que importamos Script de la raiz
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from Script import (
    add_prefix_to_column,
    build_order_create_week,
    combine_date_time,
    extract_store_name,
    find_chmps_columns,
    get_best_fuzzy_match,
    normalize_text,
)

def format_shop_name_like_didi(raw_name) -> str:
    if pd.isna(raw_name) or not str(raw_name).strip():
        return ""
    clean_name = extract_store_name(raw_name)
    if not clean_name:
        return str(raw_name)
    return f"KFC({clean_name.title()})"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# El diccionario gigante que creamos
CHMPS_MAPPING_DICT = {
    "altavista usme": "57K5123",
    "americas": "57K5045",
    "arkadia": "57K5095",
    "av 6": "57K5053",
    "av chile": "57K5101",
    "av jimenez": "57K5063",
    "av junin": "57K5072",
    "av sexta": "57K5053",
    "belen molinos": "57K5183",
    "bosa piamonte": "57K5147",
    "bosa": "57K5059",
    "buenavista": "57K5111",
    "bulevar niza": "57K5021",
    "c c cencosud": "57K5185",
    "cabecera bucaramanga": "57K5099",
    "cabecera": "57K5099",
    "cacique bucaramanga": "57K5117",
    "cacique": "57K5117",
    "calasanz": "57K5139",
    "calle 10": "57K5014",
    "calle 100": "57K5017",
    "calle 140 cedritos": "57K5012",
    "calle 85": "57K5039",
    "caney": "57K5100",
    "caracoli": "57K5098",
    "caracoli bucaramanga": "57K5098",
    "caribe plaza ctg": "57K5122",
    "caribe plaza": "57K5122",
    "carnaval barranquilla": "57K5125",
    "carnaval": "57K5125",
    "carrera 43": "57K5081",
    "castilla": "57K5118",
    "cedritos": "57K5012",
    "centro comercial ciudad tunal": "57K5036",
    "chapinero": "57K5057",
    "chipichape": "57K5052",
    "ciudad amurallada": "57K5077",
    "ciudad cordoba": "57K5151",
    "ciudad jardin": "57K5173",
    "corales": "57K5187",
    "distrito 21 atlantico": "57K5179",
    "diverplaza": "57K5096",
    "ecoplaza mosquera": "57K5106",
    "el eden": "57K5092",
    "el ensueno": "57K5079",
    "ensueno": "57K5079",
    "exito fontibon": "57K5032",
    "ferias": "57K5064",
    "fontanar": "57K5083",
    "fontibon centro": "57K5085",
    "galerias": "57K5025",
    "gran estacion": "57K5062",
    "gran plaza bosa": "57K5059",
    "hayuelos": "57K5027",
    "iserra": "57K5004",
    "junin": "57K5072",
    "kennedy": "57K5073",
    "la central medellin": "57K5071",
    "la central": "57K5071",
    "la cordialidad": "57K5159",
    "la florida": "57K5029",
    "laureles": "57K5056",
    "lourdes": "57K5074",
    "madrid": "57K5157",
    "mayorca medellin": "57K5070",
    "mayorca ii": "57K5070",
    "megamall bucaramanga": "57K5120",
    "megamall": "57K5120",
    "mercurio": "57K5171",
    "metropolis": "57K5002",
    "modelia": "57K5084",
    "multiplaza": "57K5175",
    "normandia": "57K5105",
    "palmeto": "57K5038",
    "parkway": "57K5075",
    "parque alegra": "57K5133",
    "parque arbolatta": "57K5169",
    "parque ospina": "57K5144",
    "paso ancho": "57K5137",
    "plaza americas ii": "57K5080",
    "plaza central": "57K5048",
    "plaza del sol": "57K5046",
    "plaza fabricato": "57K5119",
    "plaza de las americas 2": "57K5080",
    "premium plaza medellin": "57K5055",
    "premium plaza": "57K5055",
    "puerta del norte": "57K5112",
    "quirigua": "57K5132",
    "restrepo": "57K5065",
    "sta fe bogota": "57K5018",
    "sta fe medellin": "57K5019",
    "san fernando": "57K5135",
    "san martin": "57K5047",
    "san pedro heredia": "57K5168",
    "san rafael": "57K5094",
    "santa helenita": "57K5091",
    "santa paula": "57K5003",
    "santafe bogota": "57K5018",
    "santafe medellin": "57K5019",
    "shaio": "57K5076",
    "soacha parque": "57K5178",
    "suba bogota": "57K5113",
    "suba pinar bogota": "57K5158",
    "suba pinar": "57K5158",
    "suba": "57K5113",
    "terminal cali": "57K5127",
    "terminal del sur medellin": "57K5124",
    "terminal del sur": "57K5124",
    "tesoro": "57K5006",
    "tintal plaza": "57K5090",
    "tintal": "57K5090",
    "toberin": "57K5068",
    "tunal": "57K5036",
    "unicentro bogota": "57K5037",
    "unicentro cali": "57K5023",
    "unicentro medellin": "57K5109",
    "unicentro": "57K5023",
    "unico bucaramanga": "57K5174",
    "unico cali": "57K5022",
    "venecia": "57K5142",
    "ventura cucuta": "57K5130",
    "ventura terreros": "57K5061",
    "versalles palmira": "57K5121",
    "villa del mar": "57K5140",
    "villa del rio": "57K5145",
    "viva envigado": "57K5078",
    "viva fontibon": "57K5032",
    "unico": "57K5022",
    "chia": "57K5001",
    "iserra 100": "57K5004",
    "salitre plaza": "57K5005",
    "el tesoro": "57K5006",
    "atlantis": "57K5007",
    "plaza imperial": "57K5011",
    "calle 10 relo": "57K5014",
    "calima": "57K5016",
    "santa fe": "57K5018",
    "llano grande palmira": "57K5020",
    "galerias relo": "57K5025",
    "unico villavicencio": "57K5026",
    "roosevelt": "57K5028",
    "parque comercial la florida": "57K5029",
    "portal del quindio": "57K5030",
    "la estacion ibague": "57K5031",
    "exito galerias fontibon": "57K5032",
    "viva villavicencio": "57K5033",
    "plaza de las americas": "57K5034",
    "centro mayor": "57K5035",
    "ciudad tunal": "57K5036",
    "palmetto cali": "57K5038",
    "cafam la floresta": "57K5040",
    "cc mayorca medellin": "57K5042",
    "portal de la 80": "57K5043",
    "buena vista": "57K5044",
    "plaza del sol barranquilla": "57K5046",
    "san martin cartagena": "57K5047",
    "cc antares": "57K5049",
    "parque la colina": "57K5050",
    "viva barranquilla relo": "57K5051",
    "cc chipichape": "57K5052",
    "avenida 6a": "57K5053",
    "ibague": "57K5054",
    "portal del prado": "57K5060",
    "av jimenez": "57K5063",
    "kfc titan": "57K5066",
    "unico barranquilla": "57K5067",
    "alcala": "57K5069",
    "centro comercial mayorca": "57K5070",
    "centro comercial buenos aires": "57K5071",
    "centro historico": "57K5077",
    "cc exito viva envigado": "57K5078",
    "gran plaza el ensueno": "57K5079",
    "centro comercial plaza de las americas": "57K5080",
    "cr 43": "57K5081",
    "mall plaza el castillo": "57K5082",
    "fontibon": "57K5085",
    "fundadores": "57K5086",
    "7 17": "57K5088",
    "mall plaza manizales": "57K5089",
    "acqua 74": "57K5093",
    "paseo san rafael": "57K5094",
    "centro pereira": "57K5097",
    "parque caracoli": "57K5098",
    "avenida chile": "57K5101",
    "san pedro plaza": "57K5102",
    "viva tunja": "57K5103",
    "unicentro pereira": "57K5104",
    "ecoplaza": "57K5106",
    "paseo villa del rio": "57K5107",
    "parque arboleda": "57K5108",
    "nuestro bogota": "57K5110",
    "cosmocentro": "57K5114",
    "jardin plaza": "57K5115",
    "centro armenia": "57K5116",
    "palmira versalles": "57K5121",
    "terminal sur": "57K5124",
    "alamedas": "57K5126",
    "nuestro monteria": "57K5128",
    "jardin plaza cucuta": "57K5129",
    "guacari": "57K5131",
    "parque alegra fc": "57K5133",
    "guatapuri": "57K5134",
    "7 de agosto": "57K5136",
    "pasoancho": "57K5137",
    "parque de los novios": "57K5138",
    "calazans": "57K5139",
    "cc plaza claro": "57K5141",
    "el leon": "57K5143",
    "20 de julio": "57K5148",
    "viva sincelejo": "57K5149",
    "mayales plaza comercial": "57K5150",
    "melgar": "57K5152",
    "7 12": "57K5153",
    "c c plaza del sol dosquebradas": "57K5154",
    "rodadero": "57K5156",
    "av cordialidad": "57K5159",
    "zipaquira": "57K5160",
    "sogamoso": "57K5161",
    "cartago": "57K5162",
    "la herradura": "57K5163",
    "c c buenavista monteria": "57K5164",
    "mall plaza cali": "57K5165",
    "san nicolas rio negro": "57K5166",
    "florida ii": "57K5167",
    "av pedro de heredia": "57K5168",
    "arbolatta": "57K5169",
    "san silvestre": "57K5172",
    "k174 multiplaza bogota": "57K5175",
    "neiva cra 7": "57K5176",
    "plaza de las americas 3": "57K5177",
    "distrito 21": "57K5179",
    "duitama": "57K5180",
    "avenida 30 de agosto": "57K5181",
    "turbaco": "57K5182",
    "belen": "57K5183",
    "cc cenco limonar": "57K5185",
    "los corales": "57K5187"
}

def process_didi(df: pd.DataFrame) -> pd.DataFrame:
    hora_cols = [c for c in df.columns if "hora" in c.lower() and "fecha" in c.lower()]
    if hora_cols:
        df["Fecha Hora"] = pd.to_datetime(df[hora_cols[0]], errors="coerce").dt.strftime("%Y-%m-%d %H:%M")
    elif "Fecha" in df.columns and "Hora" in df.columns:
        df = combine_date_time(df, date_col="Fecha", time_col="Hora", drop_originals=True)
    else:
        df["Fecha Hora"] = pd.NA

    code_col, name_col = find_chmps_columns(df)
    mapping = CHMPS_MAPPING_DICT

    df = df.drop(columns=["Núm. de id. de la tienda", "Día", "Etiqueta de calificaciones del usuario"], errors="ignore")
    
    if "Nombre de la tienda" in df.columns:
        df["Nombre de la tienda"] = df["Nombre de la tienda"].apply(format_shop_name_like_didi)

    pedido_cols = [c for c in df.columns if "pedido" in c.lower() and ("núm" in c.lower() or "id" in c.lower())]
    col_pedido_real = pedido_cols[0] if pedido_cols else "Núm. de pedido"
    if col_pedido_real in df.columns:
        df["Núm. de pedido sin prefijo"] = df[col_pedido_real].astype(str)
        df = add_prefix_to_column(df, column=col_pedido_real, prefix="id_")
        df = df.rename(columns={col_pedido_real: "Núm. de pedido"})
    else:
        df["Núm. de pedido"] = "SIN_ID"
        df["Núm. de pedido sin prefijo"] = "SIN_ID"

    def get_chmps_value(row):
        store_key = extract_store_name(row.get("Nombre de la tienda", ""))
        if not store_key:
            return pd.NA
        normalized_key = normalize_text(store_key)
        if normalized_key in mapping:
            return mapping[normalized_key]
        for rest, code in mapping.items():
            if rest in normalized_key or normalized_key in rest:
                return code
        fuzzy_code = get_best_fuzzy_match(store_key, mapping)
        return fuzzy_code if fuzzy_code else pd.NA

    df["chmps"] = df.apply(get_chmps_value, axis=1)
    df["country_code"] = "COL"
    df["order_create_week"] = build_order_create_week(df, "Fecha Hora")
    df["Núm. de pedido sin id"] = df["Núm. de pedido sin prefijo"]

    if "Nivel de calificaciones del usuario" in df.columns:
        df["Nivel de calificaciones del usuario"] = pd.to_numeric(df["Nivel de calificaciones del usuario"], errors="coerce")
        df["Nivel de calificaciones del usuario"] = df["Nivel de calificaciones del usuario"].apply(
            lambda x: int(x / 100) if pd.notnull(x) and x >= 100 else (int(x) if pd.notnull(x) else x)
        )

    desired_order = [
        "Núm. de pedido", "chmps", "Núm. de pedido sin id",
        "Nombre de la tienda", "country_code", "Fecha Hora",
        "Nivel de calificaciones del usuario",
        "Contenido de calificaciones del usuario",
        "order_create_week",
    ]
    df_filtrado = df.reindex(columns=desired_order)
    df_filtrado.columns = [
        "order_id", "chmps", "order_id_short", "shop_name",
        "country_code", "order_create_time_local",
        "rating_stars", "rating_comment", "order_create_week",
    ]
    df_filtrado = df_filtrado.sort_values(by="shop_name", na_position="last")
    return df_filtrado

def process_rappi(df: pd.DataFrame) -> pd.DataFrame:
    mapping = CHMPS_MAPPING_DICT

    def get_chmps_value(row):
        store_key = extract_store_name(str(row.get("Tienda", "")))
        if not store_key:
            return pd.NA
        normalized_key = normalize_text(store_key)
        if normalized_key in mapping:
            return mapping[normalized_key]
        for rest, code in mapping.items():
            if rest in normalized_key or normalized_key in rest:
                return code
        fuzzy_code = get_best_fuzzy_match(store_key, mapping)
        return fuzzy_code if fuzzy_code else pd.NA

    df["chmps"] = df.apply(get_chmps_value, axis=1)
    df["country_code"] = "COL"
    
    if "ID Orden" in df.columns:
        df["order_id_short"] = df["ID Orden"].astype(str)
        df["order_id"] = "id_" + df["ID Orden"].astype(str)
    else:
        df["order_id_short"] = "SIN_ID"
        df["order_id"] = "SIN_ID"
        
    df["shop_name"] = df.get("Tienda", "")
    df["shop_name"] = df["shop_name"].apply(format_shop_name_like_didi)
    df["country_code"] = "COL"
    
    if "Fecha de creación" in df.columns:
        parsed_dates = pd.to_datetime(df["Fecha de creación"], format='%d/%m/%Y - %I:%M %p', errors='coerce')
        df["order_create_time_local"] = parsed_dates.dt.strftime("%Y-%m-%d %H:%M")
        
        iso = parsed_dates.dt.isocalendar()
        valid = parsed_dates.notna()
        week_series = pd.Series(pd.NA, index=df.index, dtype="object")
        if valid.any():
            week_series.loc[valid] = (
                iso.loc[valid, 'year'].astype('Int64').astype(str)
                + '-'
                + iso.loc[valid, 'week'].astype('Int64').astype(str).str.zfill(2)
            )
        df["order_create_week"] = week_series
    else:
        df["order_create_time_local"] = pd.NA

    df["rating_stars"] = pd.to_numeric(df.get("Calificación", pd.NA), errors="coerce")
    df["rating_comment"] = df.get("Razón", pd.NA)

    desired_order = [
        "order_id", "chmps", "order_id_short", "shop_name",
        "country_code", "order_create_time_local",
        "rating_stars", "rating_comment", "order_create_week",
    ]
    df_filtrado = df.reindex(columns=desired_order)
    df_filtrado = df_filtrado.sort_values(by="shop_name", na_position="last")
    return df_filtrado

@app.get("/api/debug")
async def debug_excel():
    try:
        df = pd.read_excel("DATA_AGREGADORES_DIDI_13_08.xlsx")
        # Check if shop_name or similar column exists
        col = "shop_name" if "shop_name" in df.columns else df.columns[3] if len(df.columns) > 3 else df.columns[0]
        names = df[col].dropna().unique().tolist()[:50]
        return {"column_used": col, "sample_names": names}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/index")
async def process_file(file: UploadFile = File(...), platform: str = Form(...)):
    contents = await file.read()
    
    # Leer archivo
    if file.filename.endswith('.csv'):
        try:
            df = pd.read_csv(io.BytesIO(contents), sep=';', encoding='utf-8')
        except:
            df = pd.read_csv(io.BytesIO(contents), sep=';', encoding='latin1')
    else:
        df = pd.read_excel(io.BytesIO(contents))
        
    # Procesar
    if platform.lower() == 'didi':
        processed_df = process_didi(df)
    else:
        processed_df = process_rappi(df)
        
    # Stats
    total_filas = len(df)
    datos_procesados = len(processed_df)
    sin_asignar = int(processed_df['chmps'].isna().sum())
    tiendas_unicas = int(processed_df['chmps'].nunique())
    
    import base64

    # Extraer tiendas sin asignar (frecuencia)
    unassigned_df = processed_df[processed_df['chmps'].isna()]
    if not unassigned_df.empty:
        counts = unassigned_df['shop_name'].value_counts().reset_index()
        counts.columns = ['tienda', 'cantidad']
        unassigned_stores = counts.to_dict('records')
    else:
        unassigned_stores = []

    # Guardar a excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        processed_df.to_excel(writer, index=False, sheet_name='Sheet1')
        
    file_base64 = base64.b64encode(output.getvalue()).decode('utf-8')
    
    preview_df = processed_df.head(30).fillna("")
    preview_data = preview_df.to_dict('records')

    return JSONResponse(content={
        "file_base64": file_base64,
        "filename": f"{platform}_procesado.xlsx",
        "stats": {
            "total_filas": total_filas,
            "datos_procesados": datos_procesados,
            "sin_asignar": sin_asignar,
            "tiendas_unicas": tiendas_unicas
        },
        "unassigned_stores": unassigned_stores,
        "preview_data": preview_data
    })

# Servir el frontend localmente
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(frontend_path, "index.html"))

    @app.get("/{filename}")
    async def serve_files(filename: str):
        file_path = os.path.join(frontend_path, filename)
        if os.path.exists(file_path):
            return FileResponse(file_path)
        return JSONResponse(status_code=404, content={"message": "File not found"})

