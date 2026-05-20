# zhtw-mcp-nix

Standalone Nix packaging for [zhtw-mcp](https://github.com/sysprog21/zhtw-mcp), an MCP server and CLI for linting and normalizing Traditional Chinese text.

This repository exists because the Nix package is maintained separately from the upstream application source. The flake pins the upstream `zhtw-mcp` source and provides a ready-to-run package, overlay, and formatter.

## Usage

Run the CLI directly:

```bash
nix run github:pan93412/zhtw-mcp-nix -- lint README.md
```

Register it with Claude Code without installing a global binary:

```bash
claude mcp add zhtw-mcp -- nix run github:pan93412/zhtw-mcp-nix --
```

For Codex CLI or other MCP clients, use `nix run` as the server command:

```json
{
  "mcpServers": {
    "zhtw-mcp": {
      "command": "nix",
      "args": ["run", "github:pan93412/zhtw-mcp-nix", "--"]
    }
  }
}
```

If you prefer a persistent command on `PATH`, install the package:

```bash
nix profile install github:pan93412/zhtw-mcp-nix
zhtw-mcp lint README.md
```

From a local checkout of this repository, replace `github:pan93412/zhtw-mcp-nix` with `.`.

## Flake Outputs

- `packages.default`: the `zhtw-mcp` binary package.
- `packages.zhtw-mcp`: explicit package name for consumers that do not want to rely on the default output.
- `overlays.default`: exposes `pkgs.zhtw-mcp`.
- `devShells.default`: maintenance shell with source-update and formatting tools.
- `formatter`: `nixfmt`.

## Maintenance

Update the pinned application source by changing the `zhtw-mcp-src` input in `flake.nix`, then refresh the lock file:

```bash
nix develop --command nix flake lock
nix develop --command nix build .#zhtw-mcp
```

If Cargo dependencies changed, Nix will report the expected `cargoHash`. Replace the old hash in `flake.nix`, then rebuild.

To update the pinned upstream source or OpenCC dictionaries, use the helper script:

```bash
nix develop --command scripts/update-sources.py
```

By default, the script resolves the latest `sysprog21/zhtw-mcp` and `BYVoid/OpenCC` `HEAD` revisions, updates `flake.nix`, refreshes OpenCC dictionary hashes, and updates `flake.lock` when `zhtw-mcp-src` changes.

You can pin exact revisions or update only one source:

```bash
nix develop --command scripts/update-sources.py \
  --zhtw-mcp-rev 9b977caaa4671473d4175828ed1d5970761aa192 \
  --opencc-rev 0ad13e022313ab62daf9b7ef79047b2d084a8868

nix develop --command scripts/update-sources.py --skip-opencc
nix develop --command scripts/update-sources.py --skip-zhtw-mcp
```
