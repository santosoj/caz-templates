import ast
import inspect
import re
import sys
import typing as t

from brownie import network, project
from brownie._cli.console import Console
from brownie._config import CONFIG

from scripts.contract_loader import ContractLoader


sys.modules["brownie"].a = network.accounts
sys.modules["brownie"].__all__.append("a")


active_project = None
loader = None
startup_locals = None


def get_brownie_vars() -> dict:
    brownie = sys.modules["brownie"]
    return {k: getattr(brownie, k) for k in brownie.__all__}


def inject_vars(_vars: dict, nth_stack_frame: int = 1):
    stack = inspect.stack()
    try:
        locals_ = stack[nth_stack_frame][0].f_locals
    finally:
        del stack
    locals_.update(_vars)


def reset_network(
    fork_block_number: t.Optional[int] = None
):
    if network.rpc.backend.__name__ != "brownie.network.rpc.hardhat":
        print(f"Skipping reset_network because backend is not Hardhat ({network.rpc.backend.__name__})")
        return

    fork_url = CONFIG.active_network["cmd_settings"].get("fork", None)
    params = []
    if fork_url:
        if not fork_block_number:
            cmd = CONFIG.active_network["cmd"]
            try:
                fork_block_number = int(re.search(r"--fork-block-number (\d+)", cmd).group(1))
            except:
                print(f"Could not parse block number from command ({cmd})")
        fork_param = {
            "forking": {
                "jsonRpcUrl": fork_url
            }
        }
        if fork_block_number:
            fork_param["forking"]["blockNumber"] = fork_block_number
        params.append(fork_param)
    print(f"Resetting network with params:\n{params}")
    web3.provider.make_request("hardhat_reset", params)


def reload(
    persist_network: bool = False,
    fork_block_number: t.Optional[int] = None
):
    global active_project
    global loader
    global startup_locals

    loader = ContractLoader()
    loader.generate_solidity_interfaces()

    if active_project is not None:
        active_project.close()
    active_project = project.load()
    active_project.load_config()
    active_project._add_to_main_namespace()
    print(f"{active_project._name} is the active project.")

    if not network.is_connected():
        network.connect(CONFIG.argv["network"])
    elif not persist_network:
        reset_network(fork_block_number)

    loader.build_contract_table()
    injected_locals = {
        **get_brownie_vars(),
        **loader.contract_table
    }
    inject_vars(injected_locals, nth_stack_frame=2)  # inject into reload's caller

    globals().update(get_brownie_vars())

    print()
    loader.print_loaded_contract_info()
    print("These are available as local variables now.\n")

    script = sys.argv[1] if len(sys.argv) > 1 else "console_startup.py"
    with open(script, "r") as f:
        startup_code = f.read()
    startup_ast = ast.parse(startup_code)
    startup_locals = {
        "loader": loader,
        **get_brownie_vars(),
        **loader.contract_table
    }
    exec(
        compile(
            startup_ast,
            filename=script,
            mode="exec"
        ),
        None,  # globals
        startup_locals
    )

    inject_vars(startup_locals, nth_stack_frame=2)


reload()


extra_locals = {
    "loader": loader,
    "reload": reload,
    **startup_locals,
}

shell = Console(active_project, extra_locals=extra_locals)
shell.interact()
