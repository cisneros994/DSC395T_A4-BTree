import random
import graph
from py_btrees.btree import BTree

M = 3
L = 3
btree = BTree(M, L)
keys = [i for i in range(12)]
random.shuffle(keys)
for k in keys:
    btree.insert(k, str(k))

g = graph.create(btree)
g.view()
