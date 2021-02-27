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

## TODO
In-depth documentation of the actual SC.
