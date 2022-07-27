import json
from os import path

import abi2solc

from brownie import Contract, web3


class ContractLoader:
    def __init__(self, directory="scripts/abis"):
        self.directory = directory
        with open(path.join(self.directory, "contracts.json"), "r") as f:
            self.specs = json.loads(f.read())
    
    def build_contract_table(self):
        self.contract_table = dict()
        for spec in self.specs:
            key = spec["key"]
            iface_name = spec["iface_name"]
            same_iface_specs = [s for s in self.specs if s["iface_name"] == iface_name]
            abi = None
            for spec_inner in same_iface_specs:
                file = path.join(self.directory, f"{spec_inner['key']}.json")
                if path.exists(file):
                    with open(file, "r") as f:
                        abi = json.loads(f.read())
                    break
            assert abi is not None, f"Missing ABI for interface {iface_name}"
            self.contract_table[key] = Contract.from_abi(spec["name"], spec["addr"], abi)

    def __getitem__(self, key):
        return self.contract_table[key]

    def generate_solidity_interfaces(self, directory="contracts/external"):
        ifaces = []
        for spec in self.specs:
            key, iface_name, addr = spec["key"], spec["iface_name"], spec["addr"]
            try:
                d = next(i for i in ifaces if i["iface_name"] == iface_name)
                d["deployments"].append({
                    "key": key,
                    "addr": addr,
                })
            except StopIteration:
                ifaces.append({
                    "iface_name": iface_name,
                    "deployments": [
                        {
                            "key": key,
                            "addr": addr,
                        }
                    ]
                })
        for iface in ifaces:
            iface_name = iface["iface_name"]
            load_code = ""
            abi_file = None
            for deployment in iface["deployments"]:
                load_code += f"// {iface_name} {deployment['key']} = {iface_name}({web3.toChecksumAddress(deployment['addr'])});\n"
                file = path.join(self.directory, f"{deployment['key']}.json")
                if abi_file is None and path.exists(file):
                    abi_file = file
            assert abi_file is not None, f"Missing ABI for interface {iface_name}"
            with open(abi_file, "r") as f:
                abi = json.loads(f.read())
            iface_solidity = (
                abi2solc.generate_interface(abi, iface_name)
                .replace(
                    "pragma solidity ^0.5.0",
                    "pragma solidity ^0.6.0"
                )
                .replace(
                    "function () external payable;",
                    "fallback () external payable;"
                )
            )
            output_file = path.join(directory, f"{iface_name}.sol")
            with open(output_file, "w") as f:
                f.write(load_code)
                f.write(iface_solidity)

    def print_loaded_contract_info(self):
        print("ContractLoader has loaded:")
        for spec in self.specs:
            print(f"    {spec['key']}: {spec['name']}")
