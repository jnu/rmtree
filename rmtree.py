#~*~coding:utf8~*~#
'''
RapidMiner Decision Tree Transducer

Purpose
    Parses the text version of a decision tree generated by RapidMiner. The
    decision tree is stored in a Tree object (Tree class is defined in this
    file). Tree class implements several output methods so that Tree can be
    exported to various visualization libraries.

Output -- Supported Visualizations
    So far the formats expected by the following visualization libraries
    are supported:
        1. ListUI JS Library       http://listui.com/?p=84
        2. InfoVis JS Toolkit      http://philogb.github.com/jit/
        3. d3 v2                   http://d3js.org/

Usage
    $ python rmtree.py rmtree.txt 

About
    Script to transform a decision tree produced by RapidMiner (rmtree.txt)
    to an HTML table in the format expected by the JS library ListUI.

    The decision tree, obviously, has to be in text format. Go to "Text View"
    and copy+paste the text of the tree to a file, then pass that file to this
    script.

    Script stores this decision tree internally as a Tree object. The Tree
    class, defined in this file, provides multiple output methods: simple
    JSON (which is returned by Tree.__repr__() and Tree.__str__()), and also
    other JSON formats used by common JS visualization libraries (see above
    for currently implemented formats).

Classes
    Tree    Simple Tree data structure. call help() for more information.


Copyright (c) 2012 Joseph Nudell
This code is freely distributable under the MIT License.
'''

import re
import codecs
from sys import argv, stderr, exit


class Tree(object):
    '''Simple tree data structure'''
    def __init__(self, name='', parent=None):
        '''Create new tree data structure. Two optional initialization
        parameters: name and parent. name is just a property and can be set
        whenever. It is the node lable (keys in self.__branches dict are the
        edge labels; values that are strings indicate leaves). parent is a
        pointer to the parent Tree, which is necessary for traversal. Note
        that it is generally best to leave this blank upon initialization, as
        the parent attribute is automatically assigned when new subtrees are
        appended as children. The status of root-node is indicated by a None-
        type parent.'''
        self.__branches = dict()
        self.__parent = parent
        self.name = name

    def __getitem__(self, key):
        '''Keys are aliases of self.__branches. Nonexistent keys return None.'''
        try:
            return self.__branches[key]
        except KeyError:
            return None

    def __setitem__(self, key, value):
        '''Keys aliased to self.__branches. Make sure type is either a Tree
        or a string (can be unicode); i.e., type is either a subtree or
        a leaf. Raise TypeError if anything else is given as value.
        NB When a new tree is added here (as a subtree) its parent (i.e.,
        the working tree) is automatically assigned.'''
        if type(value) is Tree:
            value.set_parent(self)
        elif type(value) is not str and type(value) is not unicode:
            raise TypeError
        self.__branches[key] = value

    def __contains__(self, key):
        '''Test whether tree contains branch (by name)'''
        return self.__branches.has_key(key)

    def get_parent(self):
        '''Return parent'''
        return self.__parent

    def set_parent(self, parent):
        '''Set parent'''
        self.__parent = parent

    def get_root(self):
        '''Return the tree's rootnode'''
        root = self
        if root.get_parent() is not None:
            return root.get_parent().get_root()
        return root

    def json(self, style='d3', rootname='Root', indent=0):
        '''Output the Tree in a specified JSON format used by common
        visualization libraries. Currently implemented JIT and d3 (v2)'''
        templates = { 'jit' : '{"id": %d, "name": "%s", "children": [',
                      'd3' : '{"name": "%s", "children": [' }
        if style not in templates.keys():
            raise KeyError
        json = ""
        json_template = templates[style]
        if indent == 0:
            json = ""
            if style=='jit':
                json = json_template % (id(self), rootname)
            else:
                json = json_template % rootname
        for key, value in self.__branches.iteritems():
            # Create node for 'key' (an 'edge' in a normal tree)
            if style=='jit':
                json += json_template % (id(key), self.name+": "+key)
            else:
                json += json_template % (self.name+": "+key)
            if type(value) is Tree:
                value = value.json(style, indent=indent+1)
            else:
                if style=='jit':
                    value = json_template % (id(value), str(value))
                else:
                    value = json_template % str(value)
                value += ']}'
            json += '%s]},' % value
        if indent==0:
            json = '%s]}' % json[:-1]
        else:
            json = json[:-1]
        if style=='d3':
            substr = '"size": %d' % id(json)
            json = re.sub(r'"children"\s*\:\s*\[\]', substr, json)
        return json

    def __repr__(self, indent=0):
        '''Return textual representation of class. This textual representation
        is human-readable JSON.'''
        string = ''
        tab = '\t' * indent
        if indent > 0: string = '\n%s' % tab
        string += '["%s", {\n' % self.name
        for key, value in self.__branches.iteritems():
            if type(value) is Tree:
                value = value.__repr__(indent=indent+1)
            else:
                value = '"%s"' % str(value)
            string += '%s\t"%s" : %s,\n' % (tab, key, value)
        string = string[:-2] + '\n%s}]' % tab
        return string

    def to_listui_html(self, level=0):
        '''Output tree as HTML table compatible with Decision Tree
        JavaScript by ListUI. Note that the IDs will vary each time the
        script is run. As long as they are internally consistent the
        decision tree will work.'''
        string = '<tr>'
        string += '<td>%s</td>' % id(self)
        string += '<td>%s</td>' % self.name
        string += '<td><ul>'
        for key, value in self.__branches.iteritems():
            string += '<li id="%d">%s</li>' % (id(value), key)
        string += '</ul></td>'
        string += '</tr>'

        for key, value in self.__branches.iteritems():
            if type(value) is Tree:
                string += value.to_listui_html(level=level+1)
            else:
                string += "<tr><td>%d</td><td>%s</td><td>%s</td></tr>" % \
                            (id(value), str(value), str(value))
        
        if level == 0:
            wrapper = '''\
<div id="showquestion" class="answers"></div><table id="questions">\
<tr><td>ID</td><td>Questions</td><td>Answers</td></tr>%s</table></div>'''
            return wrapper % string
        return string


    def __str__(self):
        return repr(self)


def parse_rmtree(fh):
    '''
    Parse RapidMiner textual decision tree, return Tree object.
    Accepts file object (opened for reading) as argument.
    '''
    # RegEx to parse RM Decision Tree line. Uses the named groups 'indent',
    # 'node', 'branch', and 'leaf'. 'indent' and 'leaf' are optional. If
    # 'indent' is omitted, the root node is being described. If 'leaf' is
    # present, a leaf is being described.
    re_line = re.compile(
r'^(?P<indent>(?:\|\s{3})*)(?P<node>[^=]+) = (?P<branch>[^:]+)(?:: (?P<leaf>[^\{]+) {)?'
)
    tree = Tree()
    depth = 0
    for line in fh.readlines():
        # Parse line with RegEx
        line_parts = re_line.search(line.strip())
        if line_parts is None:
            raise ValueError

        # Determine level of indent
        level = 0
        if line_parts.group('indent') is not None:
            level = line_parts.group('indent').count('|')
        
        if level < depth:
            # Go back up the tree to appropriate parent node
            for i in range(depth - level):
                tree = tree.get_parent()

        # Make sure node is labeled (will be redundant)
        tree.name = line_parts.group('node')

        # Add leaves & branches
        if line_parts.group('leaf') is not None:
            # This branch leads to a leaf
            tree[line_parts.group('branch')] = line_parts.group('leaf')
        else:
            # Entering a new subtree
            if line_parts.group('branch') not in tree:
                tree[line_parts.group('branch')] = Tree()
            tree = tree[line_parts.group('branch')]

        # Update depth
        depth = level
    return tree.get_root()


if __name__=='__main__':
    '''Check input and run parser'''
    if len(argv)!=2:
        print >>stderr, "Error: Incorrect arguments."
        print >>stderr, __doc__
        exit(1)
    try:
        with codecs.open(argv[1], 'r', 'utf-8') as fh:
            # Parse RM Tree store as tree variable
            tree = parse_rmtree(fh)
    except IOError:
        print >>stderr, "Error opening file `%s`" % argv[1]
        print >>stderr, __doc__
        exit(2)
