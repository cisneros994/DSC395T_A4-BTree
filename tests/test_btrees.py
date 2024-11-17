from random import random

from py_btrees.disk import DISK
from py_btrees.btree import BTree
from py_btrees.btree_node import BTreeNode, get_node
import graph
import random

import pytest
from typing import Any

# This is a rewriting of all of the specifications that the handout provides,
# except it does not test the property that all leaf nodes reside at the same level.
# Note that fulfilling all of these requirements does NOT guarantee a working BTree.
def btree_properties_recurse(root_node_addr, node, M, L):

    assert sorted(node.keys) == node.keys # Keys should remain sorted so that a binary search is possible

    if node.is_leaf:
        # Leaf node general properties
        assert len(node.children_addrs) == 0
        assert len(node.keys) == len(node.data)
        assert len(node.data) <= L
    else:
        # Non-leaf node general properties
        assert len(node.data) == 0
        assert len(node.keys) == len(node.children_addrs) - 1
        assert len(node.children_addrs) <= M

    if node.my_addr == root_node_addr:
        # Root node properties
        assert node.parent_addr is None
        assert node.index_in_parent is None
        if not node.is_leaf:
            assert len(node.children_addrs) >= 2
    else:
        # Non-root node properties
        assert node.parent_addr is not None
        assert node.index_in_parent is not None
        if node.is_leaf:
            assert len(node.data) >= (L+1)//2
        else:
            assert len(node.children_addrs) >= (M+1)//2
        
    # Run the assertions on all children
    for child_addr in node.children_addrs:
        btree_properties_recurse(root_node_addr, DISK.read(child_addr), M, L)

def test_btree_properties_even() -> None:
    M = 6
    L = 6
    btree = BTree(M, L)
    for i in range(100):
        btree.insert(i, str(i))
    for i in range(0, -100, -1):
        btree.insert(i, str(i))

    root_addr = btree.root_addr
    btree_properties_recurse(root_addr, DISK.read(root_addr), M, L)

def test_btree_properties_odd() -> None:
    M = 5
    L = 3
    btree = BTree(M, L)
    for i in range(100):
        btree.insert(i, str(i))
    for i in range(0, -100, -1):
        btree.insert(i, str(i))

    root_addr = btree.root_addr
    btree_properties_recurse(root_addr, DISK.read(root_addr), M, L)


# If you want to run tests with various parameters, lookup pytest fixtures
def test_insert_and_find_odd():
    M = 3
    L = 3
    btree = BTree(M, L)
    btree.insert(0, "0")
    btree.insert(1, "1")
    btree.insert(2, "2")
    btree.insert(3, "3") # SPLIT!
    btree.insert(4, "4")

    root = DISK.read(btree.root_addr)
    assert not root.is_leaf
    assert len(root.keys) == 1
    assert root.keys[0] in [1, 2] # the split must divide the data evenly, so the key will be 1 or 2 depending on how you represent the keys array
    assert len(root.children_addrs) == 2
    left_child = DISK.read(root.children_addrs[0])
    right_child = DISK.read(root.children_addrs[1])

    assert left_child.is_leaf
    assert right_child.is_leaf
    assert right_child.parent_addr == root.my_addr
    assert right_child.index_in_parent == 1
    for key in left_child.keys:
        assert key in [0, 1]
    for key in right_child.keys:
        assert key in [2, 3, 4]

    assert btree.find(0) == "0"
    assert btree.find(4) == "4"

def test_insert_and_find_even():
    M = 3
    L = 2
    btree = BTree(M, L)
    btree.insert(0, "0")
    btree.insert(1, "1")
    btree.insert(2, "2") # SPLIT!

    root = DISK.read(btree.root_addr)
    assert not root.is_leaf
    assert len(root.keys) == 1
    assert root.keys[0] in [0, 1, 2] # You can divide the data into [0] [1 2] or [0 1] [2], so since the keys representation could mean left or right, it can be 0, 1, or 2
    assert len(root.children_addrs) == 2
    left_child = DISK.read(root.children_addrs[0])
    right_child = DISK.read(root.children_addrs[1])

    assert left_child.is_leaf
    assert right_child.is_leaf
    for key in left_child.keys:
        assert key in [0, 1]
    for key in right_child.keys:
        assert key in [1, 2]

    assert btree.find(0) == "0"
    assert btree.find(2) == "2"

def test_insert_and_find_edge():
    M = 3
    L = 1
    btree = BTree(M, L)
    btree.insert(0, "0")
    btree.insert(1, "1") # SPLIT!

    root = DISK.read(btree.root_addr)
    assert not root.is_leaf
    assert len(root.keys) == 1
    assert root.keys[0] in [0, 1]
    assert len(root.children_addrs) == 2
    left_child = DISK.read(root.children_addrs[0])
    right_child = DISK.read(root.children_addrs[1])

    assert left_child.is_leaf
    assert right_child.is_leaf
    for key in left_child.keys:
        assert key in [0]
    for key in right_child.keys:
        assert key in [1]

    assert btree.find(0) == "0"
    assert btree.find(1) == "1"

def test_other_datatypes():
    M = 3
    L = 3
    btree = BTree(M, L)
    btree.insert("0", "0")
    btree.insert("1", "1")
    btree.insert("2", "2")
    btree.insert("-2", "-2")
    graphTree(btree)
    btree.insert("hello", "there")
    graphTree(btree)
    btree.insert("0", "3")
    graphTree(btree)

    assert btree.find("1") == "1"
    assert verify_leaf_depth(btree)

def test_insert_50():
    M = 4
    L = 4
    btree = BTree(M, L)
    keys = [i for i in range(50)]
    random.shuffle(keys)
    for k in keys:
        btree.insert(k, str(k))
        graphTree(btree)
        assert verify_leaf_depth(btree)
        test = 1

def verify_leaf_depth(btree) -> bool:
    def check_depth(node_addr, current_depth, leaf_depths):
        node = DISK.read(node_addr)
        if node.is_leaf:
            leaf_depths.append(current_depth)
        else:
            for child_addr in node.children_addrs:
                check_depth(child_addr, current_depth + 1, leaf_depths)

    leaf_depths = []
    check_depth(btree.root_addr, 0, leaf_depths)

    # All leaves should have the same depth
    return len(set(leaf_depths)) == 1

def graphTree(btree:BTree):
    g = graph.create(btree)
    g.view()
    print("\n")
    debug_traverse(btree)

def debug_traverse(btree:BTree, addr=None):
    if addr is None:
        addr = btree.root_addr

    node = DISK.read(addr)
    print(f"Node at address {addr}: keys={node.keys}, children_addrs={node.children_addrs}, index_of_parent={node.index_in_parent}")

    if not node.is_leaf:
        for child_addr in node.children_addrs:
            debug_traverse(btree, child_addr)

def test_find(): #PASS
    # Create a B-Tree instance
    btree = BTree(M=3, L=2)

    # Manually create nodes
    root_node = BTreeNode(my_addr=DISK.new(), parent_addr=None, index_in_parent=None, is_leaf=False)  # Non-leaf node
    root_node.keys = [10, 20]

    # Create intermediate non-leaf nodes
    left_intermediate = BTreeNode(my_addr=DISK.new(), parent_addr=root_node.my_addr, index_in_parent=0, is_leaf=False)  # Non-leaf intermediate node
    left_intermediate.keys = [7]

    right_intermediate = BTreeNode(my_addr=DISK.new(), parent_addr=root_node.my_addr, index_in_parent=1, is_leaf=False)  # Non-leaf intermediate node
    right_intermediate.keys = [17]

    # Create leaf nodes
    left_child = BTreeNode(my_addr=DISK.new(), parent_addr=left_intermediate.my_addr, index_in_parent=0, is_leaf=True)  # Leaf node
    left_child.keys = [5, 6]
    left_child.data = ['val5', 'val6']

    middle_child = BTreeNode(my_addr=DISK.new(), parent_addr=left_intermediate.my_addr, index_in_parent=1, is_leaf=True)  # Leaf node
    middle_child.keys = [8, 9]
    middle_child.data = ['val8', 'val9']

    right_left_child = BTreeNode(my_addr=DISK.new(), parent_addr=right_intermediate.my_addr, index_in_parent=0,
                                 is_leaf=True)  # Leaf node
    right_left_child.keys = [15]
    right_left_child.data = ['val15']

    right_right_child = BTreeNode(my_addr=DISK.new(), parent_addr=right_intermediate.my_addr, index_in_parent=1,
                                  is_leaf=True)  # Leaf node
    right_right_child.keys = [18]
    right_right_child.data = ['val18']

    # Link leaf nodes to intermediate nodes
    left_intermediate.children_addrs = [left_child.my_addr, middle_child.my_addr]
    right_intermediate.children_addrs = [right_left_child.my_addr, right_right_child.my_addr]

    # Link intermediate nodes to root
    root_node.children_addrs = [left_intermediate.my_addr, right_intermediate.my_addr]

    # Write nodes to disk
    DISK.write(root_node.my_addr, root_node)  # Writing non-leaf node (root)
    DISK.write(left_intermediate.my_addr, left_intermediate)  # Writing non-leaf intermediate node (left)
    DISK.write(right_intermediate.my_addr, right_intermediate)  # Writing non-leaf intermediate node (right)
    DISK.write(left_child.my_addr, left_child)  # Writing leaf node (left child)
    DISK.write(middle_child.my_addr, middle_child)  # Writing leaf node (middle child)
    DISK.write(right_left_child.my_addr, right_left_child)  # Writing leaf node (right left child)
    DISK.write(right_right_child.my_addr, right_right_child)  # Writing leaf node (right right child)

    # Set the root address in the B-Tree
    btree.root_addr = root_node.my_addr

    # Graph
    graphb(btree)

    # Test the find function
    assert btree.find(5) == "val5" # should find
    assert btree.find(15) == "val15"  # should find
    assert btree.find(7) is None # It exists, but is a non-leaf node. Therefore, should return None
    assert btree.find(10) is None # Doesn't exist. Therefore, should return None