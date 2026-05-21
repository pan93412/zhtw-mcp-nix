{
  description = "Nix package for zhtw-mcp";

  inputs = {
    nixpkgs.url = "https://flakehub.com/f/NixOS/nixpkgs/0.1";
    fenix = {
      url = "https://flakehub.com/f/nix-community/fenix/0.1";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    zhtw-mcp-src = {
      url = "github:sysprog21/zhtw-mcp/a2d53f4a4ef6821b974cd4b435a340133071b7d3";
      flake = false;
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      fenix,
      zhtw-mcp-src,
    }:

    let
      supportedSystems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forEachSupportedSystem =
        f:
        nixpkgs.lib.genAttrs supportedSystems (
          system:
          f {
            inherit system;
            pkgs = import nixpkgs {
              inherit system;
              overlays = [ self.overlays.default ];
            };
          }
        );
    in
    {
      overlays.default = final: prev: {
        rustToolchain =
          with fenix.packages.${final.stdenv.hostPlatform.system};
          combine (
            with stable;
            [
              cargo
              clippy
              rust-src
              rustc
              rustfmt
            ]
          );

        zhtw-mcp =
          let
            cargoToml = builtins.fromTOML (builtins.readFile "${zhtw-mcp-src}/Cargo.toml");
            openccRev = "472e8957788e14835b2ff806cc7e305732b2c7f6";
            openccDictUrl =
              file: "https://raw.githubusercontent.com/BYVoid/OpenCC/${openccRev}/data/dictionary/${file}";
            openccDicts = final.linkFarm "opencc-dictionaries" [
              {
                name = "STPhrases.txt";
                path = final.fetchurl {
                  url = openccDictUrl "STPhrases.txt";
                  hash = "sha256-eljboErDBjRGX7BIIVSWWraMVYROVnvtpj//xfVe7QA=";
                };
              }
              {
                name = "STCharacters.txt";
                path = final.fetchurl {
                  url = openccDictUrl "STCharacters.txt";
                  hash = "sha256-cUsOfiYVKpnLIhV30WBXSoMHGt6mNWppJnFXRSFCKDg=";
                };
              }
              {
                name = "TWVariants.txt";
                path = final.fetchurl {
                  url = openccDictUrl "TWVariants.txt";
                  hash = "sha256-iUc+luP2HpvT8uMDudiKycqmHv+x+q3O+U/15luO1Us=";
                };
              }
            ];
            rustPlatform = final.makeRustPlatform {
              cargo = final.rustToolchain;
              rustc = final.rustToolchain;
            };
          in
          rustPlatform.buildRustPackage {
            pname = "zhtw-mcp";
            inherit (cargoToml.package) version;

            src = zhtw-mcp-src;

            cargoHash = "sha256-vwguHA1z9ne6P8Q+JBMafAIkhihMgBOdxbHF0HrWLes=";

            nativeBuildInputs = [
              final.python3
              final.rustToolchain
            ];

            preBuild = ''
              mkdir -p data/opencc
              cp ${openccDicts}/STPhrases.txt data/opencc/STPhrases.txt
              cp ${openccDicts}/STCharacters.txt data/opencc/STCharacters.txt
              cp ${openccDicts}/TWVariants.txt data/opencc/TWVariants.txt
              python3 scripts/gen-s2t-tables.py
              rustfmt src/engine/s2t_data.rs
            '';

            cargoTestFlags = [
              "--lib"
              "--bins"
            ];

            meta = with final.lib; {
              description = "MCP server for Traditional Chinese (zh-TW) text linting and normalization";
              homepage = "https://github.com/sysprog21/zhtw-mcp";
              license = licenses.mit;
              mainProgram = "zhtw-mcp";
              platforms = platforms.unix;
            };
          };
      };

      packages = forEachSupportedSystem (
        { pkgs, ... }:
        {
          inherit (pkgs) zhtw-mcp;
          default = pkgs.zhtw-mcp;
        }
      );

      devShells = forEachSupportedSystem (
        { pkgs, ... }:
        {
          default = pkgs.mkShell {
            packages = [
              pkgs.git
              pkgs.nixfmt
              pkgs.python3
              pkgs.ruff
            ];
          };
        }
      );

      formatter = forEachSupportedSystem ({ pkgs, ... }: pkgs.nixfmt);
    };
}
