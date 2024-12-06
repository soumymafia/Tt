import os
import subprocess
import time
import requests
from web3 import Web3
from mnemonic import Mnemonic
from eth_account import Account

# Auto-install and update required packages
def install_packages():
    packages = ["web3", "mnemonic", "eth_account", "requests"]
    for package in packages:
        subprocess.call(['pip', 'install', '--upgrade', package])

# Handle `Mapping` import issue for Python 3.10+
def fix_mapping_import():
    import pathlib
    eth_account_path = pathlib.Path(__file__).parent / 'eth_account/account.py'
    if eth_account_path.exists():
        with open(eth_account_path, 'r') as file:
            data = file.read()
        if 'from collections import Mapping' in data:
            data = data.replace('from collections import Mapping', 'from collections.abc import Mapping')
            with open(eth_account_path, 'w') as file:
                file.write(data)

# Run installation and fix
install_packages()
fix_mapping_import()

# Enable HD Wallet feature
Account.enable_unaudited_hdwallet_features()

# Display top design
def display_banner():
    print("=" * 50)
    print("   CRYPTOGRAPHYTUBE - BNB Address Generator   ")
    print("=" * 50)
    print("   Generating addresses with private keys")
    print("   and checking for balance on BNB Smart Chain")
    print("=" * 50 + "\n")

# Initialize Web3 for BSC (Binance Smart Chain)
bsc_url = "https://bsc-dataseed.binance.org/"
web3 = Web3(Web3.HTTPProvider(bsc_url))

# Prompt for BscScan API key
api_key = input("Please enter your BscScan API key: ")
bscscan_url = "https://api.bscscan.com/api"

# Generate a BNB Smart Chain address and private key
def generate_address():
    mnemo = Mnemonic("english")
    seed = mnemo.generate(256)  # 24-word mnemonic phrase
    account = Account.from_mnemonic(seed)
    return account.address, account.key.hex()

# Check the balance of a BNB address
def check_balance(address):
    params = {
        "module": "account",
        "action": "balance",
        "address": address,
        "apikey": api_key,
        "tag": "latest"
    }
    response = requests.get(bscscan_url, params=params)
    if response.status_code == 200:
        balance = int(response.json().get("result", 0)) / (10 ** 18)  # Convert Wei to BNB
        return balance
    else:
        return None

# Save found address and private key in a file
def save_found(address, private_key):
    with open("found.txt", "a") as f:
        f.write(f"Address: {address}\nPrivate Key: {private_key}\n\n")

# Main function to generate and check balances until a non-zero balance is found
def main():
    display_banner()
    while True:
        address, private_key = generate_address()
        print(f"Checking Address: {address}")
        print(f"Private Key: {private_key}")
        
        balance = check_balance(address)
        if balance is not None and balance > 0:
            print(f"\nBalance Found! Address: {address}, Balance: {balance} BNB")
            save_found(address, private_key)
            break
        else:
            print("No balance found.\n" + "-" * 50)
        
        time.sleep(1)  # Delay for 1 second between requests

if __name__ == "__main__":
    main()
