# Security policy

## What this tool touches

mcp-census is a measurement tool. Its attack surface is small on purpose, and
this is the whole of it:

| Surface | What happens |
|---|---|
| Network | `mcp-census indir` only: HTTP(S) `GET` to `/v0/servers` on the registry (`https://registry.modelcontextprotocol.io` by default, `--taban` to change it). `file://`, `ftp://` and other schemes are refused. No other command opens a socket. |
| Registry responses | Untrusted data. Parsed as JSON, never executed or evaluated. A page larger than 32 MiB (decompressed) is refused, so a gzip bomb cannot exhaust memory. Non-object rows are refused before they reach disk. |
| Files written | Inside the `--veri` directory only (`kayitlar*.jsonl`, `manifest*.json`, `sayim.json`, `zaman-serisi.csv`), plus the paths you pass to `--yaz` / `--ozet`. `--surum` becomes part of a file name and is restricted to `[A-Za-z0-9._+-]` without `..`. |
| Credentials | None. No token, API key or environment secret is read. |
| Dependencies | None at runtime (standard library only). `pytest` is a development dependency. |
| Subprocesses | None. |

The `Sayim` workflow has `contents: write` because it commits the monthly
count. Its only input (`azami_sayfa`) is passed through an environment
variable and validated as an integer; it is never pasted into a shell script.
A partial (trial) run commits nothing. The `Yayinla` workflow publishes to
PyPI with Trusted Publishing (OIDC): there is no stored PyPI token.

## What the numbers do not mean

"23% of servers declare no `repository`" is an **auditability** measurement,
not a security finding. mcp-census does not read any server's code and does
not verify that a declared repository exists or matches the package. For that,
see [mcp-vet](https://github.com/Furkiozknn/mcp-vet).

## Reporting a vulnerability

Please report privately through
[GitHub Security Advisories](https://github.com/Furkiozknn/mcp-census/security/advisories/new)
rather than a public issue. If that page is not available to you, open an
issue that says only "security contact wanted" (no details) and a private
channel will be arranged. Especially interesting:

- a registry response (or `--taban` server) that makes mcp-census write
  outside `--veri`, hang, or exhaust memory
- a way to make the `Sayim` workflow commit something other than a full count
- a count that is silently wrong for well-formed registry data

Supported version: the latest release and `master`.
