# TODO

## Sync Branches
Right now incompatibilities between contracting and the actual blockchain make production code untestable (decimal issues). As such, `remove-decimal` was created as a temporary measure. 

However, having to maintain two branches of code is time consuming and prone to error especially because one cannot be tested. This is fine as a short term solution, but should be rectified as soon as convenient.

## Limit Orders/Stop Orders
This is often requested. A layer 2 solution would probably be ideal.

## Token/Token Swaps
This should be implemented in the next release. 

## Automatically Updating Token Reserves
This should be implemented in the next release with `balance_of`. However, this may be impossible if Token/Token swaps are also implemented. The best way to solve this would be with spin-off contracts.

## Better API 
(This might be frontend)

Set up an API with a serverless framework (like AWS Lambda) to facilitate future app development.

## Rocketswap-CLI
### Basic CLI (pypi)
Set up a CLI program.
### Self Contained CLI (hosted on Arweave/IPFS or other Web3 networks)
Set up a CLI program with no external libraries. 

# Got more TODOs? Open a PR!
