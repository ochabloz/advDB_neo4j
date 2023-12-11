import json
import re
from neo4j import GraphDatabase

from logging import getLogger

logger = getLogger()

# flush DB
# match (a) -[r] -> () delete a, r; match (a) delete a

# le truc a streamer depuis: http://vmrum.isc.heia-fr.ch/dblpv13.json #attention c'est lourd, pas cliquer sur le lien (ff va l'ouvrir)

# Je reflechis en SQL et en table, donc les relation sont séparée des objects
class Article:
    def __init__(self, _id, title):
        self._id=_id
        self.title=re.sub(r'"',r'\"',str(title))
    def __repr__(self):
            return str(self._id)+" "+str(self.title)

class Author:
    def __init__(self, _id, name):
        self._id=_id
        self.name=re.sub(r'"',r'\"',str(name))

class Cites:
    def __init__(self, article_id_left, article_id_right):
        self.article_id_left=article_id_left
        self.article_id_right=article_id_right

class Authored:
    def __init__(self, author_id, article_id):
        self.author_id=author_id
        self.article_id=article_id

class Consumer:

    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.tx_limit=1000 # this number controls the fast: the bigger it is the faster it goes, but the more RAM (DB and Python !!) is needed
        self.tmp_article_array = []
        self.tmp_author_array = []
        self.tmp_cites_array = []
        self.tmp_authored_array = []

    def feed_line(self, json_line):
        line_dict = json.loads(json_line) # maybe replace with the panda version
        authored_flag = "authors" in line_dict
        citation_flag = "references" in line_dict

        if not '_id' in line_dict:
            tmp_art_title = line_dict.get("title", None)
            print(f"missing id: title {tmp_art_title}") # what do we do with these?
            return

        tmp_article = Article(line_dict["_id"],line_dict["title"])
        self.insert_article(tmp_article)
        if(citation_flag):
            for references in line_dict["references"]:
                tmp_cites = Cites(tmp_article._id,references)
                self.insert_cites(tmp_cites)
        if(authored_flag):
            for author in line_dict["authors"]:
                if not '_id' in author:
                    tmp_auth_name = author.get("name", None)
                    print(f"missing id: name {tmp_auth_name}") # what do we do with these?
                    break
                tmp_author = Author(author["_id"],author.get("name", None))
                tmp_authored = Authored(tmp_author._id,tmp_article._id)
                self.insert_author(tmp_author)
                self.insert_authored(tmp_authored)

        
        

    def close(self):
        if (len(self.tmp_article_array) != 0):
            self.insert_articles(self.tmp_article_array)
        if (len(self.tmp_author_array) != 0):
            self.insert_authors(self.tmp_author_array)
        if (len(self.tmp_cites_array) != 0):
            self.insert_citess(self.tmp_cites_array)
        if (len(self.tmp_authored_array) != 0):
            self.insert_authoreds(self.tmp_authored_array)
        self.driver.close()

    # these functions would be some neat template functions in cpp
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

    def insert_cites(self, cites):
        self.tmp_cites_array.append(cites)

        if len(self.tmp_cites_array) >= self.tx_limit:
            self.insert_citess(self.tmp_cites_array)
            self.tmp_cites_array.clear()

    def insert_authored(self, authored):
        self.tmp_authored_array.append(authored)

        if len(self.tmp_authored_array) >= self.tx_limit:
            self.insert_authoreds(self.tmp_authored_array)
            self.tmp_authored_array.clear()

    '''   
    # debug function to remove later
    def insert_one_article(self, article):
        with self.driver.session() as session:
            query = f"CREATE (a:Article {{_id: '{article._id}',title: '{article.title}'}})"
            result = session.write_transaction(self._run_query, query)
            #print(result)
    '''

    # act like the function below is private
    def insert_articles(self, articles):
        with self.driver.session() as session:
            tx_query = "WITH ["
            for article in articles:
                if article.title is not None: # maybe do a ternary, or in constructor give default title, I don't know python well enough to know what is fastest
                    tx_query += f" {{_id: '{article._id}', title: \"{article.title}\" }},"
                else:
                    tx_query += f" {{_id: '{article._id}', title: 'n/a' }},"
            tx_query = tx_query[:-1] # remove last comma

            tx_query += "] AS articles "
            tx_query += "UNWIND articles AS article "
            tx_query += "MERGE (a:Article { _id: article._id})"
            tx_query += " SET a.title = article.title" 
            # tx_query += " ON CREATE SET a.title = article.title" 
            # tx_query += " ON MATCH SET a.title = article.title" 

            result = session.execute_write(self._run_query, tx_query)
            #print(result)

    # act like the function below is private
    def insert_authors(self, authors):
        with self.driver.session() as session:

            tx_query = "WITH ["
            for author in authors:
                if author.name is not None: # maybe do a ternary, or in constructor give default title, I don't know python well enough to know what is fastest
                    tx_query += f" {{_id: '{author._id}', name: \"{author.name}\" }},"
                else:
                    tx_query += f" {{_id: '{author._id}', name: 'n/a' }},"
            tx_query = tx_query[:-1] # remove last comma

            tx_query += "] AS authors "
            tx_query += "UNWIND authors AS author "
            tx_query += "MERGE (a:Author { _id: author._id})"
            tx_query += " SET a.name = author.name" 
            # tx_query += " ON CREATE SET a.name = author.name" 
            # tx_query += " ON MATCH SET a.name = author.name" 

            result = session.execute_write(self._run_query, tx_query)
            #print(result)

    # act like the function below is private
    def insert_citess(self, citess):
        with self.driver.session() as session:
            tx_query = "WITH ["
            for cites in citess:
                tx_query += f" {{article_id_left: '{cites.article_id_left}', article_id_right: '{cites.article_id_right}' }},"
            tx_query = tx_query[:-1] # remove last comma

            tx_query += "] AS citess "
            tx_query += "UNWIND citess AS cites "
            # look into the direction of relathionship in details
            tx_query += "MERGE (a:Article { _id: cites.article_id_left }) MERGE (b:Article { _id: cites.article_id_right}) MERGE  (a) -[:CITES]-> (b)"

            result = session.execute_write(self._run_query, tx_query) 
            #print(result)

    # act like the function below is private
    def insert_authoreds(self, authoreds):
        with self.driver.session() as session:

            tx_query = "WITH ["
            for authored in authoreds:
                tx_query += f" {{author_id: '{authored.author_id}', article_id: '{authored.article_id}' }},"
            tx_query = tx_query[:-1] # remove last comma

            tx_query += "] AS authoreds "
            tx_query += "UNWIND authoreds AS authored "
            # look into the direction of relathionship in details
            tx_query += "MERGE (a:Author { _id: authored.author_id }) MERGE (b:Article { _id: authored.article_id}) MERGE  (a) -[:AUTHAURED]-> (b)"

            result = session.execute_write(self._run_query, tx_query) 
            #print(result)


    def set_constraints(self): # should speed MERGE like crazy
        with self.driver.session() as session:
            tx_query01 = f"DROP CONSTRAINT article_id IF EXISTS"
            tx_query02 = f"DROP CONSTRAINT author_id IF EXISTS"
            tx_query1 = f"CREATE CONSTRAINT article_id FOR (a:Article) REQUIRE a._id IS UNIQUE"
            tx_query2 = f"CREATE CONSTRAINT author_id FOR (b:Author) REQUIRE b._id IS UNIQUE"
            result = session.execute_write(self._run_query, tx_query01)
            result = session.execute_write(self._run_query, tx_query02)
            result = session.execute_write(self._run_query, tx_query1)
            result = session.execute_write(self._run_query, tx_query2)
            #print(result)

    def flush_db(self):
        with self.driver.session() as session:
            tx_query = f"MATCH (n) DETACh DELETE n"
            #tx_query1 = f"MATCH (a) -[r] -> () DELETE a, r"
            #tx_query2 = f"MATCH (a) DELETE a"

            result = session.execute_write(self._run_query, tx_query)

            #result = session.write_transaction(self._run_query, tx_query1)
            #result = session.write_transaction(self._run_query, tx_query2)
            #print(result)

    @staticmethod
    def _run_query(tx, query):
        logger.debug("Query: %s", query)
        result = tx.run(query)
        #print("")
        return result



if __name__ == "__main__":
    print('Hello neo4j Exporter!')
    URI = "neo4j://192.168.0.121:7687"
    USERNAME = "neo4j"
    PASSWORD = "Password123."
    with open('dblp/mega_lines_2.json','r', encoding="utf-8") as file:
        my_consumer = Consumer(URI, USERNAME, PASSWORD) # init
        my_consumer.flush_db() # to always start from an empty DB
        my_consumer.set_constraints()

        for line in file:
            my_consumer.feed_line(line)
        my_consumer.close() # vital, push the element in buffer before closing the app
            

'''
Example JSON entry
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
