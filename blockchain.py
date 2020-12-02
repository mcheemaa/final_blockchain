import time
import hashlib
import urllib.parse
from urllib.parse import urlparse
import json
import random


class Block:
    def __init__(self, index, timestamp, transactions, previous_hash, nonce=0, portnumber = 5000):
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.portnumber = portnumber

    def get_port(self):
        return self.portnumber


    def calc_hash(self):
        # Get SHA256 hash of block

        block_string = json.dumps(self.__dict__, sort_keys=True)
        #print("\nBlock String : ", block_string)
        raw_hash = hashlib.sha256(block_string.encode())
        hex_hash = raw_hash.hexdigest()
        return hex_hash

        
    def calc_proof(self, difficulty):
        # Simple proof of work algorithm - hash must begin with # of zeros defined by difficulty property

        hash = self.calc_hash()
        #print("Hash : ",  hash)


        start = time.perf_counter()
        while not hash.startswith('0' * difficulty):
            self.nonce += 1
            hash = self.calc_hash()
            #print("Hash Inside : ",  hash)
            if ((time.perf_counter() - start) >= 30):
                hash = 404
                return hash

        print("Completed In: " + str((time.perf_counter() - start)) + " seconds")
        return hash


class Blockchain:
    def __init__(self):
        self.chain = []
        self.pending_transactions = []
        self.nodes = set()
        self.create_genesis_block()


    @property
    def last_block(self):
        # Get last block in the chain

        return self.chain[-1]


    @property
    def difficulty(self):
        # Complexity of proof of work algorithm

        return 4


    def create_genesis_block(self):
        # Create the first block in the chain

        genesis_block = Block(
            index = 0,
            timestamp = 0,
            transactions = [],
            previous_hash = '0'
        )

        self.chain.append(genesis_block)


    def new_transaction(self, sender, recipient, amount):
        # Add transaction to the list

        transaction = {
            'sender': sender,
            'recipient': recipient,
            'amount': amount
        }

        self.pending_transactions.append(transaction)

        return len(self.chain)


    def mine(self, portN):
        # Create new block with pending transactions

        if not self.pending_transactions:
            return False

        block = Block(
            index = len(self.chain),
            timestamp = time.time(),
            transactions = self.pending_transactions,
            previous_hash = self.last_block.calc_hash(),
            portnumber = portN  
        )

        added = self.add_block(block)

        if added:
            self.pending_transactions = []

            return block
        else:
            return False


    def add_block(self, block):
        # Forge block to chain if valid
        porti = block.get_port()
        lastblock = self.last_block
        lastport = self.last_block.get_port()

        diff = self.difficulty

        if (porti == lastport):
            print("Warning Too Many Mining Requests - Difficulty Will Be Increased")
            diff = self.difficulty + 1
            proof = block.calc_proof(diff)
        else:
            proof = block.calc_proof(self.difficulty)

        if (block.calc_hash == 404):
            return False
        if block.previous_hash != self.last_block.calc_hash():
            return False

        if not self.validate_proof(block, proof, diff):
            return False

        self.chain.append(block)

        return True


    def validate_proof(self, block, proof, diff):
        # Validate the hash of a block 

        return (block.calc_hash().startswith('0' * diff) and proof == block.calc_proof(diff))


    def validate_chain(self, chain):
        # Ensure validity of block hashes to ensure the chain hasn't been tampered with

        for i in range (2, len(chain)):
            current_block = chain[i]
            previous_block = chain[i-1]
          
            if current_block.previous_hash != previous_block.calc_hash():
                return False

            if not current_block.calc_hash().startswith('0' * self.difficulty):
                return False

        return True


    def hack_chain(self, block_index, transaction_id):
        # Illegally change a transaction in a block in the chain to invalidate the chain (testing purposes)

        block = self.chain[block_index]
        transactions = []

        for i in range(0, len(block.transactions)-1):
            if i == transaction_id:
                sender = random.randint(0, len(self.nodes) - 1)
                recipient = random.randint(0, len(self.nodes) - 1)
                amount = random.randint(1, 100)
                new_transaction = {
                    'sender' : sender,
                    'recipient' : recipient,
                    'amount' : amount
                }
                transactions.append(new_transaction)
            else:
                transactions.append(block.transactions[i])

        block.transactions = transactions
        self.chain[block_index] = block

        return block_index

