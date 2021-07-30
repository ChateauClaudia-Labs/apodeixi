# NOTE
#
# This file is 100% documentation. It describes a mathematical/algorithmic concept called an "AssertionTree" and the
# combinatorics possible on AssertionTrees.
#
# There is no "real code" in this file, i.e., code intended to be ever run.
#
# The reason for using a Python file to store documentation is convenience to the audience for whom this documentation
# is intended, consisting of Apodeixi developers. Convenience manifests itself in these forms:
#
#   1) Navigating to this documentation is as easy as navigating to any other file of code, directly in the code
#       editor.
#   2) The documentation can be structured in sections modeled as code constructs (classes, sub-classes, methods)
#       which makes it possible in most code editors (such as in VS Code) to hide/expand individual sections.
#       That makes it easier to navigate through the documentation and to digest conceptual structure.

class AssertionTree():
    '''
    An assertion tree is a mathematical concept. Here we discribe their simpler form, the assertion 1-tree.
    Later in this documentation there is a description of the more complicated assertion n-ree.

    For simplicity, within this documentation section and its sub-sections we will use the term "assertion tree"
    to mean an assertion 1-tree.
    '''

    def motivation(self):
        '''
        Assertion trees were initially invented to represent human statements about complex domains.
        A tree is supposed to represent just one perspective into a larger reality, a perspective that is
        expressed at different levels of generality. As a tree branches, the children (which are also
        assertion trees) are meant to be next-level detail about the generality described in the parent node.

        A common example is to represent complex projects. A node may represent an area of work, with children
        representing different sub-areas. Assertion trees were initially invented to model this domain,
        though their applicability is wider. In the domain of complex projects, multiple assertion trees
        collectively provide a view of a complex reality from multiple perspectives. Those "views" are really
        assertions of beliefs by a human, and may not be totally consistent, and that is normal. Assertion 
        trees can be linked via various combinatorial operations (such as joining trees) which then support
        computing inferences from the assertions made and/or measure the degree of inconsistency, helping humans
        improve their own description of the complex project they are engaged in.
        '''

    def definition(self):
        '''
        An assertion tree is a finite tree with these characteristics:
        1) It is a finite tree
        2) Any node is also an assertion tree
        3) All nodes at the same level in the tree share some common constraints:
            a) All nodes contain a finite set of scalar properties. A scalar property is a data item that is
                not a complex structure, such as number, a string, or a date.
            b) All nodes' properties are a subset of a common schema, which for reasons explained below is called
                an "interval"
            c) There is a distinguished property that all nodes have in common, called the entity name, that must
                have the same value for all nodes at that level.
            d) Across all levels, there is another distinguished property that all nodes have, called UID. It's
                value is a string and is unique for each node. For a given assertion tree, there is a bijection
                between UID values and nodes.
        '''

    def b_table(self):
        '''
        Assertion trees are best visualized horizontally, as opposed to vertically. This means that we can picture
        the root as being on the left and its children on the right.

        Such a horizontal visualization can be formalized into a tabular view called a "b-table", where the "b"
        acronym stands for "branch", since each row in the table represents a branch in the tree,
        and the headers represent the properties of the nodes.

        Each row additionally has a row number (an integer)

        For example, consider a tree defined as follows:

        1) n.1 is the root. Properties are from the interval [UID, President, a, b], and entity is "President"
        2) n.1.1, n.1.2, n.1.3 are children of n.1. They have properties from the interval [UID, VicePresident, c, d], 
            and entity is "Vice President"
        3) n.1.2.1, n.1.2.2 are children of n.2.1. Properties are from the interval [UID, Director, e], and entity is
            "Director"
        4) For each node and each of its properties, the value of the property is either null or it is the
            name of a fruit, except for entities where the value is the name of a person

        Then a b-table for this tree might be like this:

          row  |     |           |       |      |       |   Vice    |           |       |         |          |               
        number | UID | President |   a   |   b  | UID   | President |      c    |   d   | UID     | Director |   e
        ================================================================================================================
            0  | n.1 | Juan      | apple | kiwi | n.1.1 |   Maria   | nectarine | uva   |         |          |
            1  |     |           |       |      | n.1.2 |  Jorge    | grapefruit| grape | n.1.2.1 | Bill     | peach
            2  |     |           |       |      |       |           |           |       | n.1.2.2 | Lucia    | cherry
            3  |     |           |       |      | n.1.3 |  Julian   |           | mora  |         |          |  
           
        There is a 1-1 mapping between branches in the assertion tree and rows in this b-table, and all the
        information in either can be inferred from the information in the other.

        Now we can explain why the properties of a node are taken from a list called "interval". It is because if
        we concatenate the intervals associated to each level of the tree, in the order of the levels, then we
        get the columns of the b-table above (except for the "row number" column, which is extraneous
        to the tree)

        Some comments:
        1) For any node, only the UID and entity properties are mandatory. The other are optional. For example,
            node n.1.3 has no value for property c. That is fine.
        2) We say that an interval "is blank" for a row if all row values for that row are blank. For each row 
            and each interval, this constraint must be met: all non-blank intervals are "contiguous".
            I.e., there might an initial list of blank intervals, followed by a contiguous list of non-blank
            intervals, after which there might a final list of blank intervals.
        3) Every interval corresponds to a level in the tree.  For example, [UID, Vice President, c, d] corresponds
           to level 2 of the tree (level 0 being the root)
        4) For a given row, the interval properties of the row totally define a unique node at the level of the
           tree corresponding to the interval. 
           For example, in row 1 and interval[UID, Vice President, c, d],
           that corresponds to node n.1.2 with properties UID=n.12, Vice President=Jorge, c=grapefruit, d=grape.
        5) For any given row and interval, if the initial intervals have blank properties then they are inferred to be
           as for the most recent row for which they were not blank. 
           For example, for row 2 and interval[UID, Vice President, c, d], the blank values are assumed to 
           be the same as for row 1, defining node n.1.2
        '''

    def n_table(self):
        '''
        The "n-table" is a refinement of the "b-table", the difference being that each row represents a node as
        as opposed to a branch.

        As a result, an n-table has exactly one UID per row, while a b-table can have multiple UIDs per row
        (in a b-table, there is a UID for every node in the branch in represents, with the leaf node corresponding
        to the "last UID", i.e., the one furthest to the right in the row).

        In the example above for b-tables, the n-table equivalent would be as shown below. There are 6 rows because
        there are 6 nodes, whereas the original b-table had 4 rows because there are 4 branches.

          row  |     |           |       |      |       |   Vice    |           |       |         |          |               
        number | UID | President |   a   |   b  | UID   | President |      c    |   d   | UID     | Director |   e
        ================================================================================================================
            0  | n.1 | Juan      | apple | kiwi |       |           |           |       |         |          |
            1  |     |           |       |      | n.1.1 |   Maria   | nectarine | uva   |         |          |
            2  |     |           |       |      | n.1.2 |  Jorge    | grapefruit| grape |         |          | 
            3  |     |           |       |      |       |           |           |       | n.1.2.1 | Bill     | peach
            4  |     |           |       |      |       |           |           |       | n.1.2.2 | Lucia    | cherry
            6  |     |           |       |      | n.1.3 |  Julian   |           | mora  |         |          |  
           
        The rules for inferring a branch from an n-table are similar as for a b-table: if any 
        initial collection of totally blank intervals are inferred to have the values of the previous non-blank interval.
        In the above example, the interval [UID, Vice President, c, d] is blank for row 3, so they are assumed to
        have the same values as in row 2.

        In an n-table, a row N corresponds to a leaf node if the next row N+1 only has blank intervals to the right 
        of the interval containing the presumed leaf node in row N. 
        In contrast, in a b-table a row N corresponds to a leaf node if all intervals to its left are blank in row
        N itself (as opposed to N+1, as for n-table)
            
        When making joins across assertion trees, the n-table representation is used it removes an ambiguity.
        This is explained below.
        '''

    def link_table(self):
        '''
        A link table is used to provide a tabular view of a join between two assertion trees.

        Assertion trees can be joined at the node level foreign keys based on UIDs. 
        
        That is, a tree T2 can have a "foreign key" on T1 by having one T1's UIDs as a property in one
        of its intervals.

        This is best visualized and defined through n-tables.

        Let T1 be the tree defined earlier, whose n-table representation is:

          row  |     |           |       |      |       |   Vice    |           |       |         |          |               
        number | UID | President |   a   |   b  | UID   | President |      c    |   d   | UID     | Director |   e
        ================================================================================================================
            0  | n.1 | Juan      | apple | kiwi |       |           |           |       |         |          |
            1  |     |           |       |      | n.1.1 |   Maria   | nectarine | uva   |         |          |
            2  |     |           |       |      | n.1.2 |  Jorge    | grapefruit| grape |         |          | 
            3  |     |           |       |      |       |           |           |       | n.1.2.1 | Bill     | peach
            4  |     |           |       |      |       |           |           |       | n.1.2.2 | Lucia    | cherry
            6  |     |           |       |      | n.1.3 |  Julian   |           | mora  |         |          |  
           
        Now suppose that T2 is this other tree (in n-table representation):

          row  |     |            |    Vice    |                    
        number | UID | Department |  President | Budget  
        =================================================
            0  | d.1 | Education  | n.1.1      | $400 m
            1  | d.2 | Defense    | n.1.2      | $40,000 m
            2  | d.3 | Treasury   | n.1.3      | $3,500 m

        This expresses that the Vice President of Education is Maria, since that is the value of the entity
        "Vice President" in node n.1.1 in T1, and T2 is joined to T1 by mapping node d.1 in T1 to node n.1.1 in T2, 
        for example.

        Thus, in tree T2 the property "Vice President" is not an entity (the entity is "Department"). Instead, it is
        a foreign key.

        We call T2 the "referencing tree" and T1 the "referenced tree"

        A "link table" is a table that captures the essential aspects of the join relationship in a single
        table with 3 columns: T1 row number, T1 UID, and T2 UID. In the above example, that would look like this:

        T1 row |  T1   |  T2               
        number | UID   | UID     
        ======================
            0  |       |  
            1  | n.1.1 | d.1
            2  | n.1.2 | d.2
            3  |       | 
            4  |       | 
            6  | n.1.3 | d.3 
           
        It is important to note that a link table is relative a n-table view of the referenced tree. Thus,
        it has the same number of rows and same row numbers as T1's n-table, but might only have populated
        data for some rows where a T1 node is actually linked to a T2 node.

        Link tables are important in situations where an n-table for T1 needs to be augmented with additional
        columns from T2. It provides a way to know which rows in the n-table are the destination for data imported
        from T2.

        In Apodeixi such situations arise often when converting assertion trees through its various representations
        in Excel, YAML or Pandas DataFrame. For example, when parsing an Excel spreadsheet with data from two
        joined assertion trees, the Excel visualization will express the match in terms of rows, but the parser
        will need to populate the T2 "Vice President" property which is probably not displayed in the T2 are in Excel.
        Thus, the parser relies on a link table to look up the T1 UID for the given Excel row (the TI row number)
        and the T2 UID.

        The same is true in reverse, when an Apodeixi representer needs to populate an Excel spreadsheet from
        two manifests (i.e., two assertion trees) which are joined. In such cases the representer has a challenge
        when populating the Excel cells for T2, since it needs place them in rows aligned with T1 so that the
        visual location of both datasets correctly expresses the join. In those cases the representer knows the T2 UID
        and the T1 UID (since the T1 UID is a foreign key in T2), so it uses a link table to find the T1 row number
        that gives the Excel row in which to put the T2 content.
        
        '''