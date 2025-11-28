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

def load_text_files_recursively(root_folder: str):
  valid_exts = {".txt", ".md", ".html", ".json", ".yaml"}
  docs = []

  for root, _, files in os.walk(root_folder):
    for fname in files:
      ext = os.path.splitext(fname)[1].lower()
      if ext not in valid_exts:
        continue
      path = os.path.join(root, fname)

      try:
        with open(path, 'r', encoding='utf-8', errors="ignore") as f:
          raw_text = f.read()
      except Exception as e:
        print(f"Skipping file {path} due to read error: {e}")
        continue

      cleaned = clean_text(raw_text)
      relative_path = os.path.relpath(path, root_folder)
      docs.append((relative_path, cleaned))

  return docs

def clean_text(text: str) -> str:
  text = text.replace('\r\n', '\n')
  text = text.replace('\u00a0', ' ')
  
  lines = [line.strip() for line in text.split('\n')]
  normalized = []
  empty_count = 0

  for line in lines:
      if line == "":
          empty_count += 1
          if empty_count > 1:
              continue
      else:
          empty_count = 0
      normalized.append(line)

  return "\n".join(normalized)


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

  print("Loading documents recursively...")
  docs = load_text_files_recursively("../datasets/k8s")
  doc_rows = insert_documents(conn, docs)
  print("Inserted docs: ", doc_rows)