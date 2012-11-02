#~*~coding:utf8~*~#
'''
RapidMiner Decision Tree to HTML Table

Usage:
    $ python rmtree.py rmtree.txt

Output:
    HTML table to stdout. Redirect this to a convenient location.

About:
    Script to transform a decision tree produced by RapidMiner (rmtree.txt)
    to an HTML table in the format expected by the JS library ListUI.

    The decision tree, obviously, has to be in text format. Go to "Text View"
    and copy+paste the text of the tree to a file, then pass that file to this
    script.

    Script stores this decision tree internally as a Tree object. The Tree
    class, defined in this file, provides multiple output methods: simple
    JSON (which is returned by Tree.__repr__() and Tree.__str__()), and also
    the JSON format used by the InfoVis Toolkit, an attractive tree
    visualization library for JS.

Classes:
    Tree    Simple implementation of Tree data structure. Implements multiple
            output formats.

Resources:
    ListUI JS Library       http://listui.com/?p=84
    InfoVis JS Toolkit      http://philogb.github.com/jit/

Copyright (c) 2012 Joseph Nudell
This code is freely distributable under the MIT License.
'''

import re
import codecs
from sys import argv, stderr, exit


class Tree(object):
    '''Simple tree data structure'''
    def __init__(self, name='', parent=None):
        '''Create new tree data structure'''
        self.__branches = dict()
        self.__parent = parent
        self.name = name

    def __getitem__(self, key):
        '''Subscripts point to branches. Return None on invalid access.'''
        try:
            return self.__branches[key]
        except KeyError:
            return None

    def __setitem__(self, key, value):
        '''Subscripts point to branches: 0 ... n, left to right.'''
        if type(value) is Tree:
            value.set_parent(self)
        elif type(value) is not str and type(value) is not unicode:
            raise TypeError
        self.__branches[key] = value

    def __contains__(self, key):
        '''Test whether tree contains branch'''
        return self.__branches.has_key(key)

    def get_parent(self):
        '''Return parent'''
        return self.__parent

    def set_parent(self, parent):
        '''Set parent'''
        self.__parent = parent

    def get_root(self):
        '''Return the root node'''
        root = self
        if root.get_parent() is not None:
            return root.get_parent().get_root()
        return root

    def to_infovis_json(self, indent=0, rootname='Root'):
        '''Return a more advanced JSON representation of the tree that is
        compliant with the InfoVis JS tree visualization libraries.
        Specify rootname to provide a custom label for root node.'''
        json_template = '{"id": %d, "name": "%s", "children": ['
        #json = json_template % (id(self), self.name)
        json = ""
        if indent == 0:
            json = json_template % (id(self), rootname)
        for key, value in self.__branches.iteritems():
            # Create node for 'key' (an 'edge' in a normal tree)
            json += json_template % (id(key), self.name+": "+key)
            if type(value) is Tree:
                value = value.to_infovis_json(indent=indent+1)
            else:
                value = json_template % (id(value), str(value))
                value += ']}'
                #value += ']},'
            json += '%s]},' % value
            #json += '%s' % value
        #json = '%s]}' % json[:-1]
        if indent== 0:
            json = '%s]}' % json[:-1]
        else:
            json = json[:-1]
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
                string += "<tr><td>%d</td><td>%s</td><td>%s</td>" % \
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
            tree = parse_rmtree(fh)
            html = tree.to_infovis_json()
            print html
    except IOError:
        print >>stderr, "Error opening file `%s`" % argv[1]
        print >>stderr, __doc__
        exit(2)
