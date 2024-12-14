from mnemonic import Mnemonic
import bip32utils
import hashlib
from itertools import product
import multiprocessing
from multiprocessing import Pool, Manager, Value

# Load BIP39 wordlist
def load_bip39_wordlist(filename="bip39-wordlist.txt"):
    try:
        with open(filename, "r") as file:
            return [line.strip() for line in file]
    except FileNotFoundError:
        print(f"Error: {filename} not found.")
        return []

# Load target addresses
def load_target_addresses(filename="target_addresses.txt"):
    try:
        with open(filename, "r") as file:
            return set(line.strip() for line in file if line.strip())
    except FileNotFoundError:
        print(f"Error: {filename} not found.")
        return set()

# Generate BIP44 and BIP32 addresses from mnemonic phrase
def generate_addresses(mnemonic_phrase):
    mnemonic = Mnemonic("english")
    seed = mnemonic.to_seed(mnemonic_phrase)

    # Generate BIP44 address
    key_bip44 = bip32utils.BIP32Key.fromEntropy(seed)
    bip44_path = "44'/0'/0'/0/0"
    for level in bip44_path.split("/"):
        if "'" in level:
            key_bip44 = key_bip44.ChildKey(int(level[:-1]) + bip32utils.BIP32_HARDEN)
        else:
            key_bip44 = key_bip44.ChildKey(int(level))
    bip44_address = key_bip44.Address()

    # Generate BIP32 address
    key_bip32 = bip32utils.BIP32Key.fromEntropy(seed)
    bip32_path = "0/0"
    for level in bip32_path.split("/"):
        key_bip32 = key_bip32.ChildKey(int(level))
    bip32_address = key_bip32.Address()

    return bip44_address, bip32_address

# Worker function to process a batch of combinations
def worker(args):
    batch, missing_positions, mnemonic_template, target_addresses = args
    matches = []
    
    for words in batch:
        test_mnemonic = mnemonic_template[:]
        for i, pos in enumerate(missing_positions):
            test_mnemonic[pos] = words[i]
        
        mnemonic_phrase = " ".join(test_mnemonic)
        bip44_address, bip32_address = generate_addresses(mnemonic_phrase)
        
        if bip44_address in target_addresses or bip32_address in target_addresses:
            matches.append((mnemonic_phrase, bip44_address, bip32_address))
    
    return matches

# Function to chunk the combinations
def chunks(iterable, n):
    """Yield successive n-sized chunks from iterable."""
    it = iter(iterable)
    while True:
        chunk = list()
        try:
            for _ in range(n):
                chunk.append(next(it))
        except StopIteration:
            if chunk:
                yield chunk
            break
        yield chunk

# Attempt to recover mnemonic and check for address match using multiprocessing
def recover_mnemonic_with_missing_words(mnemonic_template, target_addresses, wordlist, found_queue, counter, total_combinations):
    missing_positions = [i for i, word in enumerate(mnemonic_template) if word == "____"]
    num_missing = len(missing_positions)
    
    if num_missing == 0:
        print("No missing words to recover.")
        return
    
    # Define the number of processes
    num_processes = multiprocessing.cpu_count()
    pool = Pool(processes=num_processes)
    
    # Define batch size (number of combinations per task)
    batch_size = 1000  # Adjust based on memory and performance
    
    # Create a generator for all possible combinations
    combination_generator = product(wordlist, repeat=num_missing)
    
    # Create argument tuples for the worker function
    args_generator = (
        (batch, missing_positions, mnemonic_template, target_addresses)
        for batch in chunks(combination_generator, batch_size)
    )
    
    # Iterate over the results as they complete
    for matches in pool.imap_unordered(worker, args_generator):
        if matches:
            for mnemonic_phrase, bip44_address, bip32_address in matches:
                found_queue.put((mnemonic_phrase, bip44_address, bip32_address))
        
        # Update counter
        with counter.get_lock():
            counter.value += batch_size
    
        # Display progress
        if counter.value % 10000 < batch_size:
            print(f"Generated Addresses: {counter.value} / {total_combinations}")
    
    pool.close()
    pool.join()

# Function to handle writing matches to file
def writer(found_queue, stop_event):
    with open("found.txt", "a") as found_file:
        while not stop_event.is_set() or not found_queue.empty():
            try:
                mnemonic_phrase, bip44_address, bip32_address = found_queue.get(timeout=1)
                found_file.write(f"Mnemonic: {mnemonic_phrase}\n")
                found_file.write(f"BIP44 Address: {bip44_address}\n")
                found_file.write(f"BIP32 Address: {bip32_address}\n\n")
                found_file.flush()
                print(f"Match found! Mnemonic: {mnemonic_phrase} | BIP44 Address: {bip44_address} | BIP32 Address: {bip32_address}")
            except:
                continue

# Main execution
def main():
    mnemonic_phrase_input = input("Enter mnemonic phrase (use '____' for missing words): ").strip()
    mnemonic_template = mnemonic_phrase_input.split()
    target_addresses = load_target_addresses("target_addresses.txt")
    wordlist = load_bip39_wordlist("bip39-wordlist.txt")
    
    if not wordlist or not target_addresses:
        print("Error: Required files are missing or empty.")
        sys.exit(1)
    
    missing_positions = [i for i, word in enumerate(mnemonic_template) if word == "____"]
    num_missing = len(missing_positions)
    
    if num_missing == 0:
        print("No missing words to recover.")
        sys.exit(0)
    
    total_combinations = len(wordlist) ** num_missing
    print(f"Total combinations to try: {total_combinations}")
    
    manager = Manager()
    found_queue = manager.Queue()
    stop_event = manager.Event()
    counter = Value('i', 0)
    
    # Start the writer process
    writer_process = multiprocessing.Process(target=writer, args=(found_queue, stop_event))
    writer_process.start()
    
    # Start the recovery process
    recover_mnemonic_with_missing_words(
        mnemonic_template, 
        target_addresses, 
        wordlist, 
        found_queue, 
        counter, 
        total_combinations
    )
    
    # Signal the writer to stop
    stop_event.set()
    writer_process.join()
    
    print(f"Total Generated Addresses: {counter.value}")
    print("Recovery process completed.")

if __name__ == "__main__":
    main()
