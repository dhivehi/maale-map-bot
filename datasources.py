import pandas as pd
from fuzzywuzzy import fuzz
import hashlib
import sqlite3
from aiogram.types import InlineQuery, InlineQueryResultVenue


class AddressSource():
    """
    superclass for a address data source
    """
    def get_addresses_results(self, query):
        """
        must return an array of InlineQueryResultVenu
        """
        pass

    def _get_address_hash(self, address_title):
        """
        compute a unique reply hash
        """
        return hashlib.md5(address_title.encode()).hexdigest()


class SQLiteDatasource(AddressSource):
    """
    SQLite backed address data source.

    Uses fts5 for search: 
    note: update the fts table if data is changed
        CREATE VIRTUAL TABLE IF NOT EXISTS addresses_index USING fts5(CATEGORY, DISTRICT, LAT, LNG, NAME, POSTCODE, ROAD, tokenize=porter);
        DELETE FROM addresses_index;
        INSERT INTO addresses_index SELECT * FROM addresses;
    """

    def __init__(self, db_source = "databases/maalemap.db"):
        self.__dbconn = sqlite3.connect(db_source)

    def get_addresses_results(self, query):
        items = []
        
        if query:
            c = self.__dbconn.cursor()
            res = c.execute("SELECT * FROM addresses_index WHERE addresses_index MATCH ? ORDER BY rank LIMIT 10;", (f"NAME:{query}*",))
            for row in res:
                loc = InlineQueryResultVenue(
                        id = self._get_address_hash(row[4]),
                        latitude=row[2],
                        longitude=row[3],
                        title=str(row[4]).capitalize(),
                        address=f"{row[6]}, {row[5]}".capitalize()
                    )
                items.append(loc)

            c.close()
        return items


class PandasDatasource(AddressSource):
    """
    Address data source that uses a Pandas dataframe as the backing store,
    and FuzzyWuzzy to filter extensions.

    Experimental. Warning: Might be CPU/Memory heavy
    """

    def __init__(self, csv_source = "databases/male-map.csv"):
        self.__df =  pd.read_csv(csv_source)
        self.__names = self.__df['NAME'].unique()

    def __get_filter(self,q):
        """
        return fuzzy match lambda for dataframe filter
        """
        def get_fuzzy_ratio(row):
            name = row['NAME']
            return fuzz.token_set_ratio(name, q)

        return get_fuzzy_ratio

    def __query(self,q):
        return self.__df[self.__df.apply(self.__get_filter(q), axis=1) > 70]

    def get_addresses_results(self, query):
        items = []
        if query:
            res = self.__query(query)
            for index, row in res.iterrows():
                loc = InlineQueryResultVenue(
                    id = self._get_address_hash(row['NAME']),
                    latitude=row['LAT'],
                    longitude=row['LNG'],
                    title=str(row['NAME']).capitalize(),
                    address=f"{row['ROAD']}, {row['POSTCODE']}".capitalize()
                )
                items.append(loc)

        return items