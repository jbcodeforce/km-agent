"""RDF namespace constants for km-agent ontology."""

from rdflib import Namespace, URIRef

ONTO = Namespace("http://km-agent.local/ontology#")
DATA = Namespace("http://km-agent.local/id/")

# Common predicates (also declared in tbox.ttl)
RDF_TYPE = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
RDFS_LABEL = URIRef("http://www.w3.org/2000/01/rdf-schema#label")
RDFS_CLASS = URIRef("http://www.w3.org/2000/01/rdf-schema#Class")

EXTRACTION_METHOD = ONTO.extractionMethod
WIKI_PATH = ONTO.wikiPath
