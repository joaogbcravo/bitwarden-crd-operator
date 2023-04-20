import os
import json
import subprocess

class BitwardenCommandException(Exception):
    pass

def get_secret_from_bitwarden(logger, spec):
    if 'id' in spec:
        id = spec.get('id')
        logger.info(f"Looking up secret with ID: {id}")
        return get_secret_with_id_from_bitwarden(id)
    elif 'itemName' in spec and 'collectionPath' in spec:
        item_name = spec.get('itemName')
        collection_path = spec.get('collectionPath')
        logger.info(f"Looking up '{item_name}' secret in '{collection_path}' collection")
        return get_collection_secret_from_bitwarden(collection_path, item_name)
    else:
        raise BitwardenCommandException("Either 'id' or ('itemName' and 'collectionPath') need to be provided")

def get_secret_with_id_from_bitwarden(id):
    return json.loads(command_wrapper(command=f"get item {id}"))

def get_collection_secret_from_bitwarden(collection_path, item_name):
    collection_id = get_collection_from_bitwarden_with_path(collection_path)

    bitwarden_answer = command_wrapper(command=f"list items --collectionid {collection_id}")
    items = json.loads(bitwarden_answer)
    items = [obj for obj in items if obj['name'] == item_name]
    if not items:
        raise BitwardenCommandException(f"No item with name '{item_name}' found in in '{collection_path}' collection")
    if len(items) > 1:
        raise BitwardenCommandException(f"Multiple items found with name '{item_name}' in '{collection_path}' collection - name must be unique.")
    return items[0]

def get_collection_from_bitwarden_with_path(collection_path):
    bitwarden_answer = command_wrapper(command=f"list collections")
    collections = json.loads(bitwarden_answer)
    collections = [obj for obj in collections if obj['name'] == collection_path]
    if not collections:
        raise BitwardenCommandException(f"No collection with path '{collection_path}' found.")
    if len(collections) > 1:
        raise BitwardenCommandException(f"Multiple collections found with path '{collection_path}' - path must be unique.")
    return collections[0]['id']

def unlock_bw(logger):
    status_output = command_wrapper("status")
    status = json.loads(status_output)['status']
    if status == 'unlocked':
        logger.info("Already unlocked")
        return
    token_output = command_wrapper("unlock --passwordenv BW_PASSWORD")
    tokens = token_output.split('"')[1::2]
    os.environ["BW_SESSION"] = tokens[1]
    logger.info("Signin successful. Session exported")

def command_wrapper(command):
    system_env = dict(os.environ)
    sp = subprocess.Popen([f"bw {command}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True, shell=True, env=system_env)
    out, err = sp.communicate()
    if err:
        raise BitwardenCommandException(err)
    return out.decode(encoding='UTF-8')

def parse_login_scope(secret_json, key):
    return secret_json["login"][key]

def parse_fields_scope(secret_json, key):
    if "fields" not in secret_json:
        return None
    for entry in secret_json["fields"]:
        if entry['name'] == key:
            return entry['value']
