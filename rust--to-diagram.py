#!/usr/bin/env python3
import re, os, argparse, uuid
from graphviz import Digraph
from graphviz import Graph as VizGraph

def get_params():
    parser = argparse.ArgumentParser()
    parser.add_argument('tags_file', type=str, help="Rust tags file")
    parser.add_argument("--out", help="Output file",
                    action="store", default="out-graph.dot")
   
    options = parser.parse_args()
    return options

options = get_params()

definition_regex = re.compile(r'^(?P<name>\S+)\s+(?P<sourceFile>\S+)\s+/\^\s*(?P<signature>[\S \t]+)/;\"\s+(?P<type>\S+)\s(?P<metadata>[\s\S]+)')

def dict_from_regex(target, reg):
        return [m.groupdict() for m in reg.finditer(target)]

def parse_tags_file(file_path):
    return open(file_path).read().splitlines()

lines = parse_tags_file(options.tags_file)

def clear_signature(signature):
    signature = signature.replace('{$',')').replace('$/;',')')
    if signature[-1] == '$':
        signature = signature.replace(signature[len(signature)-1], ')') if signature[-2] == '(' else signature[:-1]
    signature = signature.translate({ord(c): f"\{c}" for c in "!@#$%^&*()[]{};:,./<>?\|`~-=_+"})
    return signature

class Graph:

    interface_refer="interface:"
    implementation_refer="implementation:"

    def __init__(self, header, signature, token_type, metadata):
        self.header = header
        self.node_name = f"{header}{str(uuid.uuid4()).replace('-','')}"
        self.signature = signature
        self.token_type = token_type
        self.metadata = metadata
        self.links = list()
        self.fields = list()
        self.methods = list()

    def add_link(self, graph):
        self.links.append(graph)
    
    def is_typedef(self):
        return self.token_type == 'typedef'
    
    def is_impl(self):
        return self.token_type == 'implementation'

    def is_method(self):
        return self.token_type == 'method'

    def is_field(self):
        return self.token_type == 'field'

    def is_interface(self):
        return self.token_type == 'interface'
    
    def is_interface_refer(self,refer):
        return f"{self.interface_refer}{refer}" in self.metadata
    
    def is_implementation_refer(self, refer):
        return f"{self.implementation_refer}{refer}" in self.metadata

class GraphsHandler:
    def __init__(self):
        self.all_graphs = list()
        self.target_graphs = list()

    def __contains(self, graph):
        return any(x['name'] == graph['name'] for x in self.target_graphs)
    
    def add(self, graph):
        self.all_graphs.append(graph)

    def make_structures(self):
        # interfaces
        interfaces = [g for g in self.all_graphs if g.is_interface()]
        implementations = [g for g in self.all_graphs if g.is_impl()]
        
        for interface in interfaces:
            interface_fields = [g for g in self.all_graphs if g.is_interface_refer(interface.header)]
            # methods
            methods = [m for m in interface_fields if m.is_method()]
            interface.methods.extend(methods)
            # fields
            fields = [f for f in interface_fields if not f.is_method()]
            interface.fields.extend(fields)
            # links
            links = [l.node_name for l in implementations if l.header == interface.header or interface.header in l.signature]
            interface.links.extend(links)

        self.target_graphs.extend(interfaces)

        # implementations
        for impl in implementations:
            impl_fields = [g for g in self.all_graphs if g.is_implementation_refer(impl.header)]
            #methods
            methods = [m for m in impl_fields if m.is_method()]
            impl.methods.extend(methods)
            #fields
            fields = [f for f in impl_fields if not f.is_method()]
            impl.fields.extend(fields)
        
        self.target_graphs.extend(implementations)


    def draw(self):
        s = Digraph('struct', filename=f"{options.out}.gv", node_attr={'shape': 'record'}, engine='dot', format='svg', strict=True)
        #s.attr(size='6,6')
        for graph in self.target_graphs:
            lbl = self.__format_label(graph)
            s.node(graph.node_name, label=lbl)
            for link in graph.links:
                s.edge(graph.node_name,link)
        s.view()
   
    def __format_label(self, graph):
        label = "{"
        label += f"{graph.header}|"
        for f in graph.fields:
            label += f"{f.signature}\\n"
        label += "|" if len(graph.fields) > 0 else ""
        for m in graph.methods:
            label += f"{m.signature}\\n"
        label += "}"
        return label


graphs_handler = GraphsHandler()


#indexing
for line in lines:
    if line.startswith('!'):
        continue
    metadata = dict_from_regex(line, definition_regex)[0]
    if metadata['name'] == 'main':
        continue
    
    g = Graph(metadata['name'],
        clear_signature(metadata['signature']),
        metadata['type'],
        metadata['metadata'])
    graphs_handler.add(g)

graphs_handler.make_structures()
graphs_handler.draw()
