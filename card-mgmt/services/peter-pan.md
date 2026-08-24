# peter-pan

Owned by the Authorizer squad (not Cards & Logistics), but sits directly in the
card-creation/embossing dataprep path — Rivendell, Kuchiyose, Pinboard, and
Diario-do-Povo all call it, and it's the only service that talks to the
Thales payShield 10K HSM.

## Role

- Sole interface to the HSM (`Thales payShield 10K`) for every crypto
  operation: generate/validate CVV (`:CW`/`:CY`), PIN block (`:EA`/`:EB`/`:CC`),
  ARQC/secure-message (`:KW`/`:KY`), AAV/IAV, etc.
- `POST /api/operations/execute` (`execute-operations`) is the generic,
  batched entry point used by card-creation dataprep — Rivendell sends it a
  map of named operations (`{:cvv1 {...} :cvv2 {...} :cvv3 {...}
  :pinblock-embosser {...}}`) in one call; `controller.operations/execute!`
  runs each op and returns a map keyed the same way. Allowed callers:
  `rivendell`, `diario-do-povo`, `pinboard`, `kuchiyose`.
- A separate, deprecated code path (`compute-cvv`, called from Kuchiyose's
  `card-to-prepare` topic) still runs in parallel for every card creation —
  it hardcodes `cvc2` service-code to `"000"` and `chip-cvv` to `"999"` (this
  is *correct*, not a bug: card networks require CVV2 to always be generated
  with service-code `000` and chip-CVV with `999` — it's a crypto convention,
  not a shortcut). This path does **not** feed the embossing file; it's kept
  only "until Kuchiyose's `card-to-prepare` is removed" per an in-code TODO.

## HSM return-code semantics (important for debugging)

`adapters/hsm.clj` `decode`:
- return-code `"00"` or `"02"` → success, decoded response.
- return-code `"01"` → **also resolves the Future successfully**, with value
  `:nok` (not an exception!). Downstream `extract-key` does `(get :nok :key)`
  → `nil`, silently, no error. This is a real mechanism by which a single
  operation inside an `execute-operations` batch can come back empty while
  the overall HTTP call still returns 200 and the other operations in the
  same batch succeed normally.
- anything else → `Future/exception` (a genuine, loud failure — logged as
  `error-calling-hsm`).

When investigating a "field X came back empty with no error" report, check
`log_type = 'hsm-response-code'` for the relevant HSM command and look for
`return-code` values other than `"00"`/`"02"` in the exact window — see
`log-forensics` skill for the query. (In the CSEO-6946 investigation this came
back clean for the affected cards, which ruled out an HSM-level cause and
pointed the investigation at the Rivendell-side response-building code
instead — see `embossing.md`'s debug pattern section.)

## Known command ↔ key mapping

`:CW`/`:CY` → `:cvks` · `:EA`/`:EB`/`:CC` → `:zpks`+`:pvks`+decimalization
tables · `:KW`/`:KY` → `:mk-ac`/`:mk-smi`/`:mk-smc` · `:M0` → `:zeks`/`:aav` ·
`:A6` → import/translate ZPK under ZMK · `:B2`/`:B3` → ping/health.

## Notable constraints

- Persistent Finagle connections to 6 HSMs (3 DCs × 2 HSM/DC); ~80 TCP
  socket/HSM ceiling on legacy network gear forces `peter-pan` to run pinned
  to a small, fixed pod count (horizontal scaling effectively disabled) —
  don't be surprised if it looks under-provisioned relative to its traffic.
- Config (including which HSM IPs are in rotation) lives on a separate
  `config` branch: `peter-pan/blob/config/src/prod/peter_pan_<country>_config.json`.
