#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


ZHTW_MCP_REMOTE = "https://github.com/sysprog21/zhtw-mcp.git"
OPENCC_REMOTE = "https://github.com/BYVoid/OpenCC.git"
OPENCC_DICTS = ("STPhrases.txt", "STCharacters.txt", "TWVariants.txt")


def run(args: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=None,
    )


def resolve_git_head(remote: str, name: str) -> str:
    result = run(["git", "ls-remote", remote, "HEAD"], capture=True)
    line = result.stdout.strip()
    if not line:
        raise RuntimeError(f"could not resolve HEAD for {name} from {remote}")

    return line.split()[0]


def replace_once(text: str, pattern: str, replacement: str, label: str) -> str:
    text, count = re.subn(pattern, replacement, text, count=1, flags=re.DOTALL)
    if count != 1:
        raise RuntimeError(f"{label} not found in flake.nix")

    return text


def update_zhtw_mcp_rev(text: str, rev: str) -> str:
    return replace_once(
        text,
        r'url = "github:sysprog21/zhtw-mcp/[^"]+";',
        f'url = "github:sysprog21/zhtw-mcp/{rev}";',
        "zhtw-mcp input URL",
    )


def update_opencc_rev(text: str, rev: str) -> str:
    return replace_once(
        text,
        r'openccRev = "[^"]+";',
        f'openccRev = "{rev}";',
        "openccRev",
    )


def prefetch_opencc_dict_hash(rev: str, filename: str) -> str:
    url = f"https://raw.githubusercontent.com/BYVoid/OpenCC/{rev}/data/dictionary/{filename}"
    result = run(
        ["nix", "store", "prefetch-file", "--hash-type", "sha256", "--json", url],
        capture=True,
    )
    data = json.loads(result.stdout)
    return data["hash"]


def update_opencc_hash(text: str, filename: str, hash_value: str) -> str:
    escaped = re.escape(filename)
    pattern = (
        rf'(name = "{escaped}";\s+'
        rf"path = final\.fetchurl \{{\s+"
        rf'url = openccDictUrl "{escaped}";\s+'
        rf'hash = ")[^"]+(";)'
    )
    return replace_once(text, pattern, rf"\1{hash_value}\2", f"{filename} hash block")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update zhtw-mcp and OpenCC source pins in flake.nix.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""examples:
  scripts/update-sources.py
  scripts/update-sources.py --zhtw-mcp-rev 9b977caaa4671473d4175828ed1d5970761aa192
  scripts/update-sources.py --opencc-rev 0ad13e022313ab62daf9b7ef79047b2d084a8868
  scripts/update-sources.py --skip-opencc
""",
    )
    parser.add_argument(
        "--zhtw-mcp-rev",
        help="pin github:sysprog21/zhtw-mcp to REV instead of upstream HEAD",
    )
    parser.add_argument(
        "--opencc-rev",
        help="pin BYVoid/OpenCC dictionaries to REV instead of upstream HEAD",
    )
    parser.add_argument(
        "--skip-zhtw-mcp",
        action="store_true",
        help="do not update the zhtw-mcp source pin",
    )
    parser.add_argument(
        "--skip-opencc",
        action="store_true",
        help="do not update OpenCC dictionaries",
    )

    args = parser.parse_args()

    if args.skip_zhtw_mcp and args.skip_opencc:
        parser.error("both --skip-zhtw-mcp and --skip-opencc were passed")
    if args.skip_zhtw_mcp and args.zhtw_mcp_rev:
        parser.error("--zhtw-mcp-rev cannot be used with --skip-zhtw-mcp")
    if args.skip_opencc and args.opencc_rev:
        parser.error("--opencc-rev cannot be used with --skip-opencc")

    return args


def main() -> int:
    args = parse_args()

    repo_root = Path(
        run(["git", "rev-parse", "--show-toplevel"], capture=True).stdout.strip()
    )
    flake_file = repo_root / "flake.nix"
    text = flake_file.read_text()

    zhtw_mcp_rev = args.zhtw_mcp_rev
    opencc_rev = args.opencc_rev

    if not args.skip_zhtw_mcp and not zhtw_mcp_rev:
        print("Resolving latest sysprog21/zhtw-mcp HEAD")
        zhtw_mcp_rev = resolve_git_head(ZHTW_MCP_REMOTE, "sysprog21/zhtw-mcp")

    if not args.skip_opencc and not opencc_rev:
        print("Resolving latest BYVoid/OpenCC HEAD")
        opencc_rev = resolve_git_head(OPENCC_REMOTE, "BYVoid/OpenCC")

    if not args.skip_zhtw_mcp:
        print(f"Updating zhtw-mcp source to sysprog21/zhtw-mcp@{zhtw_mcp_rev}")
        text = update_zhtw_mcp_rev(text, zhtw_mcp_rev)

    if not args.skip_opencc:
        print(f"Updating OpenCC dictionaries to BYVoid/OpenCC@{opencc_rev}")
        text = update_opencc_rev(text, opencc_rev)

        for filename in OPENCC_DICTS:
            print(f"Prefetching {filename}")
            hash_value = prefetch_opencc_dict_hash(opencc_rev, filename)
            text = update_opencc_hash(text, filename, hash_value)

    flake_file.write_text(text)
    run(["nixfmt", str(flake_file)])

    if not args.skip_zhtw_mcp:
        run(["nix", "flake", "update", "zhtw-mcp-src"], capture=False)

    print(
        """
Updated source pins.

Recommended verification:
  nix develop --command nix build .#zhtw-mcp --no-link

If the zhtw-mcp Cargo dependencies changed, update cargoHash with the hash
reported by that build and run it again.
""".strip()
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(
            f"error: command failed with exit code {exc.returncode}: {' '.join(exc.cmd)}",
            file=sys.stderr,
        )
        raise SystemExit(exc.returncode)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
