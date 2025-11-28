import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values
from openai import OpenAI

load_dotenv()
client = OpenAI()

PG_DSN = {
  "dbname": os.getenv("PG_DB"),
  "user": os.getenv("PG_USER"),
  "password": os.getenv("PG_PASSWORD"),
  "host": os.getenv("PG_HOST"),
  "port": os.getenv("PG_PORT"),
}

def load_text_files_from_folder(folder: str):
  docs = []
  for fname in os.listdir(folder):
    if not fname.endswith((".txt", ".md")):
      continue

    path = os.path.join(folder, fname)
    with open(path, 'r', encoding='utf-8') as f:
      text = f.read()
    docs.append((fname, clean_text(text)))

  return docs

def clean_text(text: str) -> str:
  text = text.replace('\r\n', '\n')
  text = text.replace('\u00a0', ' ')
  
  lines = [line.strip() for line in text.split('\n')]
  lines = [l for l in lines if l]
  return '\n'.join(lines)


def insert_documents(conn, docs):
  with conn.cursor() as cur:
    execute_values(
      cur,
      "INSERT INTO documents (source, content) VALUES %s RETURNING id, source",
      docs
    )
    rows = cur.fetchall()
  conn.commit()
  return rows


if __name__ == "__main__":
  conn = psycopg2.connect(**PG_DSN)
  docs = load_text_files_from_folder("./data")
  doc_rows = insert_documents(conn, docs)
  print("Inserted docs: ", doc_rows)