import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values

load_dotenv()
PG_DSN = {
  "dbname": os.getenv("PG_DB"),
  "user": os.getenv("PG_USER"),
  "password": os.getenv("PG_PASSWORD"),
  "host": os.getenv("PG_HOST"),
  "port": os.getenv("PG_PORT"),
}
BATCH_SIZE = 50

def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200
):
  text = text.strip()
  n = len(text)

  if n <= chunk_size:
      return [text]

  chunks = []
  start = 0

  # Ensure overlap cannot cause backwards movement
  step = chunk_size - overlap
  if step <= 0:
      raise ValueError("chunk_size must be greater than overlap to avoid infinite loops.")

  while start < n:
      end = min(start + chunk_size, n)
      chunks.append(text[start:end].strip())
      start += step

  return chunks


def create_chunks_for_all_documents(conn, chunk_size=1000, overlap=200):
  stream_conn = conn                      # use existing connection for reading
  insert_conn = psycopg2.connect(**PG_DSN)  # separate connection for writing

  cur = stream_conn.cursor(name="doc_stream_cursor")
  cur.itersize = BATCH_SIZE
  cur.execute("SELECT id, source, content FROM documents")

  docs_processed = 0
  rows = cur.fetchmany(BATCH_SIZE)

  while rows:
    for doc_id, source, content in rows:
      print(f"\n📄 Chunking: {source} (id={doc_id})")

      chunks = chunk_text(content, chunk_size, overlap)
      chunk_rows = [(doc_id, idx, chunk) for idx, chunk in enumerate(chunks)]

      with insert_conn.cursor() as insert_cur:
        execute_values(
          insert_cur,
          """
          INSERT INTO chunks (document_id, chunk_index, text)
          VALUES %s
          """,
          chunk_rows
        )
      insert_conn.commit()

      del chunks
      del chunk_rows
      del content

    docs_processed += len(rows)
    print(f"Processed {docs_processed} documents...")

    rows = cur.fetchmany(BATCH_SIZE)

  stream_conn.close()
  insert_conn.close()


if __name__ == "__main__":
  conn = psycopg2.connect(**PG_DSN)
  create_chunks_for_all_documents(conn)
