import blockchain
import flask 
from flask import Flask, request, session
from flask_script import Manager, Server, Command, Option
from flask_session import Session
from uuid import uuid4
import json
import requests
import sys
import random


my_blockchain = blockchain.Blockchain()

app = Flask(__name__)
app.debug = True
SESSION_TYPE = 'filesystem'
app.config.from_object(__name__)
Session(app)
manager = Manager(app)

portNum = 1


def echo_nodes():
    for node in range(5000, int(session['node_id'])):
        my_blockchain.nodes.add(node)

        url = 'http://127.0.0.1:' + str(node) + '/nodes/new'
        data = {'node': session['node_id']}
        headers = {'Content-type': 'application/json'}
        r = requests.post(url=url, json=data, headers=headers)


@manager.command
def runserver(port):
    portNum = port

    session['node_id'] = port
    echo_nodes()
    app.run(port=int(port))


@app.route('/transactions', methods=['GET'])
def get_transactions():
    if not my_blockchain.pending_transactions:
        return 'No pending transactions'
        
    return json.dumps(my_blockchain.pending_transactions)


@app.route('/transactions/new', methods=['POST'])
def new_transactions():
    data = request.get_json()

    # Check that required fields are in post response
    required = ['sender', 'recipient', 'amount']
    if not all(k in data for k in required):
        return 'Error: Missing transaction data', 400
        
    block_index = my_blockchain.new_transaction(data['sender'], data['recipient'], data['amount'])
        
    for node in my_blockchain.nodes:
        url = 'http://127.0.0.1:' + str(node) + '/transactions/add'
        headers = {'Content-type': 'application/json'}
        response = requests.post(url=url, json=data, headers=headers)

    return f'Transaction will be added to block {block_index}', 201


#Internal use
@app.route('/transactions/add', methods=['POST'])
def add_transactions():
    data = request.get_json()

    block_index = my_blockchain.new_transaction(data['sender'],  data['recipient'], data['amount'])

    return 'Transaction added to pending transactions'


@app.route('/chain', methods=['GET'])
def get_chain():
    chain = []
    for block in my_blockchain.chain:
        chain.append(block.__dict__)

    return json.dumps(chain)


@app.route('/chain/hack', methods=['GET'])
def hack_chain():
    block_index = random.randint(1, len(my_blockchain.chain)-1)
    transaction_id = random.randint(0, len(my_blockchain.chain[block_index].transactions)-1)
    my_blockchain.hack_chain(block_index, transaction_id)

    return f'Block {block_index} changed'


@app.route('/mine/port', methods=['GET'])
def mine():

    server_id = str(request.host)
    block = my_blockchain.mine(server_id[-4:])


    if not block:
        return 'Nik Cheem Blockchain - Error Connection Timed Out (Exceeded Time Limit)'

    # Reward for mining
    my_blockchain.new_transaction(
        sender = 0,
        recipient = session.get('node_id'),
        amount = 1
    )

    for node in my_blockchain.nodes:
        url = 'http://127.0.0.1:' + str(node) + '/blocks/new'
        data = json.dumps(block.__dict__, sort_keys=True)
        headers = {'Content-type': 'application/json'}
        r = requests.post(url=url, json=data, headers=headers)

    return f'Block {block.index} is mined'

#Internal use
@app.route('/blocks/new', methods=['POST'])
def new_block():
    data = json.loads(request.get_json())

    block = blockchain.Block(
        index = data['index'],
        timestamp = data['timestamp'],
        transactions = data['transactions'],
        previous_hash = data['previous_hash'],
        nonce = data['nonce']             
    )

    added = my_blockchain.add_block(block)

    if not added:
        return 'Block was discarded by the node', 400

    return 'Block added to chain', 201


@app.route('/nodes', methods=['GET'])
def get_peers():
    if not my_blockchain.nodes:
        return 'Node does not have any peers'

    nodes = []
    for node in my_blockchain.nodes:
        nodes.append(node)

    return json.dumps(nodes)


#Internal use
@app.route('/nodes/new', methods=['POST']) 
def new_node():
    data = request.get_json()

    node = data['node']
    if node is None:
        return 'Error: Please supply a valid node', 400

    my_blockchain.nodes.add(node)

    response = {
        'message': 'New node added',
        'total_nodes': len(my_blockchain.nodes)
    }

    return response, 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    # Replace chain with longest valid chain in network

    replaced = False
    longest_chain = my_blockchain.chain
    chain_len = len(my_blockchain.chain)

    for node in my_blockchain.nodes:
        chain = []

        # Create blockchain instance from json string returned by node
        url = 'http://127.0.0.1:' + str(node) + '/chain'
        response = requests.get(url)
        data = response.json()
        
        for i in range(0, len(data)):
            block = blockchain.Block(
                index = data[i]['index'],
                timestamp = data[i]['timestamp'],
                transactions = data[i]['transactions'],
                previous_hash = data[i]['previous_hash'],
                nonce = data[i]['nonce']             
            )

            chain.append(block)

        if my_blockchain.validate_chain(longest_chain):
            if my_blockchain.validate_chain(chain) and len(chain) > chain_len:
                replaced = True
                chain_len = len(chain)
                longest_chain = chain
        else:
            replaced = True
            chain_len = len(chain)
            longest_chain = chain
           
    if replaced:
        my_blockchain.chain = longest_chain
        return 'Our chain was replaced'

    return 'Our chain is authoritative'


if __name__ == '__main__':
    manager.run()