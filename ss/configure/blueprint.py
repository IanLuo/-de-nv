"""
a blueprint contains:
1. all units that can be used in the project
2. add defined action flows

units includes all resolved from current and included blueprints,
if a unit is defined in the current blueprint, it will override the included one

a unit contains below attributes:
1. name
2. version
3. initialize script (optional)
4. actions
5. source (nipkgs, git, plain text, file, etc)
7. listner (optional)

a action flow is formed as:
(unit1, param, condition?) -> (result) ...
an action flow is basicall a unit action call followd by another action call, whill a optional condition provide,
with the last action call return value is provided as parameter

any executables can be attached to a listener,
if a unit is attached to a lisenter, the unit will be executed (asynchromizely) with the value for the lisenter
and the same for action flow

include supports:
1. ss bluprint: ss.yaml
   if there is a ss.yaml in the destination, use it
2. flake.nix or default.nix
    if a flake or a default.nix is there, use it, and wrap the package in side
    unit

"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from .parser import parse
import os
from os.path import exists 
import re
import logging
from .resource_manager import ResourceManager, Resource
from ..folder import Folder
from os.path import dirname, join


@dataclass
class Blueprint:
    units: Dict[str, Any]
    actions: Dict[str, Any]
    action_flows: Dict[str, Any]
    includes: Dict[str, Any]
    metadata: Dict[str, Any]
    is_root_blueprint: bool

    def __init__(self, 
                 root: str, 
                 include_path: Optional[str] = None, 
                 config_path: Optional[str] = None):
        config_path = config_path or Folder(root).config_path
        self.is_root_blueprint = include_path is None
        self.root = root
        self.gen_folder = Folder(join(root, '.ss') or include_path)
        self.config_folder = Folder(dirname(config_path))
        self.resource_manager = ResourceManager(lock_root=root, 
                                                config_folder=self.config_folder)

        self.init_blueprint(config_path)

    @property
    def name(self):
        return self.metadata.get("name")

    @property
    def version(self):
        return self.metadata.get("version")

    @property
    def description(self):
        return self.metadata.get("description", "")

    def init_blueprint(self, yaml_path: str):
        logging.info("initializing blueprint..")

        logging.info(f"parsed blueprint..")
        json = self.parse_yaml(yaml_path)

        logging.info(f"parsed unit..")
        self.units = {
            name: self.parse_unit(data) for name, data in json.get("units", {}).items()
        }
        
        logging.info(f"parsed include..")
        self.includes = {
            name: self.parse_include(data) for name, data in json.get("include", {}).items()
        }

        logging.info(f"parsed metadata..")
        self.metadata = json.get("metadata", None)
        if self.metadata is None:
            raise Exception("metadata is mandatory")
        elif self.metadata.get("name") is None:
            raise Exception("name is mandatory")

        logging.info(f"parsed actions..")
        self.actions = {
            name: self.parse_actions(data) for name, data in json.get("actions", {}).items()
        }

        logging.info(f"parsed action flows..")
        self.action_flows = {
            name: self.parse_action_flow(data)
            for name, data in json.get("action_flows", {}).items()
        }

    def resovle_all_includes(self, includes: Dict[str, Any]):
        logging.info(f"start resolving includes..")
        for name, value in includes.items():
            logging.info(f"resolving include '{name}'..")
            self.resolve_include(name, value)

    def resolve_include(self, name: str, value: dict[str, Any]):
        if value is None:
            raise Exception(f"include '{name}' not found")

        logging.info(f"collecting include {value}..")
        resource_name = self.metadata.get("name", '') + "-" + name
        include_resource = self.resource_manager.fetch_resource(resource_name, value)

        self.includes[name] = {**self.includes[name], 
                               **include_resource.__dict__, 
                               'gen_root': self.gen_folder.include_path(name),
                               }

        ss_path = Folder(include_resource.local_path).config_path
        
        if exists(ss_path):
            logging.info(f"found ss.yaml at {ss_path}, using it..")
            self.includes[name]['blueprint'] = Blueprint(root=self.root,
                                                         include_path=self.gen_folder.include_path(name),
                                                         config_path=ss_path)

    def parse_yaml(self, yaml_path: str) -> Dict[str, Any]:
        with open(yaml_path, "r") as f:
            return parse(f)


    def parse_unit(self, data: Dict[str, Any]) -> Dict[str, Any]:
        def raise_exception(name):
            raise Exception(f"{name} is mandatory")

        mandatory = lambda x: data[x] if x in data else raise_exception(x)
        optional = lambda x: data.get(x)

        return {
            "source": mandatory("source"),
            "instantiate": optional("instantiate"),
            "actions": optional("actions"),
            "listener": optional("listener"),
        }

    def parse_include(self, data: Any) -> Dict[str, Any]:
        if isinstance(data, str):
            return {"url": data}
        elif isinstance(data, dict):
            return data
        else:
            raise Exception("include should be a string or a dict")



    def parse_actions(self, data: Any):
        if isinstance(data, str):
            return data

        return '' 


    def parse_action_flow(self, flow: Dict[str, Any]) -> Dict[str, Any]:
        pass


# perform actions

    def perform_action(
        self, 
        unit_name: Optional[str], 
        action_name: str
    ) -> Any:
        unit = self.units.get(unit_name or '')

        if unit is None:
            command = self.actions.get(action_name)
        else:
            command = unit.get('actions', {}).get(action_name)

        if command is None:
            raise Exception(f'command for \'{action_name}\' not found') 

        if command.startswith("$"):
            unit, unit_action = self.read_action_ref(command)
            self.perform_action(unit.get('actions', {}), unit_action)
        else:
           os.system(f'bash {command}')


    def read_action_ref(self, 
                        ref: str, 
    ) -> tuple[Dict[str, Any], str]:
        pattern = r'\$(\w*)\.(\w*)'
        match = re.match(pattern, ref)
        if match:
            unit = self.units.get(match.group(1))
            action = match.group(2)
            return unit, action
        else:
            raise Exception(f'invalid action reference {ref}')


    def action_flow(
        self,
        action: perform_action):
            pass # TODO:

    def perform_condition(self, param: Any) -> bool:
        pass # TODO:


