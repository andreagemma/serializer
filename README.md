# serializer

`serializer` salva oggetti Python in byte, file o stream usando un formato
versionato e auto-descrittivo. Preferisce `dill`, usa `pickle` con un warning se
`dill` non è disponibile e carica i compressori opzionali solo quando servono.

> **Sicurezza:** come `pickle` e `dill`, questa libreria può eseguire codice in
> fase di caricamento. Non deserializzare mai dati provenienti da fonti non fidate.

## Installazione

```bash
pip install serializer
```

Per tutti i compressori opzionali:

```bash
pip install "serializer[compression]"
```

Il pacchetto richiede Python 3.10 o successivo. `dill` è una dipendenza standard;
il fallback a `pickle` copre anche installazioni minimali eseguite con `--no-deps`.

## API standard

```python
import serializer

payload = serializer.dumps({"answer": 42}, compression="gzip", level=7)
value = serializer.loads(payload)  # il codec è registrato nel payload

serializer.dump(value, "state.srl", compression="lzma")
restored = serializer.load("state.srl")
```

`dump` e `load` accettano sia percorsi sia stream binari aperti. Gli stream
forniti dal chiamante non vengono chiusi.

```python
from io import BytesIO
import serializer

stream = BytesIO()
serializer.dump([1, 2, 3], stream, compression="zlib")
stream.seek(0)
assert serializer.load(stream) == [1, 2, 3]
```

## API fluent / method chaining

`Serializer` è una configurazione immutabile e riutilizzabile. Ogni metodo di
configurazione restituisce una nuova istanza; `dump` restituisce l'istanza stessa
per concatenare più scritture.

```python
from serializer import Serializer

codec = (
    Serializer()
    .using("gzip")
    .at_level(9)
    .with_backend("auto")  # dill, poi pickle come fallback
    .atomic()
)

codec.dump({"one": 1}, "one.srl").dump({"two": 2}, "two.srl")
assert codec.load("one.srl") == {"one": 1}
```

Usare `.strict()` per trasformare l'assenza di un compressore richiesto in
`MissingDependencyError`, invece del fallback senza compressione.

## Compressioni

Sempre disponibili perché incluse nella libreria standard:

- `gzip`, `bz2`, `lzma`, `zlib`, `zip`
- `None` / `"none"` per nessuna compressione
- `"auto"` per preferire Zstandard e ripiegare su gzip

Opzionali e importate in modo lazy:

- `zstd` (`zstandard`)
- `lz4` (`lz4`)
- `snappy` (`python-snappy`)
- `blosclz`, `lz4hc`, `blosc-zlib`, `blosc-zstd` (`blosc`)

Se una dipendenza opzionale manca durante la scrittura, il comportamento
predefinito emette `DependencyWarning` e crea correttamente un payload non
compresso. In lettura non viene mai finta una decompressione: se il codec
necessario manca, viene emesso il warning e sollevato `MissingDependencyError`.

## Formato e compatibilità

Ogni payload nuovo contiene versione, backend, compressione, lunghezza e checksum
CRC32. Questo permette a `loads` e `load` di riconoscere automaticamente come
leggere i dati e di rifiutare file troncati o corrotti.

Payload legacy senza header sono supportati specificando i parametri originali:

```python
obj = serializer.loads(old_bytes, compression="gzip", backend="pickle")
```

## Sviluppo e release

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
pytest
python -m build
twine check dist/*
```

La CI prova Python 3.10–3.14 su Linux, Windows e macOS. La workflow di release
costruisce wheel e sdist, li conserva come artifact e, sulle release GitHub,
pubblica su PyPI tramite Trusted Publishing.

Prima di pubblicare, sostituire `OWNER` negli URL di `pyproject.toml` con
l'account GitHub effettivo e configurare su PyPI il relativo trusted publisher.
