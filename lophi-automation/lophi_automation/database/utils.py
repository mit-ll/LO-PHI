"""
    Utilities for handling aiding our database operations

    (c) 2015 Massachusetts Institute of Technology
"""

# Native
import hashlib

def calculate_combined_hash(file_path):
    md5sum = calculate_md5(file_path)
    sha1sum = calculate_sha1(file_path)
    sha256sum = calculate_sha256(file_path)
    sha512sum = calculate_sha512(file_path)
    return hashlib.md5(''.join([md5sum,
                                sha1sum,
                                sha256sum,
                                sha512sum])).hexdigest()


def calculate_sha512(local_path):
    hasher = hashlib.sha512()
    with open(local_path, 'rb') as f:
        for chunk in iter(lambda: f.read(128 * hasher.block_size), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def calculate_md5(local_path):
    hasher   = hashlib.md5()
    with open(local_path, 'rb') as f:
        for chunk in iter(lambda: f.read(128 * hasher.block_size), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def calculate_sha1(local_path):
    hasher   = hashlib.sha1()
    with open(local_path, 'rb') as f:
        for chunk in iter(lambda: f.read(128 * hasher.block_size), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def calculate_sha256(local_path):
    hasher   = hashlib.sha256()
    with open(local_path, 'rb') as f:
        for chunk in iter(lambda: f.read(128 * hasher.block_size), b''):
            hasher.update(chunk)
    return hasher.hexdigest()