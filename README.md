# Magazzino Locale

Applicativo web locale per gestire articoli, giacenze, movimenti di magazzino e aggiornamento prezzi nei file Excel delle offerte.

## Requisiti

- Windows per l'uso aziendale previsto.
- Python 3.11 o superiore disponibile come comando `python`.
- Microsoft Excel installato sul PC/server se bisogna aggiornare file `.xls`.

## Installazione

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Configurazione

Le impostazioni predefinite creano database e cartelle sotto `data/`.

Variabili utili:

```powershell
$env:MAG_DATABASE="C:\Magazzino\data\magazzino.sqlite3"
$env:MAG_OFFERS_DIR="C:\Magazzino\offerte"
$env:MAG_BACKUP_DIR="C:\Magazzino\backup"
$env:MAG_EXCEL_SHEET="Offerta"
$env:MAG_EXCEL_SKU_COLUMN="A"
$env:MAG_EXCEL_PRICE_COLUMN="D"
$env:MAG_EXCEL_DATA_START_ROW="2"
```

## Avvio

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Su Windows usa il file batch, che non richiede modifiche alla policy PowerShell:

```powershell
.\start.bat
```

In alternativa, se vuoi usare `start.ps1` e PowerShell blocca gli script:

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

Dal PC server: `http://localhost:8000`.
Da altri PC nella stessa rete: `http://IP_DEL_SERVER:8000`.

## Excel

Mettere i file `.xlsx`, `.xlsm` e `.xls` nella cartella offerte configurata. L'app crea sempre una copia nella cartella backup prima di modificare il file originale.

Per i file `.xls`, il server deve avere Excel installato e il file non deve essere aperto da altri utenti.

## Test

```powershell
pytest
```
