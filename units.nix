{ sstemplate, system, name, version, lib, pkgs }:
let 
  native = sstemplate.native.${system};
  powers = sstemplate.powers.${system};
  python = native.python {
    pythonVersion = "python38";
    name = name;
    version = version;
    buildInputs = ps: with ps; [ typer ];
  };

  postgres = powers.db.postgres {
    database = name;
    folder = "postgres";        
  };

  all = [ python postgres ];
in {
  inherit all;
  scripts = builtins.concatStringsSep "\n" (map (unit: unit.script) all);
  packages = lib.attrsets.genAttrs 
               (map 
                  (x: x.name) 
                  (lib.lists.filter (x: lib.attrsets.hasAttrByPath ["buildapp"] x && x.buildapp != null) all)) 
               (name: 
                  pkgs.callPackage (lib.lists.findFirst (x: x.name == name) null all).buildapp {});
}
