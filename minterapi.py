# -------------------------------- LIBRARIES -------------------------------- #
from web3 import Web3
from web3.middleware import geth_poa_middleware
import time
import json

SENDER_ADDRESS = ''
PRIVATE_KEY = ''
RPC_URL = 'https://avalanche.drpc.org'
NFT_CA = ''
NFT_ABI_FILE = 'krooxabi.json'
MINT_COST = 0.690777
MINT_COST_WEI = int(MINT_COST * 10**18)

# ------------------------------- MAIN CLASS -------------------------------- #
class minter(object):
# ------------------------------- INITIALIZE -------------------------------- #
    def __init__(self):
        with open(NFT_ABI_FILE) as abi_file:
            self.nft_abi = json.load(abi_file)
        self.web3 = Web3(Web3.HTTPProvider(RPC_URL))
        self.SENDER_ADDRESS = self.web3.to_checksum_address(SENDER_ADDRESS)
        self.PRIVATE_KEY = PRIVATE_KEY
        self.start_balance = self.getBalance()
        self.nft_ca = NFT_CA
        self.MINT_COST = MINT_COST_WEI
        self.contract = self.web3.eth.contract(address=self.web3.to_checksum_address(self.nft_ca), abi=self.nft_abi)
        print('Starting Balance (AVAX): ', self.start_balance)
        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)


# ---------------------------------- UTILS ---------------------------------- #
    def getBalance(self):  # Get AVAX balance
        return self.web3.from_wei(self.web3.eth.get_balance(self.SENDER_ADDRESS), 'ether')

    def getNonce(self):  # Get address nonce
        return self.web3.eth.get_transaction_count(self.SENDER_ADDRESS)

    def mint(self, to):
        to = self.web3.to_checksum_address(to)
        # Get the nonce for the transaction
        nonce = self.web3.eth.get_transaction_count(self.SENDER_ADDRESS)

        # Build the transaction
        transaction = self.contract.functions.mintToMultiple(to, 1).build_transaction({
            'value': self.MINT_COST,
            'gas': 200000,  # Adjust the gas limit as needed
            'nonce': nonce,
        })

        # Sign the transaction with the private key
        signed_txn = self.web3.eth.account.sign_transaction(transaction, self.PRIVATE_KEY)

        # Attempt to send the transaction
        tx_hash_notify = 'None'
        try:
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            print(f"Transaction sent! Hash: {tx_hash.hex()}")
            tx_hash_notify = str(tx_hash.hex())
        except Exception as e:
            print(f"Error sending transaction: {e}")

        txn_receipt = self.awaitReceipt(tx_hash_notify) # Wait for transaction to finish
        if txn_receipt.status == 1:
            nft_id = str(txn_receipt.logs[0].topics[3].hex())
            print('i got : ',nft_id)
            print('which is: ',int(nft_id, 16))
            return int(nft_id, 16)
        else:
            print('n/a')
            return -1

    def transfer(self, to, nft_id):
        to = self.web3.to_checksum_address(to)
        # Get the nonce for the transaction
        nonce = self.web3.eth.get_transaction_count(self.SENDER_ADDRESS)

        # Build the transaction
        transaction = self.contract.functions.safeTransferFrom(self.SENDER_ADDRESS, to, nft_id).build_transaction({
            'gas': 200000,  # Adjust the gas limit as needed
            'nonce': nonce,
        })

        # Sign the transaction with the private key
        signed_txn = self.web3.eth.account.sign_transaction(transaction, self.PRIVATE_KEY)

        # Attempt to send the transaction
        tx_hash_notify = 'None'
        try:
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            print(f"Transaction sent! Hash: {tx_hash.hex()}")
            tx_hash_notify = str(tx_hash.hex())
        except Exception as e:
            print(f"Error sending transaction: {e}")

        return tx_hash_notify

    def refund_remainder(self, to, amount):
        to = self.web3.to_checksum_address(to)
        tx_hash = self.web3.eth.send_transaction({
            "from": self.SENDER_ADDRESS,
            "value": self.web3.to_wei(amount, 'ether'),
            "to": to
        })
        print(tx_hash)

    def estimateGas(self, txn):
        gas = self.w3.eth.estimateGas({
                    "from": txn['from'],
                    "to": txn['to'],
                    "value": txn['value'],
                    "data": txn['data']})
        gas = gas + (gas / 10) # Adding 1/10 from gas to gas!
        maxGasAVAX = Web3.from_wei(gas * self.gas_price, "ether")
        print(style.GREEN + "\nMax Transaction cost " + str(maxGasAVAX) + " AVAX" + style.RESET)

        if maxGasAVAX > self.MaxGasInAVAX:
            print(style.RED +"\nTx cost exceeds your settings, exiting!")
            raise SystemExit
        return gas

    def awaitReceipt(self, tx):
        try:
            return self.web3.eth.wait_for_transaction_receipt(tx, timeout=30)
        except Exception as ex:
            print('Failed to wait for receipt: ', ex)
            return None
