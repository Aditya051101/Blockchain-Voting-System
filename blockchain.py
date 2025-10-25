import hashlib, json, time, os
from typing import List, Dict, Any
import config

class Block:
    def __init__(self, index:int, previous_hash:str, timestamp:float, transactions:List[Dict[str,Any]], nonce:int=0):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.transactions = transactions
        self.nonce = nonce
        self.hash = self.compute_hash()

    def compute_hash(self) -> str:
        block_string = json.dumps({
            "index": self.index,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "nonce": self.nonce
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def to_dict(self):
        return {
            "index": self.index,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "nonce": self.nonce,
            "hash": self.hash
        }

class Blockchain:
    def __init__(self, chain_file: str = config.BLOCKCHAIN_FILE, difficulty: int = config.POW_DIFFICULTY):
        self.chain_file = chain_file
        self.difficulty = difficulty
        self.unconfirmed_transactions: List[Dict[str,Any]] = []
        self.chain: List[Block] = []
        self._ensure_chain_file()
        self._load_chain()

    # ✅ Create genesis block
    def create_genesis_block(self) -> Block:
        return Block(0, "0", time.time(), [], 0)

    def _ensure_chain_file(self):
        dirp = os.path.dirname(self.chain_file)
        if dirp and not os.path.exists(dirp):
            os.makedirs(dirp, exist_ok=True)
        if not os.path.exists(self.chain_file):
            genesis = self.create_genesis_block()
            with open(self.chain_file, "w") as f:
                json.dump([genesis.to_dict()], f, indent=2)

    def _load_chain(self):
        with open(self.chain_file, "r") as f:
            data = json.load(f)
        self.chain = []
        for b in data:
            block = Block(b["index"], b["previous_hash"], b["timestamp"], b["transactions"], b.get("nonce",0))
            block.hash = b.get("hash") or block.compute_hash()
            self.chain.append(block)
        if not self.is_valid_chain():
            raise Exception("Blockchain validation failed on startup! Chain may be tampered.")

    @property
    def last_block(self) -> Block:
        return self.chain[-1]

    # ✅ Add a vote and mine immediately (one vote = one block)
    def add_new_transaction(self, tx: Dict[str,Any]):
        """Immediately mine each transaction as its own block."""
        last = self.last_block
        new_block = Block(
            index=last.index + 1,
            previous_hash=last.hash,
            timestamp=time.time(),
            transactions=[tx],  # Single transaction per block
            nonce=0
        )
        proof = self.proof_of_work(new_block)
        added = self.add_block(new_block, proof)
        if added:
            self._write_chain()
            return new_block.index
        return -1

    def proof_of_work(self, block: Block) -> str:
        block.nonce = 0
        computed_hash = block.compute_hash()
        target_prefix = "0" * self.difficulty
        while not computed_hash.startswith(target_prefix):
            block.nonce += 1
            computed_hash = block.compute_hash()
        return computed_hash

    def add_block(self, block: Block, proof: str) -> bool:
        previous_hash = self.last_block.hash
        if previous_hash != block.previous_hash:
            return False
        if not proof.startswith("0" * self.difficulty) or proof != block.compute_hash():
            return False
        block.hash = proof
        self.chain.append(block)
        return True

    def to_list(self) -> List[Dict[str,Any]]:
        return [b.to_dict() for b in self.chain]

    def _write_chain(self):
        with open(self.chain_file, "w") as f:
            json.dump(self.to_list(), f, indent=2)

    def is_valid_chain(self) -> bool:
        for i in range(1, len(self.chain)):
            curr = self.chain[i]
            prev = self.chain[i-1]
            if curr.previous_hash != prev.hash:
                return False
            if curr.compute_hash() != curr.hash:
                return False
            if not curr.hash.startswith("0" * self.difficulty):
                return False
        return True

    def find_votes_by_voter(self, voter_public_key_hex: str) -> List[Dict[str,Any]]:
        res = []
        for b in self.chain:
            for tx in b.transactions:
                if tx.get("voter_pub") == voter_public_key_hex:
                    res.append(tx)
        return res

    # ✅ Reset blockchain
    def reset_chain(self):
        self.chain = [self.create_genesis_block()]
        self._write_chain()
