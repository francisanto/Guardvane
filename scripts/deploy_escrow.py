#!/usr/bin/env python3
"""
Deployment script for GuardvaneEscrow on Rabdi Testnet (Chain ID 7794095).
Uses Web3.py. Only broadcasts when explicitly called with --broadcast.
"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3

load_dotenv(Path(__file__).parent.parent / ".env")

def main():
    rpc_url = os.getenv("ARKIV_RPC_URL", "https://rpc.rabdi.db-chain.testnet.arkiv.network")
    chain_id = int(os.getenv("ARKIV_CHAIN_ID", "7794095"))
    private_key = os.getenv("ARKIV_SIGNER_PRIVATE_KEY")

    if not private_key:
        print("Error: ARKIV_SIGNER_PRIVATE_KEY is not defined in .env")
        sys.exit(1)

    artifact_path = Path(__file__).parent.parent / "contracts" / "artifacts" / "GuardvaneEscrow.json"
    if not artifact_path.exists():
        print("Error: GuardvaneEscrow.json not found. Run compile first.")
        sys.exit(1)

    with open(artifact_path, "r", encoding="utf-8") as f:
        artifact = json.load(f)

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print(f"Error: Could not connect to RPC {rpc_url}")
        sys.exit(1)

    account = w3.eth.account.from_key(private_key)
    balance_wei = w3.eth.get_balance(account.address)
    balance_eth = w3.from_wei(balance_wei, "ether")

    print("--- Guardvane Escrow Deployment ---")
    print(f"Network: {rpc_url}")
    print(f"Chain ID: {chain_id}")
    print(f"Deployer Wallet: {account.address}")
    print(f"Deployer Balance: {balance_eth} ETH / tGLM")

    should_broadcast = "--broadcast" in sys.argv

    if not should_broadcast:
        print("\n[DRY RUN] Transaction not broadcast. To deploy to Rabdi Testnet, pass --broadcast.")
        return

    print("\nDeploying GuardvaneEscrow contract to Rabdi Testnet...")
    escrow_contract = w3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])

    nonce = w3.eth.get_transaction_count(account.address)
    construct_txn = escrow_contract.constructor().build_transaction({
        "from": account.address,
        "nonce": nonce,
        "gas": 2500000,
        "gasPrice": w3.eth.gas_price,
        "chainId": chain_id
    })

    signed = w3.eth.account.sign_transaction(construct_txn, private_key=private_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"Transaction broadcast! Tx Hash: {tx_hash.hex()}")

    print("Waiting for transaction receipt...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    contract_address = receipt.contractAddress

    print("\n=============================================")
    print("GuardvaneEscrow Deployed Successfully!")
    print(f"Contract Address: {contract_address}")
    print(f"Explorer URL: https://rabdi.explorer.arkiv.network/address/{contract_address}")
    print("=============================================\n")

if __name__ == "__main__":
    main()

