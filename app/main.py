from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import Settings, get_settings
from .db import db_session, init_db
from .excel_service import backup_file, ensure_allowed_file, update_offer_file
from .repository import (
    add_update_row,
    create_item,
    create_movement,
    create_update_run,
    finish_update_run,
    get_item,
    get_update_run,
    list_items,
    list_movements,
    price_map,
    update_item,
)


app = FastAPI(title="Magazzino Locale", version="1.0.0")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")


@app.on_event("startup")
def startup() -> None:
    settings = get_settings()
    init_db(settings.database_path)
    settings.offers_dir.mkdir(parents=True, exist_ok=True)
    settings.backup_dir.mkdir(parents=True, exist_ok=True)


def settings_dep() -> Settings:
    return get_settings()


def redirect(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=303)


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, settings: Settings = Depends(settings_dep)) -> HTMLResponse:
    with db_session(settings.database_path) as conn:
        items = list_items(conn)
        movements = list_movements(conn, limit=10)
    total_value = sum(float(item["price"]) * float(item["quantity"]) for item in items)
    low_stock = [item for item in items if float(item["quantity"]) <= 0]
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "items": items,
            "movements": movements,
            "total_value": total_value,
            "low_stock": low_stock,
            "settings": settings,
        },
    )


@app.get("/items", response_model=list[dict])
def api_list_items(settings: Settings = Depends(settings_dep)) -> list[dict]:
    with db_session(settings.database_path) as conn:
        return list_items(conn)


@app.get("/articoli", response_class=HTMLResponse)
def items_page(request: Request, settings: Settings = Depends(settings_dep)) -> HTMLResponse:
    with db_session(settings.database_path) as conn:
        items = list_items(conn)
    return templates.TemplateResponse("items.html", {"request": request, "items": items})


@app.post("/items", response_model=dict)
def api_create_item(
    sku: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    quantity: float = Form(0),
    settings: Settings = Depends(settings_dep),
) -> dict:
    validate_item_payload(sku, description, price, quantity)
    with db_session(settings.database_path) as conn:
        if get_item(conn, sku.strip()):
            raise HTTPException(status_code=409, detail="SKU già esistente")
        return create_item(conn, sku, description, price, quantity)


@app.post("/articoli")
def create_item_form(
    sku: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    quantity: float = Form(0),
    settings: Settings = Depends(settings_dep),
) -> RedirectResponse:
    api_create_item(sku, description, price, quantity, settings)
    return redirect("/articoli")


@app.put("/items/{sku}", response_model=dict)
def api_update_item(
    sku: str,
    description: str = Form(...),
    price: float = Form(...),
    settings: Settings = Depends(settings_dep),
) -> dict:
    if not description.strip():
        raise HTTPException(status_code=400, detail="Descrizione obbligatoria")
    if price < 0:
        raise HTTPException(status_code=400, detail="Prezzo non valido")
    with db_session(settings.database_path) as conn:
        item = update_item(conn, sku, description, price)
        if item is None:
            raise HTTPException(status_code=404, detail="Articolo non trovato")
        return item


@app.post("/articoli/{sku}")
def update_item_form(
    sku: str,
    description: str = Form(...),
    price: float = Form(...),
    settings: Settings = Depends(settings_dep),
) -> RedirectResponse:
    api_update_item(sku, description, price, settings)
    return redirect("/articoli")


@app.get("/movimenti", response_class=HTMLResponse)
def movements_page(request: Request, settings: Settings = Depends(settings_dep)) -> HTMLResponse:
    with db_session(settings.database_path) as conn:
        items = list_items(conn)
        movements = list_movements(conn, limit=200)
    return templates.TemplateResponse(
        "movements.html",
        {"request": request, "items": items, "movements": movements},
    )


@app.post("/movements", response_model=dict)
def api_create_movement(
    sku: str = Form(...),
    movement_type: str = Form(...),
    quantity: float = Form(...),
    operator: str | None = Form(None),
    note: str | None = Form(None),
    settings: Settings = Depends(settings_dep),
) -> dict:
    if movement_type not in {"carico", "scarico"}:
        raise HTTPException(status_code=400, detail="Tipo movimento non valido")
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantità non valida")
    with db_session(settings.database_path) as conn:
        try:
            return create_movement(conn, sku.strip(), movement_type, quantity, operator, note)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/movimenti")
def create_movement_form(
    sku: str = Form(...),
    movement_type: str = Form(...),
    quantity: float = Form(...),
    operator: str | None = Form(None),
    note: str | None = Form(None),
    settings: Settings = Depends(settings_dep),
) -> RedirectResponse:
    api_create_movement(sku, movement_type, quantity, operator, note, settings)
    return redirect("/movimenti")


@app.get("/excel", response_class=HTMLResponse)
def excel_page(request: Request, settings: Settings = Depends(settings_dep)) -> HTMLResponse:
    files = sorted(
        [
            path
            for path in settings.offers_dir.glob("*")
            if path.is_file() and path.suffix.lower() in {".xlsx", ".xlsm", ".xls"}
        ],
        key=lambda item: item.name.lower(),
    )
    return templates.TemplateResponse(
        "excel.html",
        {"request": request, "files": files, "settings": settings, "run": None},
    )


@app.post("/excel/update-offers", response_model=dict)
def api_update_offers(
    files: list[str] = Form(...),
    settings: Settings = Depends(settings_dep),
) -> dict:
    with db_session(settings.database_path) as conn:
        prices = price_map(conn)
        run_id = create_update_run(conn, len(files))

        for file_name in files:
            try:
                file_path = ensure_allowed_file(settings.offers_dir / file_name, settings.offers_dir)
                backup_file(file_path, settings.backup_dir)
                results = update_offer_file(file_path, prices, settings)
                for row in results:
                    add_update_row(
                        conn,
                        run_id,
                        row.file_path,
                        row.status,
                        row.row_number,
                        row.sku,
                        row.message,
                        row.old_price,
                        row.new_price,
                    )
            except Exception as exc:
                add_update_row(conn, run_id, str(settings.offers_dir / file_name), "error", message=str(exc))

        return finish_update_run(conn, run_id)


@app.post("/excel")
def update_offers_form(
    files: list[str] = Form(...),
    settings: Settings = Depends(settings_dep),
) -> RedirectResponse:
    run = api_update_offers(files, settings)
    return redirect(f"/excel/risultato/{run['id']}")


@app.get("/excel/update-runs/{run_id}", response_model=dict)
def api_get_update_run(run_id: int, settings: Settings = Depends(settings_dep)) -> dict:
    with db_session(settings.database_path) as conn:
        run = get_update_run(conn, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Aggiornamento non trovato")
    return run


@app.get("/excel/risultato/{run_id}", response_class=HTMLResponse)
def update_run_page(request: Request, run_id: int, settings: Settings = Depends(settings_dep)) -> HTMLResponse:
    with db_session(settings.database_path) as conn:
        run = get_update_run(conn, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Aggiornamento non trovato")
    files = sorted(
        [
            path
            for path in settings.offers_dir.glob("*")
            if path.is_file() and path.suffix.lower() in {".xlsx", ".xlsm", ".xls"}
        ],
        key=lambda item: item.name.lower(),
    )
    return templates.TemplateResponse(
        "excel.html",
        {"request": request, "files": files, "settings": settings, "run": run},
    )


def validate_item_payload(sku: str, description: str, price: float, quantity: float) -> None:
    if not sku.strip():
        raise HTTPException(status_code=400, detail="SKU obbligatorio")
    if not description.strip():
        raise HTTPException(status_code=400, detail="Descrizione obbligatoria")
    if price < 0:
        raise HTTPException(status_code=400, detail="Prezzo non valido")
    if quantity < 0:
        raise HTTPException(status_code=400, detail="Giacenza iniziale non valida")
