import bisect
from typing import Any, List, Optional, Tuple, Union, Dict, Generic, TypeVar, cast, NewType
from py_btrees.disk import DISK, Address
from py_btrees.btree_node import BTreeNode, KT, VT, get_node

"""
----------------------- Starter code for your B-Tree -----------------------

Helpful Tips (You will need these):
1. Your tree should be composed of BTreeNode objects, where each node has:
    - the disk block address of its parent node
    - the disk block addresses of its children nodes (if non-leaf)
    - the data items inside (if leaf)
    - a flag indicating whether it is a leaf

------------- THE ONLY DATA STORED IN THE `BTree` OBJECT SHOULD BE THE `M` & `L` VALUES AND THE ADDRESS OF THE ROOT NODE -------------
-------------              THIS IS BECAUSE THE POINT IS TO STORE THE ENTIRE TREE ON DISK AT ALL TIMES                    -------------

2. Create helper methods:
    - get a node's parent with DISK.read(parent_address)
    - get a node's children with DISK.read(child_address)
    - write a node back to disk with DISK.write(self)
    - check the health of your tree (makes debugging a piece of cake)
        - go through the entire tree recursively and check that children point to their parents, etc.
        - now call this method after every insertion in your testing and you will find out where things are going wrong
3. Don't fall for these common bugs:
    - Forgetting to update a node's parent address when its parent splits
        - Remember that when a node splits, some of its children no longer have the same parent
    - Forgetting that the leaf and the root are edge cases
    - FORGETTING TO WRITE BACK TO THE DISK AFTER MODIFYING / CREATING A NODE
    - Forgetting to test odd / even M values
    - Forgetting to update the KEYS of a node who just gained a child
    - Forgetting to redistribute keys or children of a node who just split
    - Nesting nodes inside of each other instead of using disk addresses to reference them
        - This may seem to work but will fail our grader's stress tests
4. USE THE DEBUGGER
5. USE ASSERT STATEMENTS AS MUCH AS POSSIBLE
    - e.g. `assert node.parent != None or node == self.root` <- if this fails, something is very wrong

--------------------------- BEST OF LUCK ---------------------------
"""

# Complete both the find and insert methods to earn full credit
class BTree:
    def __init__(self, M: int, L: int):
        """
        Initialize a new BTree.
        You do not need to edit this method, nor should you.
        """
        self.root_addr: Address = DISK.new() # Remember, this is the ADDRESS of the root node
        # DO NOT RENAME THE ROOT MEMBER -- LEAVE IT AS self.root_addr
        DISK.write(self.root_addr, BTreeNode(self.root_addr, None, None, True))
        self.M = M # M will fall in the range 2 to 99999 # max number of children for non-leaf & non-root nodes
        self.L = L # L will fall in the range 1 to 99999 # max number of data items for leaf nodes

    def insert(self, key: KT, value: VT) -> None:
        """
        Insert the key-value pair into your tree.
        It will probably be useful to have an internal
        _find_node() method that searches for the node
        that should be our parent (or finds the leaf
        if the key is already present).

        Overwrite old values if the key exists in the BTree.

        Make sure to write back all changes to the disk!
        """
        #Step 1: If the key already exists in the tree, then replace the value
        existing_value = self.find(key)
        if existing_value is not None:
            # If key exists, update the value
            existing_node = self._find_node(key)
            existing_node.insert_data(key, value)
            existing_node.write_back()
            return

        # Step 2: Find the leaf node for insertion in disk
        leaf_node = self._find_node(key)

        # Step 3: Insert key-value pair into the leaf node
        # Checks to see if there's room in the leaf node to add data
        if len(leaf_node.data) < self.L:
            # modifies the node in memory
            leaf_node.insert_data(key, value)
        # Step 4: Splits the node to create more room
        else:
            # Redistribute data between leaf nodes before splitting
            #if self._redistribute(leaf_node, key, value):
                #return
            # Handle node split to make more room for data
            #else:
            self._split_node(leaf_node, key, value)
        # Step 5: Write the updated node from memory to disk
        leaf_node.write_back()

    def _split_node(self, node:BTreeNode, key: Optional[KT]=None, value: Optional[VT]=None) -> None:
        """
        Recursively handles the splitting of a node when it exceeds the maximum number of children (M).
        """
        # Step 1: Split data and keys b/w old and new nodes due to lack of space
        # Save the middle key before modifying the node; division of midpoint index of L data items
        mid_idx = self.L // 2

        # Create a new node (self address, parent address, index_in_parent, current node is_leaf)
        new_node = BTreeNode(DISK.new(), node.parent_addr, None, node.is_leaf)
        # Split the keys & data of (old) node b/w (old) node & new node
        # Need to edit data only (& keys) b/c it's a leaf
        if node.is_leaf:
            # insert data into node
            node.insert_data(key, value)
            # new node retains right half from original node
            # node retains (and rewrites) left half from original node; would have more items if odd number
            new_node.keys = node.keys[mid_idx+1:]
            new_node.data = node.data[mid_idx+1:]
            node.keys = node.keys[:mid_idx+1]
            node.data = node.data[:mid_idx+1]

        # Need to edit children addrs only (& keys) b/c it's a non-leaf. Need to also remove mid idx key that will be promoted to the parent
        else:
            # new node retains right half from original node after the midpoint index since the middle key is promoted to the parent
            # node retains (and rewrites) left half from original node; would have more items if odd number
            new_node.keys = node.keys[mid_idx+1:]
            new_node.children_addrs = node.children_addrs[mid_idx+1:]
            node.keys = node.keys[:mid_idx]
            node.children_addrs = node.children_addrs[:mid_idx+1]

        # Step 2: Update parent's mapping info
        # If the node is the root
        if node.parent_addr is None:
            # Create a new root node if the split happens at the root
            new_root_node = BTreeNode(DISK.new(), None, None, False)
            # Promotes the middle key to create a new root during the split
            new_root_node.keys = [node.keys[-1]]
            # link the new children addresses (node, new node) to the new root
            new_root_node.children_addrs = [node.my_addr, new_node.my_addr]
            # The B-Tree's reference to the root is updated to point to the newly created root node
            self.root_addr = new_root_node.my_addr
            # leaf node and new leaf node need to update their parent addresses to point to the new root
            node.parent_addr = self.root_addr
            new_node.parent_addr = self.root_addr
            # Update index_in_parent for all children of the new root
            node.index_in_parent = 0
            new_node.index_in_parent = 1

            node.write_back()
            new_node.write_back()

            # Check if root node exceeds max amount of children
            if len(new_root_node.children_addrs) > self.M:
                self._split_node(new_root_node)
            # Writes the updated root node from memory to disk
            else:
                new_root_node.write_back()
        # If the node is a non-root, split the parent & update the parent's keys and pointers
        else:
            # reads the parent node into memory
            parent_node = node.get_parent()
            # split the parent node by creating a new key in the parent via the mid key in the node
            # finds the correct index in the parent node where the middle key from the split node should be inserted
            # find_idx determines the appropriate position of the newly inserted key to maintain the sorted order
            insert_idx = parent_node.find_idx(node.keys[-1])
            # inserts the middle key into the keys list of the parent node at the position found by insert_idx
            # insert(idx position, object)
            parent_node.keys.insert(insert_idx, node.keys[-1])
            # inserts the new node address into the next position of the parent's list of child addresses
            parent_node.children_addrs.insert(insert_idx + 1, new_node.my_addr)
            # Update parent pointers for the new node
            new_node.parent_addr = node.parent_addr
            new_node.index_in_parent = insert_idx+1
            # Update index of parent
            parent_node.write_back()
            node.write_back()
            new_node.write_back()
            #for i in range(insert_idx + 2, len(parent_node.children_addrs)):
            for i in range(len(parent_node.children_addrs)):
                child = get_node(parent_node.children_addrs[i])
                child.index_in_parent = i
                child.write_back()

            # Check if parent node exceeds max amount of children
            if len(parent_node.children_addrs) > self.M:
                self._split_node(parent_node)
            # Writes the updated parent node from memory to disk
            #else:
                #parent_node.write_back()

        # Step 3: Write the node & new node from memory to disk
        #node.write_back()
        #new_node.write_back()

    def _update_index_of_parent(self, parent_node:BTreeNode):
        for i, addr in enumerate(parent_node.children_addrs):
            child_node = get_node(addr)
            child_node.index_in_parent = i
            child_node.write_back()

    def _redistribute(self, key: KT, value: VT) -> bool:
        """
        Check empty data items in surrounding leaf nodes to redistribute data versus splitting the node
        """

    def find(self, key: KT) -> Optional[VT]:
        """
        Find a key and return the value associated with it.
        If it is not in the BTree, return None.

        This should be implemented with a logarithmic search
        in the node.keys array, not a linear search. Look at the
        BTreeNode.find_idx() method for an example of using
        the builtin bisect library to search for a number in 
        a sorted array in logarithmic time.
        """
        # Finds the node that should be our parent.
        current_node = self._find_node(key)

        # At the leaf node, check to see if key exists
        # Return node if key is found, Will return None if key isn't found.
        return current_node.find_data(key)

    def _find_node(self, key: KT) -> Optional[BTreeNode]:
        """
        Finds the node that should be our parent for insertion.
        """
        # Step 1: Start at the root
        current_addr = self.root_addr
        # Uses DISK.read() to read its address in memory and return the B-Tree node
        current_node = get_node(current_addr)

        # Step 2: Traverse the B-Tree until a leaf node is reached that contains the data
        while not current_node.is_leaf:
            # Use logarithmic search to find the current key or the new location of where to insert the key
            idx = current_node.find_idx(key)
            # Traverse to the correct child address & node that corresponds to idx
            current_node = current_node.get_child(idx)

        # Step 3: Return the node of our parent; will not be 'None'
        return current_node

    def delete(self, key: KT) -> None:
        raise NotImplementedError("Karma method delete()")
