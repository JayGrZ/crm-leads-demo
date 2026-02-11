"""
Scraper de Google Maps: busca negocios por barrio y categoría (CSV),
extrae nombre, teléfono, dirección; guarda en Supabase sin duplicados por teléfono.
"""
import csv
import re
import time
from typing import Dict, List, Optional
from urllib.parse import quote_plus

from playwright.sync_api import Page, sync_playwright

from test_conexion import get_supabase_client

CSV_BARRIOS = "barrios_prioridad.csv"


def leer_barrios(csv_path: str = CSV_BARRIOS) -> List[Dict[str, str]]:
    """Lee el CSV (barrio, poblacion, categoria). Si no hay categoria, usa 'Bares'."""
    barrios: List[Dict[str, str]] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("barrio"):
                continue
            cat = (row.get("categoria") or "Bares").strip() or "Bares"
            barrios.append({
                "barrio": row["barrio"].strip(),
                "poblacion": row.get("poblacion", "").strip(),
                "categoria": cat,
            })
    return barrios


def aceptar_cookies(page: Page, timeout_ms: int = 5000) -> None:
    """Acepta popup de cookies (Aceptar todo, Aceptar, Agree)."""
    posibles = ["Aceptar todo", "Aceptar", "Agree"]
    limite = time.time() + timeout_ms / 1000.0
    while time.time() < limite:
        try:
            for txt in posibles:
                btn = page.get_by_role("button", name=txt)
                if btn and btn.is_visible():
                    btn.click()
                    time.sleep(1)
                    return
        except Exception:
            pass
        time.sleep(0.5)


def limpiar_nombre(nombre: str) -> str:
    """Quita números iniciales y caracteres raros del nombre."""
    if not nombre:
        return nombre
    s = re.sub(r"^\s*[\d]+[\.\)]\s*", "", nombre.strip())
    s = re.sub(r"^[\·\-\–\—]\s*", "", s)
    return s.strip() or nombre.strip()


def guardar_en_supabase(
    nombre: str,
    telefono: Optional[str],
    direccion: Optional[str],
    barrio: str,
    poblacion: int,
    categoria: str = "Bar",
) -> None:
    """Guarda en Supabase si el teléfono no existe ya."""
    print(f"[DB] Intentando guardar: {nombre}...", flush=True)
    try:
        supabase = get_supabase_client()
        telefono_normalizado = (telefono or "").strip()
        if telefono_normalizado:
            print(f"[DB] Comprobando si el teléfono {telefono_normalizado} ya existe...", flush=True)
            existing = (
                supabase.table("negocios")
                .select("id")
                .eq("telefono", telefono_normalizado)
                .limit(1)
                .execute()
            )
            if existing.data:
                print(f"[SKIP] Ya existe con teléfono {telefono_normalizado}", flush=True)
                return
        data = {
            "nombre": nombre,
            "telefono": telefono_normalizado or None,
            "barrio": barrio,
            "poblacion": poblacion,
            "categoria": categoria,
        }
        supabase.table("negocios").insert(data).execute()
        print(f"[DB] ¡Guardado con éxito! {nombre}", flush=True)
    except Exception as e:
        print(f"[ERROR] No se pudo guardar {nombre}: {e}", flush=True)


def scroll_panel_lateral(page: Page, veces: int = 6, espera_ms: int = 1200) -> None:
    """Scroll en el panel de resultados para cargar más (scroll infinito)."""
    print("[INFO] Scroll en panel lateral...", flush=True)
    for _ in range(veces):
        try:
            feed = page.locator("div[role='feed']")
            if feed.count() > 0:
                feed.first.evaluate("el => el.scrollBy(0, 400)")
            else:
                page.keyboard.press("PageDown")
        except Exception:
            page.keyboard.press("PageDown")
        page.wait_for_timeout(espera_ms)


def buscar_negocios_en_barrio(
    page: Page, barrio: str, poblacion: int, categoria: str = "Bares"
) -> None:
    """Busca en Maps la categoría en el barrio; extrae nombre, teléfono, dirección; guarda cada uno."""
    query = f"{categoria} en {barrio}"
    print(f"\n=== Buscando: {query} ===", flush=True)
    url = f"https://www.google.com/maps/search/{quote_plus(query)}"
    page.goto(url, wait_until="commit")
    page.wait_for_timeout(5000)
    aceptar_cookies(page, timeout_ms=5000)
    time.sleep(3)
    scroll_panel_lateral(page, veces=6, espera_ms=1200)

    cards_initial = page.query_selector_all("div[role='article']")
    num_tarjetas = min(len(cards_initial), 20)

    for idx in range(num_tarjetas):
        cards = page.query_selector_all("div[role='article']")
        if idx >= len(cards):
            break
        card = cards[idx]
        try:
            card.scroll_into_view_if_needed()
            page.wait_for_timeout(400)
            card.click()
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                time.sleep(5)

            cards_fresh = page.query_selector_all("div[role='article']")
            card_fresh = cards_fresh[idx] if idx < len(cards_fresh) else None
            nombre = None
            if card_fresh:
                name_el = card_fresh.query_selector("div.fontHeadlineSmall")
                if name_el:
                    nombre = name_el.inner_text().strip()
                else:
                    name_aria = card_fresh.query_selector("[aria-label]")
                    if name_aria:
                        nombre = name_aria.get_attribute("aria-label") or name_aria.inner_text()
                        if nombre:
                            nombre = nombre.strip()
            if not nombre:
                try:
                    panel_el = page.query_selector("h1 span, h1, .DUwDvf, .fontHeadlineSmall")
                    if panel_el:
                        cand = panel_el.inner_text().strip()
                        if cand and cand not in ("Resultados", "Results"):
                            nombre = cand
                except Exception:
                    pass
            if nombre:
                nombre = limpiar_nombre(nombre)

            direccion = None
            try:
                loc = page.locator("button[data-item-id*='address'] div[aria-label], span[aria-label*='Address'], button[aria-label*='Dirección']")
                if loc.count() > 0:
                    direccion = loc.first.get_attribute("aria-label") or loc.first.inner_text()
            except Exception:
                pass

            telefono = None
            try:
                tel_el = page.query_selector("[aria-label^='Teléfono:'], [aria-label^='Teléfono:']")
                if tel_el:
                    raw = tel_el.get_attribute("aria-label") or tel_el.inner_text()
                    if raw:
                        solo = re.sub(r"[^\d]", "", raw)
                        if len(solo) == 9 and solo[0] in "6789":
                            telefono = solo
                if not telefono:
                    detalle = page.inner_text("body")
                    for patron in [re.compile(r"\b[6789]\d{8}\b"), re.compile(r"[6789][\d\s\-\(\)]{8,}")]:
                        m = patron.search(detalle)
                        if m:
                            solo = re.sub(r"[^\d]", "", m.group(0))
                            if len(solo) == 9 and solo[0] in "6789":
                                telefono = solo
                                break
            except Exception:
                pass

            if not telefono:
                print(f"[INFO] Saltando {nombre} por falta de teléfono válido.", flush=True)
                continue

            guardar_en_supabase(nombre, telefono, direccion, barrio, poblacion, categoria)
        except Exception as e:
            print(f"[ERROR] Tarjeta {idx+1}: {e}", flush=True)


def main() -> None:
    try:
        supabase = get_supabase_client()
        supabase.table("negocios").delete().eq("telefono", "3(1031)").execute()
        print("[INFO] Limpieza teléfono de prueba.", flush=True)
    except Exception:
        pass

    barrios = leer_barrios()
    if not barrios:
        print("No hay barrios en el CSV.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=200)
        page = browser.new_page()
        page.set_default_timeout(60_000)
        for item in barrios:
            barrio = item["barrio"]
            try:
                poblacion = int(item.get("poblacion") or "0")
            except ValueError:
                poblacion = 0
            categoria = item.get("categoria") or "Bares"
            try:
                buscar_negocios_en_barrio(page, barrio, poblacion, categoria)
            except Exception as e:
                print(f"[ERROR] Barrio '{barrio}': {e}", flush=True)
        browser.close()


if __name__ == "__main__":
    main()
