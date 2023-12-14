import json
import re
import os
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
        self.title=re.sub(r'"',r'\\"',re.sub(r'\\',r'\\\\',str(title)))
    def __repr__(self):
        return str(self._id)+" "+str(self.title)

class Author:
    def __init__(self, _id, name):
        self._id=_id
        self.name=re.sub(r'"',r'\\"',str(name))

class CSV_cache:
    def __init__(self, file_name, header=None):
        self.file_name = file_name
        self.size = 0
        if os.path.exists(self.file_name):
            os.remove(self.file_name)
        if header is not None:
            self.push(header)

    def push(self, data):
        with open(self.file_name, mode='a') as file:
            for row in data:
                self.size += 1
                line = ','.join(str(item) for item in row) + '\n'
                file.write(line)

    def get(self):
        with open(self.file_name, mode='r') as file:
            for line in file:
                yield line.strip().split(',')

    def __len__(self):
        return self.size
        
def write_tx(tx, query, **params):
    return tx.run(query, **params)

class Consumer:

    def __init__(self, uri, user, password, tx_limit=1000):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.tx_limit=tx_limit # this number controls the fast: the bigger it is the faster it goes, but the more RAM (DB and Python !!) is needed
        self.tmp_article_array = []
        self.tmp_author_array = []
        self.tmp_cites_array = []
        self.tmp_authored_array = []
        self._stats_missing_author = 0
        self._stats_missing_titles = 0
        self.cites_cache = CSV_cache("cites_cache.csv")#, [":START_ID",":END_ID",":TYPE"])
        self.authored_cache = CSV_cache("authored_cache.csv")

    def feed_line(self, json_line):
        line_dict = json.loads(json_line) # maybe replace with the panda version
        authored_flag = "authors" in line_dict
        citation_flag = "references" in line_dict

        if not '_id' in line_dict:
            self._stats_missing_titles +=1
            #tmp_art_title = line_dict.get("title", None)
            #print(f"missing id: title {tmp_art_title}") # what do we do with these?
            return

        tmp_article = Article(line_dict["_id"],line_dict.get("title",None))
        self.insert_article(tmp_article)
        if(citation_flag):
            for references in set(line_dict["references"]):
                #tmp_cites = Cites(tmp_article._id,references)
                self.insert_cites((tmp_article._id, references))
        if(authored_flag):
            authors = {a["_id"]: a.get("name", None) for a in line_dict["authors"] if "_id" in a}
            self._stats_missing_author += len(line_dict["authors"]) - len(authors)
            for author_id, name in authors.items():
                tmp_author = Author(author_id, name)
                #tmp_authored = Authored(tmp_author._id,tmp_article._id)
                self.insert_author(tmp_author)
                self.insert_authored((author_id, tmp_article._id))

        
        

    def close(self):
        if (len(self.tmp_article_array) != 0):
            self.insert_articles(self.tmp_article_array)
        if (len(self.tmp_author_array) != 0):
            self.insert_authors(self.tmp_author_array)

        if (len(self.tmp_cites_array) != 0):
            self.cites_cache.push(self.tmp_cites_array)

        if (len(self.tmp_authored_array) != 0):
            self.authored_cache.push(self.tmp_authored_array)


        tmp_cites = []
        for c in self.cites_cache.get():
            tmp_cites.append(c)
            if len(tmp_cites) >= self.tx_limit:
                self.insert_citess(tmp_cites)
                tmp_cites.clear()
        self.insert_citess(tmp_cites)

        tmp_authored = []
        for c in self.authored_cache.get():
            tmp_authored.append(c)
            if len(tmp_authored) >= self.tx_limit:
                self.insert_authoreds(tmp_authored)
                tmp_authored.clear()
        self.insert_authoreds(tmp_authored)

        logger.info("Consumer closed. Number of missing: authors ID: %d, titles ID %d", self._stats_missing_author, self._stats_missing_titles)
        self.driver.close()

    # these functions would be some neat template functions in cpp
    def insert_article(self, article, force=False):
        self.tmp_article_array.append(article)

        if (len(self.tmp_article_array)>= self.tx_limit) or force:
            self.insert_articles(self.tmp_article_array)
            self.tmp_article_array.clear()


    def insert_author(self, author, force=False):
        self.tmp_author_array.append(author)

        if (len(self.tmp_author_array) >= self.tx_limit) or force:
            self.insert_authors(self.tmp_author_array)
            self.tmp_author_array.clear()

    def insert_cites(self, cites, force=False):
        self.tmp_cites_array.append(cites)

        if (len(self.tmp_cites_array) >= self.tx_limit) or force:
            #self.insert_citess(self.tmp_cites_array)
            self.cites_cache.push(self.tmp_cites_array)
            self.tmp_cites_array.clear()

    def insert_authored(self, authored, force=False):
        self.tmp_authored_array.append(authored)

        if (len(self.tmp_authored_array) >= self.tx_limit) or force:
            #self.insert_authoreds(self.tmp_authored_array)
            self.authored_cache.push(self.tmp_authored_array)
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
        articles = [{"_id": article._id, "title": article.title or 'n/a'} for article in articles]
        result = self.driver.execute_query("""
            WITH $articles AS batch_articles
            UNWIND batch_articles AS article
            CREATE (a:Article { _id: article._id, title: article.title})
        """, articles=articles, database_="neo4j")
        logger.info("added %d articles", len(articles))
            #print(result)

    # act like the function below is private
    def insert_authors(self, authors):
        authors = [{"_id": author._id, "name": author.name or 'n/a'} for author in authors]
        result = self.driver.execute_query("""
            WITH $authors AS batch_authors
            UNWIND batch_authors AS author
            MERGE (a:Author { _id: author._id})
            SET a.name = author.name
        """, authors=authors, database_="neo4j")

        logger.info("added %d authors", len(authors))
            #print(result)

    # act like the function below is private
    def insert_citess(self, citess):
        citess = [{"article_id_left": cites[0], "article_id_right": cites[1]} for cites in citess]
        self.driver.execute_query("""
            WITH $citess AS batch_citess
            UNWIND batch_citess AS cites
            MATCH (a:Article { _id: cites.article_id_left }) MATCH (b:Article { _id: cites.article_id_right}) CREATE  (a) -[:CITES]-> (b)
        """, citess=citess, database_="neo4j")
        logger.info("added %d cites", len(citess))

        # with self.driver.session() as session:
        #     tx_query = "WITH ["
        #     for cites in citess:
        #         tx_query += f" {{article_id_left: '{cites.article_id_left}', article_id_right: '{cites.article_id_right}' }},"
        #     tx_query = tx_query[:-1] # remove last comma

        #     tx_query += "] AS citess "
        #     tx_query += "UNWIND citess AS cites "
        #     # look into the direction of relathionship in details
        #     tx_query += "MERGE (a:Article { _id: cites.article_id_left }) MERGE (b:Article { _id: cites.article_id_right}) MERGE  (a) -[:CITES]-> (b)"

        #     result = session.execute_write(self._run_query, tx_query) 
            
            #print(result)

    # act like the function below is private
    def insert_authoreds(self, authoreds):
        authoreds = [{"author_id": authored[0], "article_id": authored[1]} for authored in authoreds]
        self.driver.execute_query("""
            WITH $authoreds AS batch_authoreds
            UNWIND batch_authoreds AS authored
            MATCH (a:Author { _id: authored.author_id }) MATCH (b:Article { _id: authored.article_id}) CREATE  (a) -[:AUTHAURED]-> (b)
        """, authoreds=authoreds, database_="neo4j")
        logger.info("added %d authoreds", len(authoreds))
            #print(result)


    def set_constraints(self): # should speed MERGE like crazy
        self.driver.execute_query("DROP CONSTRAINT article_id IF EXISTS", database_="neo4j")
        self.driver.execute_query("DROP CONSTRAINT author_id IF EXISTS", database_="neo4j")
        self.driver.execute_query("CREATE CONSTRAINT article_id FOR (a:Article) REQUIRE a._id IS UNIQUE", database_="neo4j")
        self.driver.execute_query("CREATE CONSTRAINT author_id FOR (b:Author) REQUIRE b._id IS UNIQUE", database_="neo4j")


    def flush_db(self):
        with self.driver.session() as session:
            tx_query = f"MATCH (n) DETACH DELETE n"
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

