import hashlib
import requests
import json
from textwrap import dedent
from time import time
from uuid import uuid4
from flask import Flask, jsonify, request, render_template
from urllib.parse import urlparse
import os
#https://www.therealtomrose.com/how-to-debug-python-or-django-in-heroku/

class Blockchain(object):

    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = []
        self.new_block(previous_hash='1', proof=100)
        self.deploynode = "https://pyblockchain.herokuapp.com"

    def register_node(self, address):
        self.nodes.append(address)


    def valid_chain(self, chain):

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            # Check that the hash of the block is correct
            last_block_hash = self.hash(last_block)
            if block['previous_hash'] != last_block_hash:
                return False

            # Check that the Proof of Work is correct
            if not self.valid_proof(last_block['proof'], block['proof'], last_block_hash):
                return False

            last_block = block
            current_index += 1

        return True


    def resolve_conflicts(self):
        """
        This is our consensus algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.
        :return: True if our chain was replaced, False if not
        """

        neighbours = self.nodes
        new_chain = None

        # We're only looking for chains longer than ours
        max_length = len(self.chain)

        # Grab and verify the chains from all the nodes in our network
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if the length is longer and the chain is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            return True

        return False

    def new_block(self, proof, previous_hash):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # Reset the current list of transactions
        self.current_transactions = []

        self.chain.append(block)
        return block


    def new_transaction(self, sender, recipient, amount):
        """
        Creates a new transaction to go into the next mined Block
        :param sender: <str> Address of the Sender
        :param recipient: <str> Address of the Recipient
        :param amount: <int> Amount
        :return: <int> The index of the Block that will hold this transaction
        """

        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })

        return self.last_block['index'] + 1





    @property
    def last_block(self):
        # Returns the last Block in the chain
        return self.chain[-1]


    @staticmethod
    def hash(block):
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()




    def proof_of_work(self, last_proof):
        """
        Simple Proof of Work Algorithm:
         - Find a number p' such that hash(pp') contains leading 4 zeroes, where p is the previous p'
         - p is the previous proof, and p' is the new proof
        :param last_proof: <int>
        :return: <int>
        """

        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        """
        Validates the Proof: Does hash(last_proof, proof) contain 4 leading zeroes?
        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :return: <bool> True if correct, False if not.
        """

        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"



# Instantiate our Node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain
blockchain = Blockchain()

@app.route('/')
def render():
    return render_template('home.html')


@app.route('/mine', methods=['GET'])
def mine():
    # We run the proof of work algorithm to get the next proof...
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # We must receive a reward for finding the proof.
    # The sender is "0" to signify that this node has mined a new coin.
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
    )

    # Forge the new Block by adding it to the chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return render_template('home.html',resp=json.dumps(response)), 200
  
@app.route('/transactions/new', methods=['POST', 'GET'])
def new_transaction():
    if request.method == 'POST':
        values = request.get_json()

        required = ['sender', 'recipient', 'amount']
        if not all(k in values for k in required):
            return 'Missing values', 400

        # Create a new Transaction
        index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

        response = {'message': f'Transaction will be added to Block {index}'}
        return jsonify(response), 201
        #return render_template('home.html',respTrans=json.dumps(response)), 201
    else:
        #need method to get last transaction from stack, last member of "current transactions list", maybe len function
        index = self.last_block['index']
        response = {'message': f'Transaction will be added to Block {index}'}
        return render_template('home.html',respTrans=json.dumps(response)), 201

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return render_template('home.html',resp2=json.dumps(response)), 200

@app.route('/nodes/register', methods=['POST'])
def register_nodespost():
#test self add error, make new condition for if nodes empty
    values = request.get_json()
    if values is None:
        return jsonify({'Error': 'None values'}), 400
    node = values.get('nodes')
    print("node variable retrieved from json: "+node)
    print("blockchain deploynode property "+blockchain.deploynode)
    print("node == deploynode property test: ")
    print(node==blockchain.deploynode)
    if node is None:
        return jsonify({'Error': 'Please supply a valid list of nodes'}), 400
    if node == blockchain.deploynode:
        return jsonify({'Error': 'Self node added'}), 400

    listcheck = blockchain.nodes
    print("listcheck variable")
    print(*listcheck)
    listcheck.append(node)
    print("list check after appending node")
    print(*listcheck)
    print("len(blockchain-nodes)")
    print(len(blockchain.nodes))
    print("len-set-listcheck")
    print(len(set(listcheck)))
    if ((len(blockchain.nodes) == len(set(listcheck))) and (len(blockchain.nodes)>0)):
        return jsonify({'Error': 'Node exists'}), 400

    blockchain.register_node(node)

    response = {
        'message': 'New node has been added',
        'node added': node,
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201


@app.route('/nodes/register', methods=['GET'])
def register_nodesget():
    response = {
        'message': 'New nodes have been added',
        'len(blockchain.nodes)': len(blockchain.nodes),
        'total_nodes not list': blockchain.nodes,
        'total_nodes as list()': list(blockchain.nodes),
    }
    return render_template('home.html',respRegister=response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return render_template('home.html',resp3=json.dumps(response)), 200

@app.route('/chaintest', methods=['GET'])
def chaintest():
    response = blockchain.chain
    return jsonify(response), 200

@app.route('/posttransaction', methods=['POST'])
def posttransaction():
    values = request.get_json()
    print("sender "+values.get('sender')+" recipient "+values.get('recipient')+" amount "+values.get('amount'))
    # Check that the required fields are in the POST'ed data
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Create a new Transaction
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201


@app.route('/queryother', methods=['GET'])
def queryother():
    r = requests.get('https://pyblockchain.herokuapp.com/chaintest').json()
    #r is text by default, checked with respQuery=r.headers['content-type'] 
    return render_template('home.html',respQuery=r), 201

@app.route('/getnodes', methods=['GET'])
def getnodes():
    msg = {
        'message': 'Checking state of nodes list',
        'len(blockchain.nodes)': len(blockchain.nodes),
        'total_nodes not list': blockchain.nodes,
        'total_nodes as list()': list(blockchain.nodes),
    }
    return jsonify(msg), 200

@app.route('/posttransaction', methods=['GET'])
def getposttransaction():
    values = request.get_json()
    return jsonify(values), 200

#https://www.geeksforgeeks.org/get-post-requests-using-python/
@app.route('/getbalance', methods=['GET'])
def getbalance():
    values = request.get_json()
    return jsonify(values), 200  


if __name__ == '__main__':
    from argparse import ArgumentParser
    port = int(os.environ.get('PORT', 5000))
    #parser = ArgumentParser()
    #parser.add_argument('-p', '--port', default=33507, type=int, help='port to listen on')
    #args = parser.parse_args()
    #port = args.port

    app.run(host='0.0.0.0', port=port, debug=True)

       
    

