from ss.configure import blueprint
from ss.configure.blueprint import Blueprint
from ss.configure.schema import LINE_BREAK, SPACE
from .renderer import Renderer


class UnitsTemplate:
    def __init__(self, blueprint: Blueprint):
        self.blueprint = blueprint
        self.renderer = Renderer()

    def render_unit(self, name, unit):
        params = self.renderer.extract_params(unit=unit)

        if self.blueprint.is_root_blueprint:
            return f"""
                {name} = (
                  {self.renderer.render_let_in(self.renderer.render_call_father(name=name, unit=unit, blueprint=self.blueprint))}
                sslib.defineUnit
                {{
                    name = "{name}";
                    {self.renderer.render_unit(unit=unit, blueprint=self.blueprint)}
                }});
            """
        else:
            render_call_father = (
                lambda name, unit, blueprint: self.renderer.render_call_father(
                    name=name, unit=unit, blueprint=self.blueprint
                )
            )

            return f"""
            {name} = _{name} {{
            }};

            _{name} = (
            {{
                {",".join([f"{key} ? {self.renderer.render_value(key, value, blueprint=self.blueprint)}" for key, value  in params.items()])}
            }}:
            {self.renderer.render_let_in(render_call_father(name, unit, blueprint) or {})}
            {{
              {self.renderer.render_unit(unit=unit, blueprint=self.blueprint)}
           }});"""

    def render_actions(self, actions: dict) -> str:
        return f"""
        actions = {{
            {LINE_BREAK.join([f"{name} = {self.renderer.render_value(name=name, value=action, blueprint=self.blueprint)};" for name, action in actions.items()])}
        }};
        """

    def render_action_flows(self, action_flows: dict) -> str:
        return f"""
            actionFlows = { self.renderer.render_value(
            name="action_flows", value=action_flows, blueprint=self.blueprint
        ) };
        """

    def render_onstart(self, onstart: dict) -> str:
        return f"""
            onstart = { self.renderer.render_value(name='onstart', value=onstart, blueprint=self.blueprint) };
        """

    def render(self) -> str:
        line_break = "\n"
        space = " "

        names = list(map(lambda x: x.replace(".", "_"), self.blueprint.units.keys()))

        render_units_in_sources = line_break.join(
            [
                self.render_unit(name, value)
                for name, value in self.blueprint.units.items()
            ]
        )

        default_imports = ["pkgs", "system", "name", "version", "lib", "sslib"]
        included_imports = [
            item[0]
            for item in self.renderer.resolve_all_includes(blueprint=self.blueprint)
            if item[1] is not None
        ]
        all_import = included_imports + default_imports
        all_interfaces = (
            space.join(map(lambda x: f"_{x}", names))
            if not self.blueprint.is_root_blueprint
            else ""
        )

        return f"""
	{{  {','.join(all_import) } }}:
		let
            metadata = {{ inherit name version; }};

            {render_units_in_sources}

            { self.render_actions(self.blueprint.actions or {}) }
            { self.render_action_flows(self.blueprint.action_flows or {}) }
            { self.render_onstart(self.blueprint.onstart or {}) }

            all = [ {line_break.join(names)}];
            allAttr = {{ inherit { space.join(names) }; }};
            actionableImport = lib.attrsets.filterAttrs (n: v: v ? isSS && v.isSS) {{ inherit {SPACE.join(included_imports)}; }};

            unitsProfile = lib.attrsets.mapAttrs
                (name: unit:
                    {{
                        path = unit;
                        actions = if unit ? actions && unit.actions != null then unit.actions else {{}};
                        action_flows = if unit ? action_flows && unit.action_flows != null then unit.action_flows else {{}};
                        onstart = if unit ? onstart && unit.actions != null then unit.onstart else {{}};
                    }}
                ) allAttr;

            currentProfile = {{
                 {self.blueprint.name} = {{
                     inherit actions;
                     inherit actionFlows;
                     inherit onstart;
                }};
            }};

            includedProfile = lib.attrsets.mapAttrs (name: include: {{
                actions = if include ? actions && include.actions != null then include.actions else {{}};
                actionFlows = if include ? actionFlows && include.actionFlows != null then include.actionFlows else {{}};
            }}) actionableImport;

            mapShs = sh:
                if builtins.isList sh then
                    map (x: mapShs x) sh
                else
                    ["source ${{sh}}"];

            load-profile = pkgs.writeScriptBin "load_profile" ''
                echo '${{builtins.toJSON ( unitsProfile // currentProfile // includedProfile)}}'
            '';

            onStartScript = lib.strings.concatStringsSep
                "\n"
                (lib.flatten
                  (
                    (map
                      (x: mapShs x.onstart)
                      (lib.filter (unit: unit ? onstart && unit.onstart != null) all) ++ (mapShs onstart)
                    )
                  )
                );

            startScript = ''
                export SS_PROJECT_BASE=$PWD
            '';

            funcs = [ load-profile ];


		in {{
		inherit all allAttr funcs actions;
		scripts = builtins.concatStringsSep "\\n" [ onStartScript ];
        dependencies = all;
		}} // {{ inherit {all_interfaces}; }}
	"""
