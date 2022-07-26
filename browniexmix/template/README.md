# Brownie X-Mix

### Enhanced Brownie project starter

----

## Requirements

The Python env used by Brownie must have the [abi2solc](https://github.com/iamdefinitelyahuman/abi2solc) package installed. If Brownie was installed using `pipx`, the dependency may be injected using

```shell
pipx inject eth-brownie abi2solc
```

If the enhanced console's `reload` function is to be used with `persist_network=False` (the default), [Hardhat](https://hardhat.org/) is required, as the network reset is triggered using a `hardhat_reset` RPC request.

```shell
npm i -D hardhat
```

## External Contract Loader

`Contract.from_explorer` is excellent, but loading the same contracts from Etherscan over and over again is wasteful. `ContractLoader` instantiates external contracts from ABIs stored within the project. It also generates Solidity interface definitions from the ABI files using [abi2solc](https://github.com/iamdefinitelyahuman/abi2solc).

A simple declaration file ([scripts/abis/contracts.json](scripts/abis/contracts.json)) specifies each contract with the following fields.

- `key`: Key under which the contract will be in the contract table. Also, the ABI filename that the loader will look for (key=`weth` → ABI in `weth.json`).
- `name`: For string representation
- `addr`: Contract address
- `iface_name`: Name of the Solidity interface to be generated from the ABI. This is non-unique. When multiple keys share one `iface_name` value, it is not required to provide an ABI file for every key. Having an ABI for one of the keys will suffice. (It doesn't matter which one.)

Create a loader instance:

```python
loader = ContractLoader()
```

(The directory containing `contracts.json` and the ABIs may optionally be passed as an argument.)

After instantiation, `loader.contract_table` maps each of the keys to a `Contract` object.

To generate the Solidity interfaces, call

```
loader.generate_solidity_interfaces()
```

An optional output directory may be passed (it defaults to `contracts/external`). The interfaces will be generated in the output directory, and each of them will have some commented Solidity at the top of the file that declares the interfaces with external contracts at the addresses specified in `contracts.json`.

## Console Enhancements

It's not just loading external contracts, there are other tasks that often need to be done upon starting a Brownie console, and having to enter the same code every time becomes tedious.

`console_loader.py` will...

- load external contracts using `ContractLoader` and add them to locals, so when e.g. there's a contract with a key of `weth`, it will be available as the local variable `weth` after starting the console.
- execute a console startup script that also adds variables to locals. The startup script may e.g. deploy contracts and make them available as local variables at console startup.
- provide a mechanism to reload the project (including compiling Solidity, if there are changes) without having to restart the console. Restarting the network is also optional: we can re-compile the Solidity, and re-deploy contracts and have them assigned to local variables, while staying in the same console session and without restarting the network.

### Console Startup

If Brownie was installed using `pipx`,

```shell
./console.sh
```

will run `console_loader.py` using the Python from Brownie's environment. The startup script (a Python file) to be executed by the loader may be passed as an argument. If no argument is passed to `console_loader.py`, it will run `console_startup.py` as the startup script.

Any variable in the `brownie` module (`web3`, contract factories, ...), as well as external contracts loaded by `ContractLoader` and bound to variables synonymous with the contracts' `key`s, are available to the startup script.

Any variable declared in the root scope of the startup script will be available as a local variable in the console.

For example, assuming...

- the project has a Solidity contract named `MyContract`
- WETH is loaded by `ContractLoader` with a key of `weth`

this makes it possible to put this (without any import statement) in `console_startup.py`:

```python
mycontract = MyContract.deploy({"from": accounts[0]})
weth.deposit({"from": accounts[0], "value": 100 * 1e18})
weth.transfer(mycontract, 100 * 1e18, {"from": accounts[0]})
```

The deployed instance will then be available as `mycontract` in the console, and have a balance of 100 WETH.

### Project Reloading

A function named `reload` is available in the console. Called without an argument...

```python
reload()
```

...it will:

- reload the Brownie project, which includes compiling the Solidity sources if there is a change
- reset the network (Only with a Hardhat backend. This does not restart the network, it makes a `hardhat_reset` RPC call.)
- execute the console startup script

It is possible to suppress the network reset by passing

```python
reload(persist_network=True)
```

In this case, the execution of the startup script will result in `MyContract` being deployed *at a different address*, and the `mycontract` variable being bound to the new deployment.

When not persisting the network, a `fork_block_number` may also be passed when using a forking node:

```python
reload(forking_block_number=15218303)
```

In this case, you need to have configured a forking network in Brownie that specifies an archive node API endpoint in the `fork` setting. (Putting `fork: mainnet` will not work.) This network must also be your project's default network.

So the `Hardhat (Mainnet Fork)` config in Brownie's `network-config.yaml` file (`~/.brownie/network-config.yaml`, YMMV) should look something like this:

```yaml
- cmd: npx hardhat node --fork-block-number 15218334
  cmd_settings:
    fork: https://eth-mainnet.g.alchemy.com/v2/<PROJECT_ID>
    port: 8545
  explorer: https://api.etherscan.io/api?apikey=<API_KEY>
  host: http://localhost
  id: hardhat-fork
  name: Hardhat (Mainnet Fork)
  timeout: 120
```

Note the `--fork-block-number 15218334` in the `cmd` field. This is the default forking block number that will be used when `reload()` is called without an argument.

And `brownie-config.yaml` in the project root should have this in the `networks` section:

```yaml
networks:
  default: hardhat-fork
```
