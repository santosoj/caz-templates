mycontract = MyContract.deploy({"from": accounts[0]})
weth.deposit({"from": accounts[0], "value": 100 * 1e18})
weth.transfer(mycontract, 100 * 1e18, {"from": accounts[0]})
