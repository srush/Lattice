# -*- coding: utf-8 -*-
import os,sys
sys.path.append("../gen-py/")
sys.path.append("../../hypergraph/gen_py/")
from lattice_pb2 import *
from hypergraph_pb2 import *
from lexical_pb2 import *

import  lattice_pb2 as lattice
DOWN = "DOWN"
UP = "UP"
class Graph(object):
  def __init__(self):
    self.nodes = {}
    self.id = 0
    self.edge_map = {}

    self.check = set()
    self.lattice = Lattice()

  def set_start(self, node):
    self.lattice.start = node.id

  def set_final(self, node):
    self.lattice.final.append(node.id)

  def register_node(self, node):
    assert node not in self.nodes
    
    self.nodes[self.id] = node
    node.id = self.id
    n = self.lattice.node.add()
    n.id = self.id
    print node
    s = str(node)
    n.label = unicode(s, errors="ignore")
    node.proto = n
    self.id += 1 
    return self.id - 1

  def register_edge_map(self, node, edge_id):
    self.edge_map.setdefault(edge_id, set())
    self.edge_map[edge_id].add(node)

  def size(self):
    return self.id
  
  def __iter__(self):
    for i in self.nodes:
      yield self.nodes[i]

  def filter(self, fn):
    todel = []
    for node in self:
      if fn(node):
        
        for bn in node.back_edges:
          bn.edges.remove(node)
        for n2 in node.edges:
          n2.back_edges.remove(node)
          
        for n2 in node.edges:
          for bn in node.back_edges:
            bn.add_edge(n2)
        todel.append(node.id)
    for i in todel:
      del self.nodes[i]
            
class LatNode(object):
  def __init__(self, graph):
    self.edges = set()
    self.back_edges = set()
    graph.register_node(self)
    self.lex = None
    self.graph = graph
    
  def add_edge(self, to_node):
    self.edges.add(to_node)
    to_node.back_edges.add(self)
    edge = self.proto.edge.add()
    edge.to_id = to_node.id

  def label(self):
    return str(self)

class NonTermNode(LatNode):
  def __init__(self, graph, forest_node, dir):    
    self.forest_node = forest_node
    self.dir = dir
    LatNode.__init__(self, graph)
    self.proto.Extensions[original_node] = -1
    self.proto.Extensions[ignore_node] = True

  def __str__(self):
    return "%s %s %s"%(str(self.forest_node.label), self.dir, self.id)

  def color(self):
    return "red"

class LexNode(LatNode):
  def __init__(self, graph, lex, edge_id):
    self.lex = lex
    LatNode.__init__(self, graph)
    
    print self.proto._known_extensions
    self.proto.Extensions[lattice.is_word] = True
    self.proto.Extensions[lattice.word] = lex.decode("utf-8")
    print lex, self.id
    self.graph.register_edge_map(self, edge_id)
    self.proto.Extensions[original_node] = edge_id

  def __str__(self):
    return "%s %s"%(self.lex, self.id)

  def color(self):
    return "blue"
    

class InternalNode(LatNode):
  def __init__(self, graph, rule, pos, name, dir, edge_id):
    
    self.name = name
    self.rule = rule

    self.dir = dir
    if self.dir == UP:
      self.pos = pos +1
    else :
      self.pos = pos
    LatNode.__init__(self, graph)
    self.graph.register_edge_map(self, edge_id)
    self.proto.Extensions[original_node] = edge_id

  def __str__(self):
    #rhs = self.rule.rhs[:]
    
    
    #rhs.insert(self.pos, ".")
    #rhsstr = " ".join(rhs)
    
    return ("%s %s %s %s"%(self.rule, None , self.dir, self.id)) # self.rule.edge.id

  def label(self):
    lhs = unicode(str(self.rule.lhs), errors='ignore')
    return "%s %s"%(lhs, str(self))

  def color(self):
    return "green"



  
class NodeExtractor(object):
  "Class for creating the FSA that represents a translation forest (forest lattice) "

  def __init__(self):
    pass
 
  def extract(self, forest):
    self.memo = {}
    self.graph = Graph()
    self.forest = forest
    first_state = LexNode(self.graph, "<s>", -1)
    second_state = LexNode(self.graph, "<s>", -1)
    first_state.add_edge(second_state)
    
    (first, last) = self.extract_fsa(self.forest.node[forest.root])
    
    second_state.add_edge(first)

    next_to_last_state = LexNode(self.graph, "</s>", -1)
    last_state = LexNode(self.graph, "</s>", -1)
    
    last.add_edge(next_to_last_state)
    next_to_last_state.add_edge(last_state)

    self.graph.set_start(first_state)
    self.graph.set_final(last_state)

    return self.graph

  def extract_fsa(self, node):
    "Constructs the segment of the fsa associated with a node in the forest"

    # memoization if we have done this node already
    if self.memo.has_key(node.id):
      return self.memo[node.id]

    # Create the FSA state for this general node (non marked)
    # (These will go away during minimization)
    down_state = NonTermNode(self.graph, node, DOWN)
    up_state = NonTermNode(self.graph, node, UP) 
    self.memo[node.id] = (down_state, up_state)
    
    for edge in node.edge:
      previous_state = down_state
    
      rhs = edge.tail_node_ids
      
      # always start with the parent down state ( . P )       
      nts_num = 0
      for i,node_id in enumerate(rhs):
        to_node = self.forest.node[node_id]
        
        # next is a word ( . lex ) 
        if to_node.Extensions[is_word]:
          new_state = LexNode(self.graph, to_node.Extensions[word].encode("UTF-8"), edge.id)

          previous_state.add_edge(new_state)

          # Move the dot ( lex . )
          previous_state = new_state          

        else:
          # it's a symbol


          # local symbol name (lagrangians!)
          #pos = get_sym_pos(sym)
          #to_node = edge.subs[nts_num]
          #nts_num += 1
          # We are at (. N_id ) need to get to ( N_id .) 

          # First, Create a unique named version of this state (. N_id) and ( N_id . )
          # We need these so that we can assign lagrangians
          local_down_state = InternalNode(self.graph, edge.label.encode("UTF-8"), i, to_node.id, DOWN, edge.id)
          local_up_state = InternalNode(self.graph, edge.label.encode("UTF-8"), i , to_node.id, UP, edge.id)

          down_sym, up_sym = self.extract_fsa(to_node)
          
          previous_state.add_edge(local_down_state)
          local_down_state.add_edge(down_sym)
          up_sym.add_edge(local_up_state)

          # move the dot
          previous_state = local_up_state
          
      previous_state.add_edge(up_state)
    return self.memo[node.id]




if __name__ == "__main__":
  hgraph = Hypergraph()  
  f = open(sys.argv[1], "rb")
  hgraph.ParseFromString(f.read())
  f.close()

  graph = NodeExtractor().extract(hgraph)

  f = open(sys.argv[2], "wb")
  f.write(graph.lattice.SerializeToString())
  f.close()
