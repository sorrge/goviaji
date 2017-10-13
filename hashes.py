import random

hash_mask = 0xffffffffffffffff
combinator_value = 0xa0cf5a622e18b479


def new_hash():
    return random.getrandbits(64)


def combine_hashes(h1, h2):
    return h1 ^ ((h2 + combinator_value + (h1 << 6) + (h1 >> 2)) & hash_mask)


hashes_for_idx = []


def get_hash_for_idx(idx1, idx2):
    while idx1 >= len(hashes_for_idx):
        hashes_for_idx.append([])

    while idx2 >= len(hashes_for_idx[idx1]):
        hashes_for_idx[idx1].append(new_hash())

    return hashes_for_idx[idx1][idx2]
