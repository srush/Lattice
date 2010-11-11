# -*- coding: utf-8 -*-
import os,sys
sys.path.append("../gen-py/")
from lattice_pb2 import *


def reverse_lat(lat):
  back_edges ={} 
  by_id = {}
  for n in lat.node:
    by_id[n.id] = n 
    for e in n.edge:
      back_edges.setdefault(e.to_id, [])
      back_edges[e.to_id].append((n.id, e.id))
  
  ret = Lattice()
  ret.start = lat.final[0]
  ret.final.append(lat.start)
  for n_id in range(len(lat.node)):
    node = ret.node.add()
    node.id = n_id
    node.label = by_id[n_id].label
    
    node.Extensions[is_word] = by_id[n_id].Extensions[is_word]
    node.Extensions[word] = by_id[n_id].Extensions[word]
    print by_id[n_id].Extensions[word], n_id
    
    
    node.Extensions[original_node] = by_id[n_id].Extensions[original_node]
    node.Extensions[ignore_node] = by_id[n_id].Extensions[ignore_node]
    
    if  n_id in back_edges:
      for to_node,e_id in back_edges[n_id]:
        edge = node.edge.add()
        edge.to_id = to_node
        edge.id =e_id
  return ret

if __name__ == "__main__":
  lat = Lattice()  
  f = open(sys.argv[1], "rb")
  lat.ParseFromString(f.read())
  f.close()

  rlat = reverse_lat(lat)

  f = open(sys.argv[2], "wb")
  f.write(rlat.SerializeToString())
  f.close()
