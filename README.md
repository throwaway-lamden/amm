# Rocketswap Smart Contracts

This repo contains the main Rocketswap AMM smart contract and associated tests.

## Testing

You can run unittests by calling the python module.

```bash
python3 -m unittest test_refactor.py
```
For better performance, you can run tests multithreaded with [Pytest](https://pytest.org/), but this requires [pytest-xdist](https://github.com/pytest-dev/pytest-xdist) and [flaky](https://github.com/box/flaky).

```bash
pytest /root/amm/lamden-version/test_refactor.py -n {amount of threads} --force-flaky
```

## Deployment
Extract the smart contract code by appending the following to `test_refactor.py`, and then call it normally (`python3 test_refactor.py`)
```python
client = ContractingClient()
print(client.closure_to_code_string(dex)[1]) #Prints only the code, and not the name of the dex function
```
You can now deploy this code via the wallet or by following the instructions in the [Contracting documentation](https://contracting.lamden.io/submitting/).
##  Dependencies
To test, [Contracting](http://contracting.lamden.io/) is required. To deploy, Lamden (`pip install lamden`) or the browser wallet is required.

## Progress
Final product and mainnet release are scheduled for early March.
## Functions/Usage
### seed
**Cannot be called**

Sets the constants to their default value. As of now, you cannot pass arguments, and you have to manually modify the code.

The default values are as follows:
```python
state["FEE_PERCENTAGE"] = 0.3 / 100
state["TOKEN_CONTRACT"] = "con_amm"
state["TOKEN_DISCOUNT"] = 0.75
state["BURN_PERCENTAGE"] = 0.8
state["BURN_ADDRESS"] = "0x0" #Will be changed
state["LOG_ACCURACY"] = 1000000000.0
state["MULTIPLIER"] = 0.05
state["OWNER"] = ctx.caller 
```

### create_market
Takes `contract: str, currency_amount: float=0, token_amount: float=0` 

Creates a liquidity market for a specified token. There must not be an existing market for the specified token. This mints 100 tokens.

Returns `True` on a success.

### liquidity_balance_of
Takes `contract: str, account: str`

Returns liquidity balance of the account calling this function.

### add_liquidity
Takes `contract: str, currency_amount: float=0`

Adds an amount of liquidity with `TAU` value equal to `currency_amount`, and a token amount equal to `currency_amount / prices[contract]`. Mints an amount of LP tokens equivalent to `total_lp_points / currency_reserve * currency_amount` 

Returns the amount of LP tokens minted.

### remove_liquidity
Takes `contract: str, amount: float=0`

Removes an amount of liquidity equal to `reserves * amount / lp_points[contract]`.

Returns tuple of `(currency_amount, token_amount)`.

### transfer_liquidity
Takes `contract: str, to: str, amount: float`

Transfers liquidity. Analogous to `transfer` in LST-0001.

### approve_liquidity
Takes `contract: str, to: str, amount: float`

Approves liquidity for transfer. Analogous to `approve` in LST-0001.

### transfer_liquidity_from
Takes `contract: str, to: str, main_account: str, amount: float`

Approves liquidity for transfer. Analogous to `transfer_from` in LST-0001.

### 
## TODO
Finish documenting functions.
An actual TODO section.
