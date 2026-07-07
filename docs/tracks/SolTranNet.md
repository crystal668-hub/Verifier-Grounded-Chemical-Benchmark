# SolTranNet Backend

Status: backend capability document, not a registered formal benchmark track.

## Purpose

This backend wraps SolTranNet through the Ersilia `eos6oli` Docker image to
predict a logS-style aqueous solubility value from a single-component
small-molecule SMILES.

## Property

| Verifier property | Model output | Meaning |
|---|---|---|
| `soltrannet_log_s` | `solubility` | SolTranNet aqueous solubility prediction, treated as a logS-style scalar for verifier scoring. |

## Runtime

Default development runtime:

```yaml
soltrannet:
  runtime: external_docker
  image: ersiliaos/eos6oli:v1.0.0
  container_name: vgb-soltrannet-eos6oli
  host: 127.0.0.1
  port: 18081
  startup_timeout_seconds: 60
  prediction_timeout_seconds: 30
```

If `SOLTRANNET_BASE_URL` or `soltrannet.base_url` is set, the backend calls that
service and does not manage a Docker container.

## Environment Check

```bash
uv run python scripts/check_soltrannet_env.py --smiles CCO
```

The script prints structured JSON with runtime metadata and a sample
prediction.

## Limitations

- The backend accepts one single-component SMILES at a time.
- The Ersilia output field is `solubility`; the verifier maps it to
  `soltrannet_log_s`.
- External Docker is the development deployment path. A future official
  verifier image should switch this backend to `runtime: local` while keeping
  the property script and result schema unchanged.
