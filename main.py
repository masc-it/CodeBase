from fastapi import FastAPI, Request, File, Body, Form
from http import HTTPStatus
from neo4j import GraphDatabase, basic_auth
import os
from fastapi.responses import HTMLResponse
import json
from fastapi.middleware.cors import CORSMiddleware

from pydantic.fields import Field

from pydantic import BaseModel

with open("creds.txt", "r") as f:
    creds = f.read().split(",")

url = os.getenv("NEO4J_URI", creds[0])
username = os.getenv("NEO4J_USER", creds[1])
password = os.getenv("NEO4J_PASSWORD", creds[2])

neo4jVersion = os.getenv("NEO4J_VERSION", "4.3")
database = os.getenv("NEO4J_DATABASE", "neo4j")

driver = GraphDatabase.driver(url, auth=basic_auth(username, password))
db = driver.session(database=database)

app = FastAPI(
    title="ProgrammingBase",
    description="Programming knowledge base",
    version="0.1",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Query(BaseModel):
    name: str
    url: str
    rel: str
    topic: str
    content : str
    date : str

class QueryDel(BaseModel):
    topic_name: str

@app.get("/", tags=["General"])  # path operation decorator
def _index(request: Request,):
    """Root endpoint."""

    return "gg"

@app.get("/graph.add.subject", tags=["Graph"])  # path operation decorator
def _index(request: Request, subjectName: str ):
    """Root endpoint."""

    summary = db.write_transaction(lambda tx: tx.run("CREATE(n:Subject{name: $subjectName}) return n", {"subjectName": subjectName}).consume())
    response = {
        "message": HTTPStatus.OK.phrase,
        "status-code": HTTPStatus.OK,
        "data": summary,
    }
    return response

@app.post("/graph.query.run", tags=["Graph"])  # path operation decorator
def _run_query(request: Request, query: str ):
    """Root endpoint."""

    resp = db.run(query).data()
    response = {
        "message": HTTPStatus.OK.phrase,
        "status-code": HTTPStatus.OK,
        "data" : resp
    }
    return response

@app.post("/graph.query.delete.topic", tags=["Graph"])  # path operation decorator
def _run_query(request: Request, payload: QueryDel ):
    """Root endpoint."""

    resp = db.run("MATCH (n:Subject)-[r]->(n1) \
        where n.name=$topicName \
        DETACH DELETE n", {"topicName": payload.topic_name}).data()

    response = {
        "message": HTTPStatus.OK.phrase,
        "status-code": HTTPStatus.OK,
        "data" : resp
    }
    return response

@app.post("/graph.query.delete.res", tags=["Graph"])  # path operation decorator
def _run_query(request: Request, payload: QueryDel ):
    """Root endpoint."""

    resp = db.run("MATCH (n:Subject)-[r]->(n1:Resource) \
        where n1.url=$topicName \
        DETACH DELETE n1", {"topicName": payload.topic_name}).data()

    response = {
        "message": HTTPStatus.OK.phrase,
        "status-code": HTTPStatus.OK,
        "data" : resp
    }
    return response

@app.post("/graph.add.resource", tags=["Graph"])  # path operation decorator
def _index(request: Request, 
    payload: Query ):
    """Root endpoint."""

    summary = {"msg": "Already exists"}
    try:
        summary = db.run("\
            MERGE (n:Resource{name: $name, url: $url, content: $content, date: datetime($date)}) \
            MERGE (cv:Subject{name : $subj}) \
            MERGE (cv)-[:" +payload.rel + "]->(n) return cv, n",

            {"name": payload.name, "url": payload.url, "subj":payload.topic,"content": payload.content, "date": payload.date} 
            
            ).data()
    except Exception as e:
        print(e)
    
    response = {
        "message": HTTPStatus.OK.phrase,
        "status-code": HTTPStatus.OK,
        "data": summary,
    }
    return response

@app.get("/graph.resources.get", tags=["Graph"])  # path operation decorator
def _index(request: Request, ):
    """Root endpoint."""

    results = db.read_transaction(lambda tx: list(tx.run("MATCH (cv)-[rel]->(n:Resource) \
         return cv.name as subjectname, type(rel) as r, n.name as title, n.url as url, n.content as content"
        
        )))
    
    nodes, rels = get_results_v2(results)
    return {"nodes": nodes, "links": rels}


@app.post("/graph.resources.by.subject", tags=["Graph"])  # path operation decorator
def _search_resources(request: Request, payload: QueryDel):

    subj = payload.topic_name.lower()
    """Root endpoint."""

    results = db.read_transaction(lambda tx: list(tx.run("MATCH (cv:Subject)-[rel]->(n:Resource) \
        WHERE toLower(cv.name) =~ $subj or toLower(n.name) =~ $subj or toLower(n.content) =~ $subj or toLower(n.url) =~ $subj \
            or toLower(cv.name) CONTAINS $subj or toLower(n.name) CONTAINS $subj or toLower(n.content) CONTAINS $subj or toLower(n.url) CONTAINS $subj \
         return cv.name as subjectname, type(rel) as r, n.name as title, n.url as url, n.content as content"
            , {"subj": subj}
        )))
    # print(results)
    nodes, rels = get_results_v2(results)
    return {"nodes": nodes, "links": rels}

def get_results(results):
    nodes = {}
    rels = []
    i = 0

    for record in results:
        i += 1
        n = {"name": record["title"],"url": record["url"], "label": "title","color": "#c6dbef", "textcolor": "black"}
        nodes[i] = n
        if nodes.get(record["subjectname"]) is None:
            n = {"name": record["subjectname"], "label": "title", "color": "#4679BD", "textcolor": "white"}
            nodes[record["subjectname"]] = n
        
        rels.append({"source": record["subjectname"] , "target": i, "label": record["r"], "id" : i, "color": "#c6dbef" })

    return nodes, rels

def get_results_v2(results):
    nodes = {}
    rels = []
    i = 0
    nodes_ = []
    for record in results:
        i += 1
        n = {"name": record["title"], "url": record["url"], "id": record["url"],"color": "#c6dbef","group": "resource", "textcolor": "black"}
        nodes[i] = n
        nodes_.append(n)
        if nodes.get(record["subjectname"]) is None:
            n = {"id": record["subjectname"], "group": "topic", "name": record["subjectname"], "color": "#4679BD", "textcolor": "white"}
            nodes[record["subjectname"]] = n
            nodes_.append(n)
        
        rels.append({"source": record["subjectname"] , "target": record["url"], "label": record["r"], "color": "#c6dbef" })

    return nodes_, rels