import concurrent.futures
from tonsdk.contract.wallet import Wallets, WalletVersionEnum

# Function to load addresses from a file
def load_addresses(file_name):
    try:
        with open(file_name, "r") as f:
            return {line.strip() for line in f if line.strip()}  # Return a set of addresses
    except FileNotFoundError:
        print(f"Error: The file '{file_name}' was not found.")
        return set()  # Return an empty set if the file does not exist

# Function to generate a single wallet
def generate_wallet(existing_addresses):
    mnemonics, pub_k, priv_k, wallet = Wallets.create(WalletVersionEnum.v4r2, workchain=0)
    wallet_address = wallet.address.to_string(True, True, False)
    private_key = priv_k.hex()  # Convert private key from bytes to hex string
    
    # Print the generated wallet details
    print(f"Generated Wallet Address: {wallet_address}")
    print(f"Mnemonics: {' '.join(mnemonics)}")
    print(f"Private Key: {private_key}\n")
    
    # Check if the generated address matches any in the existing addresses
    if wallet_address in existing_addresses:
        return (wallet_address, mnemonics, private_key)  # Return matching wallet info
    return None  # Return None if not matching

# Function to generate wallets until a match is found
def generate_wallets_until_match(existing_addresses):
    found_wallet = None  # Initialize found wallet variable
    with concurrent.futures.ThreadPoolExecutor() as executor:
        while found_wallet is None:  # Loop until a match is found
            future = executor.submit(generate_wallet, existing_addresses)
            result = future.result()
            if result is not None:
                found_wallet = result  # Save the found wallet info
                wallet_address, mnemonics, private_key = found_wallet
                
                # Print found matching wallet details immediately
                print(f"Found matching Wallet Address: {wallet_address}")
                print(f"Mnemonics: {' '.join(mnemonics)}")
                print(f"Private Key: {private_key}\n")
                
                # Save the found wallet to found.txt
                with open("found.txt", "a") as found_file:
                    found_file.write(f"Wallet Address: {wallet_address}\n")
                    found_file.write(f"Mnemonics: {' '.join(mnemonics)}\n")
                    found_file.write(f"Private Key: {private_key}\n\n")
            else:
                print("No match found, generating another wallet...")

# Main script
if __name__ == "__main__":
    # Load existing addresses from addresses.txt
    existing_addresses = load_addresses("addresses.txt")
    print(f"Loaded {len(existing_addresses)} addresses to match against.")
    
    # Start generating wallets until a match is found
    generate_wallets_until_match(existing_addresses)
    
    print("Wallet generation complete.")
