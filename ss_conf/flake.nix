
      {
        description = "devlopment environment with 1 command";

        inputs.nixpkgs = {
          url = "github:NixOS/nixpkgs/";
        };

        inputs.flake-utils.url = "github:numtide/flake-utils";

        inputs.sstemplate.url = "path:/Users/ianluo/Documents/apps/templates";
        inputs.sstemplate.inputs.nixpkgs.follows = "nixpkgs";

        outputs = { self, nixpkgs, flake-utils, sstemplate }:
          flake-utils.lib.eachDefaultSystem (system:
            let
              pkgs = import nixpkgs { inherit system; };

              version = "0.0.1";
              name = "ss";

              units = pkgs.callPackage ./units.nix { inherit sstemplate name version system; };
            in
            {
              devShells = with pkgs; {
                default = mkShell {
                  name = name;
                  version = version;
                  buildInputs = (map (x: x.value) units.all) ++ units.all;
                  shellHook = ''
                    ${units.scripts}
                  '';
                };
              };

              packages = units.packages;
            });
      }
      
