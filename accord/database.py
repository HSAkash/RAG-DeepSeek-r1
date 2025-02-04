import sqlite3
import os
from pathlib import Path
from accord import logger
from accord.utils import get_config

class Database:
    def __init__(self):
        self.connection = sqlite3.connect(Path("accord.db"))
        self.crsr = self.connection.cursor()
        self.config = get_config()


    def create_table(self):
        # Check if table already exists
        self.crsr.execute("""
            SELECT name FROM sqlite_master WHERE type='table' AND name='document';
        """)
        
        if self.crsr.fetchone():  # If table exists, return
            logger.info("Table 'document' already exists.")
            return
        
        # SQL command to create a table in the database
        sql_command = """CREATE TABLE document ( 
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        name TEXT NOT NULL,
        vector_path TEXT NOT NULL);"""
        # execute the statement
        self.crsr.execute(sql_command)

        self.insert_data('concatenate.pdf', self.config.vector_store.CONCATENATE_VECTOR_FILE_PATH)
        logger.info("Table created successfully")



    def insert_data(self, file_name:str, vector_path:str):
        # SQL command to insert the data in the table
        sql_command = """INSERT INTO document (name, vector_path) VALUES (?, ?, ?);"""
        # execute the statement
        self.crsr.execute(sql_command, (file_name, vector_path))
        # commit the statement
        self.connection.commit()

    def update_data(self, id:int, vector_path:str):
        # SQL command to update the data in the table
        sql_command = f"""UPDATE document SET vector_path = "{vector_path}" WHERE id = {id};"""
        # execute the statement
        self.crsr.execute(sql_command)
        # commit the statement
        self.connection.commit()


    def get_data(self):
        # SQL command to fetch data from the table
        sql_command = """SELECT * FROM document;"""
        # execute the statement
        self.crsr.execute(sql_command)
        # store all the fetched data in the ans variable
        ans = self.crsr.fetchall()
        # loop to print all the data
        data = [{"id":i[0], "name": i[1], "vector_path": i[2]} for i in ans]
        return data


    def close_connection(self):
        # close the connection
        self.connection.close()


if __name__ == "__main__":
    db = Database()
    db.create_table()
    db.insert_data("test", "test")
    print(db.get_data())
    db.close_connection()

