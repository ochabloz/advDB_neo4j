import json
from neo4j import GraphDatabase

URI = "neo4j://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "Password123."

# flush DB
# match (a) -[r] -> () delete a, r; match (a) delete a

# le truc a streamer depuis: http://vmrum.isc.heia-fr.ch/dblpv13.json #attention c'est lourd, pas clicquer sur le lien (ff va l'ouvrir)

# Je reflechis en SQL et en table, donc les relation sont séparée des objects
class Article:
    def __init__(self, _id, title):
        self._id=_id
        self.title=title
    def to_string(self):
            print(str(self._id)+" "+str(self.title))

class Author:
    def __init__(self, _id, name):
        self._id=_id
        self.name=name

class Consumer:

    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.tx_limit=1
        self.citation=[] # to keep tracks, delete later
        self.authored=[] # to keep tracks, delete later
        self.tmp_article_array = []
        self.tmp_author_array = []

    def feed_line(self, json_line):
        line_dict = json.loads(json_line) # maybe replace with the panda version
        authored_flag = "authors" in line_dict
        citation_flag = "references" in line_dict

        tmp_article = Article(line_dict["_id"],line_dict["title"])
        self.insert_article(tmp_article)
        if(citation_flag):
            for references in line_dict["references"]:
                self.citation.append((tmp_article._id,references))
        if(authored_flag):
            for author in line_dict["authors"]:
                if not '_id' in author:
                        print("missing id")
                        break
                tmp_author = Author(author["_id"],author.get("name", None))
                    self.insert_author(tmp_author)
                    self.authored.append((author.get("_id",None),tmp_article._id))

        
        

    def close(self):
        if (len(self.tmp_article_array) != 0):
            self.insert_articles(self.tmp_article_array)
        if (len(self.tmp_author_array) != 0):
            self.insert_authors(self.tmp_author_array)
        self.driver.close()


    def insert_article(self, article):
        self.tmp_article_array.append(article)

        if len(self.tmp_article_array)>= self.tx_limit:
            self.insert_articles(self.tmp_article_array)
            self.tmp_article_array.clear()


    def insert_author(self, author):
        self.tmp_author_array.append(author)

        if len(self.tmp_author_array) >= self.tx_limit:
            self.insert_authors(self.tmp_author_array)
            self.tmp_author_array.clear()

    '''   
    # debug function to remove later
    def insert_one_article(self, article):
        with self.driver.session() as session:
            query = f"CREATE (a:Article {{_id: '{article._id}',title: '{article.title}'}})"
            result = session.write_transaction(self._run_query, query)
            print(result)
    '''

    # act like the function below is private
    def insert_articles(self, articles):
        with self.driver.session() as session:
            tx_query = ""
            for article in articles:
                tx_query += f"CREATE (a:Article {{_id: '{article._id}',title: '{article.title}'}}),"

            #print(tx_query[:-1])
            result = session.write_transaction(self._run_query, tx_query[:-1]) # on enleve la derniere virgule
            print(result)

    # act like the function below is private
    def insert_authors(self, authors):
        with self.driver.session() as session:
            tx_query = ""
            for author in authors:
                if(author.name is not None):
                    tx_query += f"MERGE (a:Author {{_id: '{author._id}',name: '{author.name}'}})," # MERGE to avoid doublons
                else:
                    tx_query += f"MERGE (a:Author {{_id: '{author._id}'}})," # MERGE to avoid doublons

            result = session.write_transaction(self._run_query, tx_query[:-1]) # on enleve la derniere virgule
            print(result)

    def flush_db(self):
        with self.driver.session() as session:
            tx_query1 = f"MATCH (a) -[r] -> () DELETE a, r"
            tx_query2 = f"MATCH (a) DELETE a"

            result = session.write_transaction(self._run_query, tx_query1)
            result = session.write_transaction(self._run_query, tx_query2)
            print(result)

    @staticmethod
    def _run_query(tx, query):
        return tx.run(query)



if __name__ == "__main__":
    print('Hello neo4j Exporter!')
    with open('tst.json','r', encoding="utf-8") as file:
        my_consumer = Consumer(URI, USERNAME, PASSWORD) # init
        for line in file:
            my_consumer.feed_line(line)
        my_consumer.close() # vital, ca insert les objets qui n'ont pas encore été push
            

'''
{
    '_id': '53e99784b7602d9701f3f95b',
    'title': 'Fisherfaces',
    'authors': 
        [
            {
                '_id': '53f46eefdabfaee02adb698d',
                'name': 'Aleix Martinez',
                'sid': '29205725'
            }
        ],
    'venue': 
        {
            '_id': '555036c97cea80f954155dd5',
            'raw': 'Scholarpedia',
            'raw_zh': None,
            'publisher': None,
            'type': 0
        },
    'year': 2011,
    'keywords': [],
    'n_citation': 9,
    'lang': 'en',
    'volume': '6',
    'issue': '2',
    'doi': '10.4249/scholarpedia.4282',
    'pdf': '',
    'url': ['http://dx.doi.org/10.4249/scholarpedia.4282'],
    'abstract': ''
}
'''
