import os.path
from whoosh import index, analysis, highlight, scoring, searching
from whoosh.fields import Schema, STORED, ID, KEYWORD, TEXT
from whoosh.qparser import MultifieldParser

from server import music_manager

def index_data():
    schema = Schema(
        title=TEXT(stored=True, analyzer=analysis.NgramWordAnalyzer(minsize=2)),
        artists=KEYWORD(stored=True, analyzer=analysis.NgramWordAnalyzer(minsize=2)),
        album=STORED,
        album_title=TEXT(stored=True),
        genres=KEYWORD(stored=True),
        uuid=STORED
    )

    if not os.path.exists("index"):
        os.mkdir("index")
        
    ix = index.create_in("index", schema)

    writer = ix.writer()

    for song in music_manager.get_songs():
        song_data = song.get_json()
        
        writer.add_document(
            title=song_data["title"],
            artists=" ".join(song_data["artists"]),
            album=song_data["album"],
            album_title=song_data["album_title"],
            genres=song_data["genres"],
            uuid=song_data["uuid"]
        )
        
    writer.commit()

def search(query_string):
    ix = index.open_dir("index")
    with ix.searcher(weighting=scoring.BM25F()) as searcher:
        query_parser = MultifieldParser(fieldnames=["title", "artists", "album_title"], schema=ix.schema)
        query = query_parser.parse(query_string)
        results = searcher.search(query)
        
        if results:
            best_hit = results[0]
            suggestions = best_hit.more_like_this("genres")
            
        else:
            suggestions = []
        
        return {
            "results": [dict(hit) for hit in results],
            "suggestions": [dict(hit) for hit in suggestions]
        }

def recommend(user_songs: list[str]):
    ix = index.open_dir("index")
    doc_nums = {}
    
    with ix.searcher() as searcher:
        suggestions: searching.Results = None

        for doc in searcher.document_numbers():
            uuid = searcher.stored_fields(doc)["uuid"]
            doc_nums[uuid] = doc
        
        for song_id in user_songs:

            if song_id in doc_nums:
                doc_num = doc_nums[song_id]
            else:
                continue
            
            cur_result = searcher.more_like(doc_num, "genres", top=3)

            if suggestions is None:
                suggestions = cur_result
            else:
                suggestions.upgrade_and_extend(cur_result)

        if suggestions is None:
            suggestions = []

        return {
            "results": [dict(hit)["uuid"] for hit in suggestions]
        }