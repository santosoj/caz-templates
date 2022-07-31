# Brownie X-Mix

### Enhanced Brownie project starter


[Requirements](#requirements)

[External Contract Loader](#external_contract_loader)

[Console Enhancements](#console_enhancements)

[Various Notes](#various_notes)

----

## <a id="requirements"></a> Requirements

The Python env used by Brownie must have the [abi2solc](https://github.com/iamdefinitelyahuman/abi2solc) package installed. If Brownie was installed using `pipx`, the dependency may be injected using

```shell
pipx inject eth-brownie abi2solc
```

If the enhanced console's `reload` function is to be used with `persist_network=False` (the default), [Hardhat](https://hardhat.org/) is required, as the network reset is triggered using a `hardhat_reset` RPC request.

```shell
npm i -D hardhat
```

## <a id="external_contract_loader"></a> External Contract Loader

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

Build the contract table (requires a network for `Contract.from_abi`):

```python
loader.build_contract_table()
```

After building the contract table, `loader.contract_table` maps each of the keys to a `Contract` object.

To generate the Solidity interfaces, call

```
loader.generate_solidity_interfaces()
```

An optional output directory may be passed (it defaults to `contracts/external`). The interfaces will be generated in the output directory, and each of them will have some commented Solidity at the top of the file that declares the interfaces with external contracts at the addresses specified in `contracts.json`.

##  <a id="console_enhancements"></a> Console Enhancements

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

## <a id="various_notes"></a> Various Notes

### Forking node with any EVM network

#### Add a development network with a do-nothing `cmd`

Specification in `network-config.yaml` looks something like this:

```yaml
- cmd: ':'
  cmd_settings:
    chain_id: 56
    fork: http://127.0.0.1:8545
  host: http://127.0.0.1:8545
  id: local_8545
  name: local_8545
```

And `brownie-config.yaml` in the project root should have this in the `networks` section:

```yaml
networks:
  default: local_8545
```

This will make brownie run the `:` command, which does nothing, and connect to the network at `http://127.0.0.1:8545`. This network needs to be started manually.

To ensure Hardhat uses the correct chain ID (rather than `31337`) with the forking node, put this in `hardhat.config.js`:

```javascript
module.exports = {
    networks: {
        hardhat: {
            // ...any other settings that may be there...
            chainId: 56,
        }
    }
}
```

Start the node manually (before running brownie commands) using:

```bash
npx hardhat node --fork http://127.0.0.1:8545
```

Then, when running `brownie console`, you'll be on the forked network with the usual accounts with 10k ETH, and the chain ID will be correct.

```
Attached to local RPC client listening at '127.0.0.1:8545'...
Brownie environment is ready.
>>> web3.eth.blockNumber
19995527
>>> web3.eth.chainId
56
>>> accounts
[<Account '0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266'>, <Account '0x70997970C51812dc3A010C7d01b50e0d17dc79C8'>, <Account 
...
>>> web3.eth.getBalance(accounts[0].address) / 1e18
10000.0
```

### Simple local proxy for JSON RPC requests

This is useful when:
  - you would specify an API key in a query parameter. So there would be `POST` requests with a JSON RPC body and the API key in the URL (`https://bsc.getblock.io/?api_key=<YOUR_API_KEY>`), as supported by GetBlock
  - *something* is silently removing this (and any) query parameter
  - the API supports passing the API key in HTTP header (as GetBlock does)

The approach here is to use `npx hardhat node --fork` with the URL of a proxy running locally. The proxy adds the API key header, makes the request to the node provider, and relays the response back to Hardhat.

Sample proxy implemented with Flask. (Start with `FLASK_APP=proxy flask run`)

```python
# proxy.py

import json
import requests

from flask import Flask, request

app = Flask(__name__)

@app.route("/mainnet", methods=["POST"], strict_slashes=False)
def mainnet():
    res = requests.post(
        "https://bsc.getblock.io/mainnet/",
        json=request.json,
        headers={
            "x-api-key": "<YOUR_API_KEY>"
        },
        verify=False,
    )
    return res.json()
```

Then, with this proxy listening at e.g. `127.0.0.1:5000`:

```
npx hardhat node --fork http://127.0.0.1:5000/mainnet
```

(Wouldn't work when using `localhost` instead of `127.0.0.1`.)

### BSC archive node

```shell
npx hardhat node --fork https://bscrpc.com/erigonbsc --fork-block-number <BLOCK_NUMBER>
```

No authentication needed. Free BSC **archive** node provided by Ankr.

The version of Erigon they're currently running seems to have an issue processing the `net_version` command, which would cause Hardhat to fail with this error message:

```
Error HH604: Error running JSON-RPC server: connection error: desc = "transport: Error while dialing dial tcp 127.0.0.1:9090: connect: connection refused"
```

This can be helped by e.g. extending the proxy snippet above to intercept `net_version` and return the 'canonical' response without sending the command to the remote node:

```
{
	"id": <INCOMING_JSON_RPC_REQUEST_ID>,
	"jsonrpc": "2.0",
	"result": "56"
}
```
