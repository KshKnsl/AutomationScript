import csv
import os

completed_csv = 'completed_articles.csv'
if os.path.exists(completed_csv):
    with open(completed_csv, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        print(f'Found {len(rows)} completed articles')
        if rows:
            print('Sample completed articles:')
            for row in rows[:3]:
                print(f'  {row.get("title", "Unknown")} - {row.get("completed_at", "Unknown")}')
else:
    print('No completed_articles.csv found yet')