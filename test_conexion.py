import os

from dotenv import load_dotenv
from supabase import create_client, Client


def get_supabase_client() -> Client:
    """
    Carga las variables de entorno desde .env y crea el cliente de Supabase.
    Requiere: SUPABASE_URL, SUPABASE_KEY
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(base_dir, ".env")
    load_dotenv(env_path)

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise RuntimeError(
            "Faltan SUPABASE_URL o SUPABASE_KEY en el archivo .env"
        )

    return create_client(url, key)


def insertar_negocio_prueba() -> None:
    """Inserta un bar de prueba en la tabla 'negocios'."""
    supabase = get_supabase_client()
    data = {
        "nombre": "Bar La Demo",
        "barrio": "Centro",
    }
    response = supabase.table("negocios").insert(data).execute()
    print("Inserción realizada. Respuesta de Supabase:")
    print(response.data)


def comprobar_insercion() -> None:
    """Comprueba que el registro existe consultando por nombre."""
    supabase = get_supabase_client()
    response = (
        supabase.table("negocios")
        .select("*")
        .eq("nombre", "Bar La Demo")
        .execute()
    )
    print("Comprobación de existencia del registro:")
    print(response.data)


if __name__ == "__main__":
    insertar_negocio_prueba()
    comprobar_insercion()
